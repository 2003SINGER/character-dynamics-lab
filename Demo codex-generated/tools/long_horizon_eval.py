"""Run same-world Demo P comparisons and history forks without huge raw JSON arrays."""
import argparse
import collections
import contextlib
import ast
import gzip
import hashlib
import json
import math
import os
import pathlib
import select
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile

LAYA_POLICY_ID = "laya-typed-policy-v0"
LAYA_CASSETTE_TYPES = {
    "laya_typed_choice", "laya_noul_soft_reconsideration",
    "laya_commitment_choice", "laya_appraisal_scores",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path = pathlib.Path(path)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def lock_experiment_file(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(" ")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def proxy_identity(proxy_path):
    source = pathlib.Path(proxy_path).read_bytes()
    constants = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"CHECKPOINT", "CHECKPOINT_REVISION", "PROMPT_VERSION", "PROTOCOL_VERSION"}:
                constants[name] = ast.literal_eval(node.value)
    required = {"CHECKPOINT", "CHECKPOINT_REVISION", "PROMPT_VERSION", "PROTOCOL_VERSION"}
    if set(constants) != required or any(not constants[name] for name in required):
        raise RuntimeError("cannot lock Laya proxy checkpoint/prompt/protocol constants")
    return {
        "checkpoint": constants["CHECKPOINT"],
        "checkpoint_revision": constants["CHECKPOINT_REVISION"],
        "prompt_version": constants["PROMPT_VERSION"],
        "protocol_version": constants["PROTOCOL_VERSION"],
        # The proxy source contains the actual prompt text and the request/replay contract.
        "proxy_source_sha256": hashlib.sha256(source).hexdigest(),
    }


def worktree_identity(repo):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, text=True)
    diff = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=repo)
    digest = hashlib.sha256(diff)
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=repo)
    for relative in untracked.split(b"\0"):
        if relative:
            path = repo / os.fsdecode(relative)
            if path.is_file():
                digest.update(relative)
                digest.update(bytes.fromhex(sha256_file(path)))
    return {"git_head": head, "git_status_porcelain": status,
            "worktree_sha256": digest.hexdigest()}


def experiment_signature(exe, repo, days, cases, axes, policy, flags, cassette, output):
    mode = mode_metadata(policy, **flags)
    signature = {
        "signature_version": 1,
        "repo_path": str(pathlib.Path(repo).resolve()),
        **worktree_identity(repo),
        "evaluator_source_sha256": sha256_file(__file__),
        "executable_path": str(pathlib.Path(exe).resolve()),
        "executable_sha256": sha256_file(exe),
        "days": days,
        "cases": cases,
        "axes": axes,
        "policy": policy,
        **mode,
        "scenario_seed_formula": "1000 + 17*case",
        "policy_seed_formula": "5000 + 31*case",
    }
    if policy == "laya":
        if cassette is None:
            raise ValueError("Laya evaluation requires --laya-cassette")
        cassette = pathlib.Path(cassette).resolve()
        bridge = pathlib.Path(__file__).with_name("laya_typed_proxy.py")
        locked_laya = proxy_identity(bridge)
        signature["laya"] = locked_laya
        signature["cassette_path"] = str(cassette)
        previous_signature_path = pathlib.Path(output) / "experiment.json"
        if previous_signature_path.exists():
            previous = json.loads(previous_signature_path.read_text())
            if previous.get("cassette_path") != str(cassette):
                raise RuntimeError("resume requires the same Laya cassette path")
            initial_state = previous["cassette_initial_state"]
        else:
            existing_size = cassette.stat().st_size if cassette.exists() else 0
            if existing_size:
                raise RuntimeError("new Laya experiment requires a dedicated empty cassette")
            initial_state = {"existed": cassette.exists(),
                             "sha256": sha256_file(cassette) if cassette.exists() else None,
                             "size": existing_size}
        signature["cassette_initial_state"] = initial_state
    return signature


def assert_signature_current(signature):
    repo = pathlib.Path(signature["repo_path"])
    current = worktree_identity(repo)
    if any(current[field] != signature[field]
           for field in ("git_head", "git_status_porcelain", "worktree_sha256")):
        raise RuntimeError("repository HEAD/worktree changed during the experiment")
    if sha256_file(__file__) != signature["evaluator_source_sha256"]:
        raise RuntimeError("evaluator source changed during the experiment")
    if sha256_file(signature["executable_path"]) != signature["executable_sha256"]:
        raise RuntimeError("long-horizon executable changed during the experiment")
    if "laya" in signature and proxy_identity(
            pathlib.Path(__file__).with_name("laya_typed_proxy.py")) != signature["laya"]:
        raise RuntimeError("Laya proxy source/checkpoint/prompt changed during the experiment")


def acquire_output(output, signature):
    output = pathlib.Path(output)
    if output.exists() and not output.is_dir():
        raise RuntimeError(f"output path is not a directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    lock_path = output / ".experiment.lock"
    lock_handle = lock_path.open("a+")
    try:
        lock_experiment_file(lock_handle)
    except OSError as error:
        lock_handle.close()
        raise RuntimeError(f"another evaluator owns this output directory: {output}") from error
    signature_path = output / "experiment.json"
    if signature_path.exists():
        existing = json.loads(signature_path.read_text())
        if existing != signature:
            lock_handle.close()
            raise RuntimeError("experiment signature mismatch; refusing to mix or resume artifacts")
    else:
        recognized = {".experiment.lock"}
        unexpected = [path.name for path in output.iterdir() if path.name not in recognized]
        if unexpected:
            lock_handle.close()
            raise RuntimeError("non-empty output has no experiment signature; use a new output directory")
        atomic_json(signature_path, signature)
    if "laya" in signature:
        cassette = pathlib.Path(signature["cassette_path"])
        initial = signature["cassette_initial_state"]
        if initial["size"] != 0 or (initial["existed"] and
                                     initial["sha256"] != hashlib.sha256(b"").hexdigest()):
            lock_handle.close()
            raise RuntimeError("experiment signature does not describe an empty initial Laya cassette")
        validate_cassette(cassette, signature["laya"])
    return lock_handle


def mode_metadata(policy, soft_gate=False, commitment=False, appraisal=False):
    flags = {"soft_gate": bool(soft_gate), "typed_commitment": bool(commitment),
             "typed_appraisal": bool(appraisal)}
    if policy != "laya" and any(flags.values()):
        raise ValueError("Laya mode flags require --policy laya")
    active = [name for name, enabled in flags.items() if enabled]
    if policy == "rule":
        return {"policy_id": "rule-policy-v0", "base_policy_id": "rule-policy-v0",
                "mode_flags": flags, "comparison_scope": "rule-baseline",
                "experiment_track": "rule-baseline",
                "paired_policy_compare_eligible": False}
    if not active:
        return {"policy_id": LAYA_POLICY_ID, "base_policy_id": LAYA_POLICY_ID,
                "mode_flags": flags, "comparison_scope": "policy-only",
                "experiment_track": "policy-only-primary",
                "paired_policy_compare_eligible": True}
    # Distinct manifest identity makes the existing policy-only comparator fail closed.
    labels = {"soft_gate": "soft-gate", "typed_commitment": "typed-i",
              "typed_appraisal": "typed-x"}
    suffix = "+".join(labels[name] for name in active)
    dynamics = "typed-xi" if commitment and appraisal else "typed-i" if commitment else "typed-x" if appraisal else "base-dynamics"
    track = ("typed-dynamics-plus-soft-gate-supplement" if soft_gate and (commitment or appraisal)
             else "typed-dynamics-supplement" if commitment or appraisal
             else "soft-gate-supplement")
    return {"policy_id": f"{LAYA_POLICY_ID}+{suffix}", "base_policy_id": LAYA_POLICY_ID,
            "mode_flags": flags, "comparison_scope": f"laya-policy-plus-{dynamics}",
            "experiment_track": track,
            "paired_policy_compare_eligible": False}


def validate_cassette(cassette, locked_laya):
    cassette = pathlib.Path(cassette)
    if not cassette.exists():
        return 0
    rows = 0
    seen_hashes = set()
    with cassette.open() as handle:
        for number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise RuntimeError(f"Laya cassette has an incomplete final line: {cassette}:{number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"invalid Laya cassette row {number}: {error}") from error
            if row.get("type") not in LAYA_CASSETTE_TYPES:
                raise RuntimeError(f"unexpected Laya cassette row type at line {number}")
            for field, expected in (("model", locked_laya["checkpoint"]),
                                    ("checkpoint_revision", locked_laya["checkpoint_revision"]),
                                    ("prompt_version", locked_laya["prompt_version"]),
                                    ("protocol_version", locked_laya["protocol_version"]),
                                    ("proxy_source_sha256", locked_laya["proxy_source_sha256"])):
                if row.get(field) != expected:
                    raise RuntimeError(f"Laya cassette provenance mismatch at line {number}: {field}")
            stored_request = row.get("request")
            if not isinstance(stored_request, dict):
                raise RuntimeError(f"Laya cassette row {number} has no request object")
            request = dict(stored_request)
            if (request.get("protocol_version") != locked_laya["protocol_version"]
                    or request.get("prompt_version") != locked_laya["prompt_version"]):
                raise RuntimeError(f"Laya cassette request is not pinned to its version at line {number}")
            request.pop("request_id", None)
            request_hash = hashlib.sha256(json.dumps(
                request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if row.get("request_hash") != request_hash:
                raise RuntimeError(f"Laya cassette request hash mismatch at line {number}")
            if request_hash in seen_hashes:
                raise RuntimeError(f"duplicate Laya cassette request hash at line {number}")
            seen_hashes.add(request_hash)
            rows += 1
    return rows


def verify_live_laya_identity(port, locked_laya):
    """Fail before an actor runs if the external bridge is not the locked proxy."""
    request = json.dumps({"operation": "identity"}, separators=(",", ":")).encode() + b"\n"
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=5) as connection:
            connection.settimeout(5)
            connection.sendall(request)
            with connection.makefile("rb") as stream:
                line = stream.readline()
    except OSError as error:
        raise RuntimeError(f"could not verify live Laya proxy identity on port {port}: {error}") from error
    try:
        identity = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError("live Laya proxy returned invalid identity JSON") from error
    expected = {
        "model": locked_laya["checkpoint"],
        "checkpoint_revision": locked_laya["checkpoint_revision"],
        "protocol_version": locked_laya["protocol_version"],
        "prompt_version": locked_laya["prompt_version"],
        "proxy_source_sha256": locked_laya["proxy_source_sha256"],
    }
    if any(identity.get(field) != value for field, value in expected.items()):
        raise RuntimeError("live Laya proxy identity does not match the locked experiment provenance")


@contextlib.contextmanager
def laya_replay_server(cassette, scratch):
    bridge = pathlib.Path(__file__).with_name("laya_typed_proxy.py")
    stderr_path = scratch / "replay-proxy.stderr.log"
    stderr_handle = stderr_path.open("w+")
    process = subprocess.Popen(
        [sys.executable, str(bridge), "--replay", str(cassette),
         "--cassette", str(scratch / "replay-unused.jsonl"), "--port", "0"],
        stdout=subprocess.PIPE, stderr=stderr_handle, text=True,
    )
    try:
        ready, _, _ = select.select([process.stdout], [], [], 30)
        if not ready:
            raise RuntimeError("Laya cassette replay proxy did not become ready")
        announcement = process.stdout.readline()
        if not announcement:
            stderr_handle.flush()
            raise RuntimeError(
                "Laya cassette replay proxy exited before readiness: "
                + stderr_path.read_text()[-4000:]
            )
        info = json.loads(announcement)
        if info.get("model") != "convaiinnovations/laya-typed-decisions":
            raise RuntimeError("unexpected Laya replay checkpoint")
        yield info["port"]
    except BaseException as error:
        stderr_handle.flush()
        try:
            with socket.create_connection(("127.0.0.1", int(info["port"])), timeout=0.2):
                listener = "listening"
        except (OSError, UnboundLocalError, KeyError, ValueError):
            listener = "not listening"
        raise RuntimeError(
            f"Laya cassette replay proxy failure (pid={process.pid}, "
            f"exit={process.poll()}, port_state={listener}): {stderr_path.read_text()[-4000:]}"
        ) from error
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        stderr_handle.close()

PROFILES = ["balanced", "disciplined", "procrastinating", "rest_seeking",
            "stimulation_seeking", "anxious", "body_sensitive", "spontaneous"]
AXES = ["procrastination", "self_control", "rest_preference", "stimulation_seeking",
        "task_anxiety_sensitivity", "screen_strain_sensitivity", "need_response", "action_noise"]
MINUTE_FIELDS = ["study_minutes", "leisure_minutes", "rest_minutes", "sleep_minutes",
                 "idle_minutes", "bodily_minutes"]
BEHAVIOR_FIELDS = ["mean_action_bout_minutes", "median_action_bout_minutes",
                   "p90_action_bout_minutes", "commitment_active_minutes_per_day",
                   "commitment_suspended_minutes_per_day", "action_entropy_bits",
                   "switches_per_day", "max_same_action_streak",
                   "repeat_transition_fraction"]


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def behavioral_metrics(boundaries, days):
    bouts = collections.defaultdict(int)
    selections = []
    commitment = collections.Counter()
    for frame in boundaries:
        minutes = frame["elapsed_minutes"]
        action = frame["running_action_before"]
        if action is not None:
            bouts[(action, frame["running_action_started_at"])] += minutes
        commitment[frame["commitment_before"]] += minutes
        if frame["selected_action"] is not None:
            selections.append(frame["selected_action"])
    bout_lengths = list(bouts.values())
    counts = collections.Counter(selections)
    entropy = -sum((count / len(selections)) * math.log2(count / len(selections))
                   for count in counts.values()) if selections else 0.0
    transitions = list(zip(selections, selections[1:]))
    switches = sum(left != right for left, right in transitions)
    repeat = len(transitions) - switches
    streak = 0
    longest = 0
    prior = None
    for action in selections:
        streak = streak + 1 if action == prior else 1
        longest = max(longest, streak)
        prior = action
    return {
        "mean_action_bout_minutes": statistics.mean(bout_lengths) if bout_lengths else 0.0,
        "median_action_bout_minutes": percentile(bout_lengths, 0.5),
        "p90_action_bout_minutes": percentile(bout_lengths, 0.9),
        "commitment_active_minutes_per_day": commitment["active"] / days,
        "commitment_suspended_minutes_per_day": commitment["suspended"] / days,
        "action_entropy_bits": entropy,
        "switches_per_day": switches / days,
        "max_same_action_streak": longest,
        "repeat_transition_fraction": repeat / len(transitions) if transitions else 0.0,
        "selected_action_count": len(selections),
        "action_bout_count": len(bout_lengths),
    }


def run_command(exe, raw, days, case, profile, axis, value, policy, laya_port, flags):
    scenario, policy_seed = 1000 + 17 * case, 5000 + 31 * case
    command = [str(exe), str(scenario), str(policy_seed), str(days), profile,
               str(raw), "boundaries"]
    if axis is not None:
        command += [axis, str(value)]
    if policy == "laya":
        command += ["--laya-port", str(laya_port)]
        if flags["soft_gate"]:
            command.append("--laya-soft-gate")
        if flags["commitment"]:
            command.append("--laya-commitment")
        if flags["appraisal"]:
            command.append("--laya-appraisal")
    return command


def read_run(raw, root, days, case, profile, policy):
    scenario, policy_seed = 1000 + 17 * case, 5000 + 31 * case
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    metadata = None
    daily, forks, tape, boundaries = [], [], [], []
    with raw.open() as handle:
        for line in handle:
            frame = json.loads(line)
            kind = frame["type"]
            if kind == "run":
                metadata = frame
            elif kind == "daily":
                daily.append(frame)
            elif kind == "fork":
                forks.append(frame)
            elif kind == "boundary":
                boundaries.append(frame)
                for event in frame["world_events"]:
                    tape.append((frame["timestamp"], event))
    assert metadata and metadata["scenario_seed"] == scenario and metadata["policy_seed"] == policy_seed
    assert metadata["policy_id"] == (LAYA_POLICY_ID if policy == "laya" else "rule-policy-v0")
    assert len(daily) == days and [row["day"] for row in daily] == list(range(1, days + 1))
    assert all(row["profile_id"] == metadata["profile_id"] for row in daily)
    expected = [7, 30, 60, 120, 180] if days >= 180 else sorted({7, days})
    expected = [day for day in expected if day <= days]
    assert len(forks) == len(expected) * 3 * 3, (len(forks), expected)
    return {"metadata": metadata, "daily": daily, "forks": forks,
            "tape": tape, "behavior": behavioral_metrics(boundaries, days),
            "sha256": digest}


def expected_dynamics_model(policy, flags):
    if policy == "rule" or not (flags["commitment"] or flags["appraisal"]):
        return "demo-living-v1"
    if flags["commitment"] and flags["appraisal"]:
        return "demo-living-v1+laya-typed-xi"
    return ("demo-living-v1+laya-typed-i" if flags["commitment"]
            else "demo-living-v1+laya-typed-x")


def actor_paths(root, case, label):
    runs = root / "runs"
    checkpoints = root / "checkpoints"
    runs.mkdir(parents=True, exist_ok=True)
    checkpoints.mkdir(parents=True, exist_ok=True)
    stem = f"case_{case:02d}_{label}"
    return (runs / f"{stem}.partial.jsonl", runs / f"{stem}.jsonl.gz",
            checkpoints / f"{stem}.DONE.json")


def cassette_prefix_evidence(cassette, byte_count=None):
    cassette = pathlib.Path(cassette)
    if not cassette.exists():
        if byte_count not in (None, 0):
            raise RuntimeError("Laya cassette is missing despite checkpoint evidence")
        return {"byte_count": 0, "sha256": hashlib.sha256(b"").hexdigest(),
                "record_count": 0}
    data = cassette.read_bytes()
    if byte_count is None:
        byte_count = len(data)
    if len(data) < byte_count:
        raise RuntimeError("Laya cassette is shorter than completed actor evidence")
    prefix = data[:byte_count]
    if prefix and not prefix.endswith(b"\n"):
        raise RuntimeError("Laya cassette checkpoint ends inside a record")
    return {"byte_count": byte_count, "sha256": hashlib.sha256(prefix).hexdigest(),
            "record_count": len(prefix.splitlines())}


def world_tape_sha256(run):
    encoded = json.dumps(run["tape"], separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_done_actor(root, done_path, trace_path, days, case, profile, policy, flags,
                    axis=None, value=None, laya_cassette=None):
    if not done_path.exists():
        return None
    done = json.loads(done_path.read_text())
    actor = done.get("actor", {})
    if any(actor.get(key) != expected for key, expected in
           {"case": case, "profile": profile, "axis": axis, "value": value}.items()):
        raise RuntimeError(f"actor checkpoint identity mismatch: {done_path}")
    if not trace_path.is_file() or sha256_file(trace_path) != done.get("compressed_trace_sha256"):
        raise RuntimeError(f"completed actor trace missing or changed: {trace_path}")
    with tempfile.TemporaryDirectory(prefix="laya-resume-read-") as temp:
        raw = pathlib.Path(temp) / "trace.jsonl"
        with gzip.open(trace_path, "rb") as source, raw.open("wb") as sink:
            shutil.copyfileobj(source, sink)
        if sha256_file(raw) != done.get("trace_sha256"):
            raise RuntimeError(f"completed actor trace payload changed: {trace_path}")
        run = read_run(raw, root, days, case, profile, policy)
    expected_mode = mode_metadata(policy, **flags)
    if done.get("metadata") != run["metadata"] or done.get("trace_sha256") != run["sha256"]:
        raise RuntimeError(f"completed actor checkpoint does not match trace: {done_path}")
    if done.get("replay_sha256") != run["sha256"] or done.get("mode") != expected_mode:
        raise RuntimeError(f"completed actor replay/mode evidence mismatch: {done_path}")
    if run["metadata"].get("dynamics_model") != expected_dynamics_model(policy, flags):
        raise RuntimeError(f"completed actor Dynamics mode mismatch: {done_path}")
    if policy == "laya":
        evidence = done.get("cassette_at_completion")
        if not isinstance(evidence, dict) or evidence != cassette_prefix_evidence(
                laya_cassette, evidence.get("byte_count")):
            raise RuntimeError(f"Laya cassette prefix changed since actor completion: {done_path}")
    if (actor.get("scenario_seed") != run["metadata"]["scenario_seed"]
            or actor.get("policy_seed") != run["metadata"]["policy_seed"]
            or actor.get("personality") != run["metadata"]["personality"]
            or actor.get("initial_state") != run["metadata"]["initial_state"]
            or actor.get("world_tape_sha256") != world_tape_sha256(run)):
        raise RuntimeError(f"completed actor W/P/seed evidence mismatch: {done_path}")
    run["trace"] = str(trace_path.relative_to(root))
    return run


def run_one(exe, root, days, case, profile, axis=None, value=None,
            policy="rule", laya_port=None, laya_cassette=None, flags=None, signature=None):
    flags = flags or {"soft_gate": False, "commitment": False, "appraisal": False}
    if signature:
        assert_signature_current(signature)
    label = profile if axis is None else f"axis_{axis}_{value:.1f}"
    raw, compressed, done_path = actor_paths(root, case, label)
    completed = load_done_actor(root, done_path, compressed, days, case, profile, policy,
                                flags, axis, value, laya_cassette)
    if completed is not None:
        return completed
    command = run_command(exe, raw, days, case, profile, axis, value,
                          policy, laya_port, flags)
    # An unfinished actor always restarts from its deterministic initial state.
    if signature:
        assert_signature_current(signature)
    subprocess.run(command, check=True)
    run = read_run(raw, root, days, case, profile, policy)
    if run["metadata"].get("dynamics_model") != expected_dynamics_model(policy, flags):
        raise RuntimeError(f"long-horizon executable did not select requested Dynamics mode: {case} {label}")
    if signature:
        assert_signature_current(signature)
    digest = run["sha256"]
    with tempfile.TemporaryDirectory(prefix="life-replay-") as temp:
        replay = pathlib.Path(temp) / "replay.jsonl"
        second = command.copy()
        second[5] = str(replay)
        if policy == "laya":
            with laya_replay_server(laya_cassette, pathlib.Path(temp)) as replay_port:
                second[second.index("--laya-port") + 1] = str(replay_port)
                subprocess.run(second, check=True)
        else:
            subprocess.run(second, check=True)
        replay_digest = sha256_file(replay)
        if replay_digest != digest:
            raise RuntimeError(f"non-deterministic long run: {case} {label}")
    if signature:
        assert_signature_current(signature)
    with compressed.with_name(compressed.name + ".partial").open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, compresslevel=6, mtime=0) as target:
            with raw.open("rb") as source:
                shutil.copyfileobj(source, target)
    compressed.with_name(compressed.name + ".partial").replace(compressed)
    cassette_evidence = None
    if policy == "laya":
        cassette = pathlib.Path(laya_cassette)
        cassette_rows = validate_cassette(cassette, proxy_identity(
            pathlib.Path(__file__).with_name("laya_typed_proxy.py")))
        cassette_evidence = cassette_prefix_evidence(cassette)
        if cassette_evidence["record_count"] != cassette_rows:
            raise RuntimeError("Laya cassette changed while finalizing actor evidence")
    scenario, policy_seed = 1000 + 17 * case, 5000 + 31 * case
    atomic_json(done_path, {
        "actor": {"case": case, "profile": profile, "axis": axis, "value": value,
                  "scenario_seed": scenario, "policy_seed": policy_seed,
                  "personality": run["metadata"]["personality"],
                  "initial_state": run["metadata"]["initial_state"],
                  "world_tape_sha256": world_tape_sha256(run)},
        "metadata": run["metadata"],
        "trace_sha256": digest,
        "compressed_trace_sha256": sha256_file(compressed),
        "replay_sha256": replay_digest,
        "mode": mode_metadata(policy, **flags),
        "cassette_at_completion": cassette_evidence,
    })
    raw.unlink()
    run["trace"] = str(compressed.relative_to(root))
    return run


def means(rows):
    return {key: statistics.mean(row[key] for row in rows) for key in
            MINUTE_FIELDS + ["task_completions", "decision_count"]}


def features(daily):
    aggregates = means(daily)
    pressure = statistics.mean(row["state"]["task_pressure"] for row in daily)
    fatigue = statistics.mean(row["state"]["fatigue"] for row in daily)
    anxiety = statistics.mean(row["state"]["anxiety"] for row in daily)
    early = daily[:max(1, len(daily) // 3)]
    late = daily[-max(1, len(daily) // 3):]
    return [aggregates["study_minutes"], aggregates["leisure_minutes"],
            aggregates["rest_minutes"], aggregates["sleep_minutes"],
            aggregates["task_completions"] * 100, aggregates["decision_count"] * 5,
            pressure * 100, fatigue * 100, anxiety * 100,
            statistics.mean(row["study_minutes"] for row in late)
            - statistics.mean(row["study_minutes"] for row in early)]


def classifier(records):
    """Leave-one-environment-tape-out nearest-centroid diagnostic, no tuning."""
    if len({record["case"] for record in records}) < 3:
        return None
    correct = 0
    matrix = collections.Counter()
    for held_case in sorted({record["case"] for record in records}):
        train = [record for record in records if record["case"] != held_case]
        test = [record for record in records if record["case"] == held_case]
        scale = [max(1.0, statistics.pstdev(record["features"][i] for record in train))
                 for i in range(len(train[0]["features"]))]
        centroids = {}
        for profile in PROFILES:
            members = [record["features"] for record in train if record["profile"] == profile]
            centroids[profile] = [statistics.mean(vector[i] for vector in members)
                                  for i in range(len(scale))]
        for record in test:
            prediction = min(PROFILES, key=lambda profile:
                sum(((a - b) / width) ** 2 for a, b, width in
                    zip(record["features"], centroids[profile], scale)))
            matrix[(record["profile"], prediction)] += 1
            correct += prediction == record["profile"]
    return {"correct": correct, "total": len(records), "accuracy": correct / len(records),
            "chance": 1 / len(PROFILES),
            "confusion": [{"actual": a, "predicted": p, "count": n}
                          for (a, p), n in sorted(matrix.items())]}


def analyze_forks(forks):
    grouped = collections.defaultdict(dict)
    for row in forks:
        key = (row["scenario_seed"], row["profile_id"], row["checkpoint_day"],
               row["horizon_minutes"])
        grouped[key][row["branch"]] = row
    samples = []
    for key, branch in grouped.items():
        if set(branch) != {"correct", "reset", "stale_24h"}:
            raise RuntimeError(f"missing history branch: {key}")
        reference_events = branch["correct"]["future_world_events"]
        for alternative in ("reset", "stale_24h"):
            if branch[alternative]["future_world_events"] != reference_events:
                raise RuntimeError(f"future external tape diverged within history fork: {key}")
        for alternative in ("reset", "stale_24h"):
            source, other = branch["correct"], branch[alternative]
            samples.append({"scenario_seed": key[0], "profile_id": key[1],
                            "checkpoint_day": key[2], "horizon_minutes": key[3],
                            "branch": alternative,
                            "immediate_pi_js": other["immediate_pi_js"],
                            "immediate_top1_changed": other["immediate_top1_changed"],
                            "study_minutes_gap": other["study_minutes"] - source["study_minutes"],
                            "leisure_minutes_gap": other["leisure_minutes"] - source["leisure_minutes"],
                            "task_effort_gap": other["task_effort"] - source["task_effort"],
                            "fatigue_gap": other["state"]["fatigue"] - source["state"]["fatigue"]})
    summary = []
    for branch in ("reset", "stale_24h"):
        for horizon in (360, 1440, 4320):
            rows = [row for row in samples if row["branch"] == branch
                    and row["horizon_minutes"] == horizon]
            summary.append({"branch": branch, "horizon_minutes": horizon,
                            "checkpoints": len(rows),
                            "mean_immediate_pi_js": statistics.mean(row["immediate_pi_js"] for row in rows),
                            "immediate_top1_change_rate": statistics.mean(row["immediate_top1_changed"] for row in rows),
                            "mean_abs_study_gap_minutes": statistics.mean(abs(row["study_minutes_gap"]) for row in rows),
                            "mean_abs_leisure_gap_minutes": statistics.mean(abs(row["leisure_minutes_gap"]) for row in rows),
                            "mean_abs_task_effort_gap": statistics.mean(abs(row["task_effort_gap"]) for row in rows),
                            "mean_abs_fatigue_gap": statistics.mean(abs(row["fatigue_gap"]) for row in rows)})
    return samples, summary


def report(root, days, cases, actors, axes, policy, mode=None):
    profile_rows = []
    feature_records = []
    all_forks = []
    for case, profile, run in actors:
        day_means = means(run["daily"])
        profile_rows.append({"case": case, "profile": profile, **day_means,
                             **run["behavior"]})
        feature_records.append({"case": case, "profile": profile,
                                "features": features(run["daily"])})
        all_forks.extend(run["forks"])
    profile_summary = []
    for profile in PROFILES:
        rows = [row for row in profile_rows if row["profile"] == profile]
        profile_summary.append({"profile": profile, "cases": len(rows), **{
            field: statistics.mean(row[field] for row in rows)
            for field in MINUTE_FIELDS + ["task_completions", "decision_count"]
                         + BEHAVIOR_FIELDS}})
    fork_samples, fork_summary = analyze_forks(all_forks)
    axis_summary = []
    for axis in AXES:
        variants = [item for item in axes if item[0] == axis]
        if not variants:
            continue
        axis_summary.append({"axis": axis, "values": [{"value": value,
            **means(run["daily"])} for _, value, run in variants]})
    outcome = {"days": days, "cases": cases, "profiles": PROFILES,
               **(mode or mode_metadata(policy)),
               "profile_summary": profile_summary, "paired_case_metrics": profile_rows,
               "overall_behavior": {field: statistics.mean(row[field] for row in profile_rows)
                                    for field in BEHAVIOR_FIELDS},
               "personality_classifier": classifier(feature_records),
               "history_fork_summary": fork_summary, "axis_interventions": axis_summary}
    (root / "analysis.json").write_text(json.dumps(outcome, indent=2) + "\n")
    (root / "history_fork_samples.jsonl").write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in fork_samples) + "\n")
    lines = [f"# Same-world character evaluation — {days} days", "",
             f"Condition: `{outcome['policy_id']}` ({outcome['experiment_track']}). Demo engineering evidence only.", "",
             ("This is a policy-only Rule/Laya comparison; the existing paired policy comparator is applicable."
              if outcome["paired_policy_compare_eligible"] else
              "This is a Laya intervention supplement; do not use the policy-only Rule/Laya comparator."), "",
             "Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, "
             "scenario seed, task/event tape and policy RNG seed. Only P changes within a case.",
             "", "## Personality comparison", "",
             "| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in profile_summary:
        lines.append(f"| {row['profile']} | {row['study_minutes']:.1f} | "
                     f"{row['leisure_minutes']:.1f} | {row['rest_minutes']:.1f} | "
                     f"{row['sleep_minutes']:.1f} | {row['task_completions']:.3f} |")
    lines += ["", "## Persistence, commitment and action patterns", "",
              "Action bouts are keyed by RunningAction start time, not boundary count. "
              "Commitment duration is attributed to its pre-boundary status. "
              "Entropy and repeats use selected action starts, without a pathology threshold.", "",
              "| Profile | Mean bout min | P90 bout min | Active I min/day | Suspended I min/day | Entropy bits | Switches/day | Max same-action streak |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in profile_summary:
        lines.append(f"| {row['profile']} | {row['mean_action_bout_minutes']:.1f} | "
                     f"{row['p90_action_bout_minutes']:.1f} | "
                     f"{row['commitment_active_minutes_per_day']:.1f} | "
                     f"{row['commitment_suspended_minutes_per_day']:.1f} | "
                     f"{row['action_entropy_bits']:.3f} | {row['switches_per_day']:.1f} | "
                     f"{row['max_same_action_streak']:.1f} |")
    lines += ["", "## History forks", "",
              "At each checkpoint, W/O/P and the policy RNG position are copied. "
              "Correct, neutral-reset and prior-day S/commitment receive the same future external tape.", "",
              "| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in fork_summary:
        lines.append(f"| {row['branch']} | {row['horizon_minutes']//60}h | "
                     f"{row['mean_immediate_pi_js']:.4f} | "
                     f"{row['immediate_top1_change_rate']:.1%} | "
                     f"{row['mean_abs_study_gap_minutes']:.1f} min | "
                     f"{row['mean_abs_task_effort_gap']:.3f} |")
    if outcome["personality_classifier"]:
        score = outcome["personality_classifier"]
        lines += ["", "## Unseen-tape profile identification", "",
                  f"Leave-one-tape-out nearest centroid: {score['correct']}/{score['total']} "
                  f"= {score['accuracy']:.1%}; eight-way chance = 12.5%. "
                  "This is a diagnostic, not a calibrated human validity metric."]
    if axis_summary:
        lines += ["", "## Single-axis P interventions", "",
                  "Each row holds all other P dimensions, W and RNG fixed; values are 0.2/0.5/0.8.", ""]
        for row in axis_summary:
            values = row["values"]
            lines.append(f"- `{row['axis']}` study min/day: "
                         + " / ".join(f"{item['study_minutes']:.1f}" for item in values)
                         + "; rest min/day: "
                         + " / ".join(f"{item['rest_minutes']:.1f}" for item in values))
    lines += ["", "## Limits", "",
              "This tape reuses one room and deterministic recurring coursework every three days. "
              "It provides repeated opportunities, interruptions and deadlines, but does not model a full life. "
              "Strong or weak differentiation is a fact about this Demo and tape. "
              "The historical 48h batch was not paired and is not personality evidence.", ""]
    (root / "REPORT.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--days", type=int, choices=(7, 30, 90, 180, 365), required=True)
    parser.add_argument("--cases", type=int, default=1)
    parser.add_argument("--axes", action="store_true")
    parser.add_argument("--policy", choices=("rule", "laya"), default="rule")
    parser.add_argument("--laya-port", type=int)
    parser.add_argument("--laya-cassette", type=pathlib.Path)
    parser.add_argument("--laya-soft-gate", action="store_true")
    parser.add_argument("--laya-commitment", action="store_true")
    parser.add_argument("--laya-appraisal", action="store_true")
    args = parser.parse_args()
    if args.cases < 1:
        parser.error("cases must be positive")
    if args.policy == "laya" and (args.laya_port is None or args.laya_cassette is None):
        parser.error("Laya evaluation requires --laya-port and --laya-cassette")
    flags = {"soft_gate": args.laya_soft_gate,
             "commitment": args.laya_commitment,
             "appraisal": args.laya_appraisal}
    try:
        mode = mode_metadata(args.policy, **flags)
    except ValueError as error:
        parser.error(str(error))
    repo = pathlib.Path(__file__).resolve().parents[2]
    signature = experiment_signature(args.executable, repo, args.days, args.cases, args.axes,
                                     args.policy, flags, args.laya_cassette, args.output)
    lock_handle = acquire_output(args.output, signature)
    try:
        if args.policy == "laya":
            verify_live_laya_identity(args.laya_port, signature["laya"])
        run_experiment(args, signature, mode, flags)
    finally:
        lock_handle.close()


def run_experiment(args, signature, mode, flags):
    actors, axes, manifest_runs = [], [], []
    for case in range(args.cases):
        reference_tape = None
        reference_initial = None
        for profile in PROFILES:
            run = run_one(args.executable, args.output, args.days, case, profile,
                          policy=args.policy, laya_port=args.laya_port,
                          laya_cassette=args.laya_cassette, flags=flags, signature=signature)
            initial = (run["metadata"]["initial_task_effort_target"],
                       run["metadata"]["initial_task_deadline"])
            if reference_tape is None:
                reference_tape, reference_initial = run["tape"], initial
            if run["tape"] != reference_tape or initial != reference_initial:
                raise RuntimeError(f"external tape or initial task diverged: case={case} profile={profile}")
            actors.append((case, profile, run))
            manifest_runs.append({"case": case, "profile": profile,
                                  "scenario_seed": run["metadata"]["scenario_seed"],
                                  "policy_seed": run["metadata"]["policy_seed"],
                                  "personality": run["metadata"]["personality"],
                                  "initial_state": run["metadata"]["initial_state"],
                                  "dynamics_model": run["metadata"]["dynamics_model"],
                                  "behavior": run["behavior"],
                                  "sha256": run["sha256"], "trace": run["trace"],
                                  "mode": mode})
    if args.axes:
        axis_reference = next(run for case, profile, run in actors
                              if case == 0 and profile == "balanced")
        for axis in AXES:
            for value in (0.2, 0.5, 0.8):
                run = run_one(args.executable, args.output, args.days, 0,
                              "balanced", axis, value, policy=args.policy,
                              laya_port=args.laya_port, laya_cassette=args.laya_cassette,
                              flags=flags, signature=signature)
                if run["tape"] != axis_reference["tape"] or (
                    run["metadata"]["initial_task_effort_target"],
                    run["metadata"]["initial_task_deadline"]
                ) != (
                    axis_reference["metadata"]["initial_task_effort_target"],
                    axis_reference["metadata"]["initial_task_deadline"]
                ):
                    raise RuntimeError(f"axis intervention changed external tape: {axis}={value}")
                baseline_p = axis_reference["metadata"]["personality"]
                variant_p = run["metadata"]["personality"]
                if any(variant_p[key] != (value if key == axis else baseline_p[key])
                       for key in baseline_p):
                    raise RuntimeError(f"axis intervention changed more than {axis}={value}")
                axes.append((axis, value, run))
                manifest_runs.append({"case": 0, "axis": axis, "value": value,
                                      "scenario_seed": run["metadata"]["scenario_seed"],
                                      "policy_seed": run["metadata"]["policy_seed"],
                                      "personality": run["metadata"]["personality"],
                                      "dynamics_model": run["metadata"]["dynamics_model"],
                                      "sha256": run["sha256"], "trace": run["trace"],
                                      "mode": mode})
    manifest = {"experiment": "DEMO_CORE_BEHAVIOR_EVAL_V0", "days": args.days,
                **mode,
                "git_revision": signature["git_head"],
                "git_status_porcelain": signature["git_status_porcelain"],
                "worktree_sha256": signature["worktree_sha256"],
                "evaluator_source_sha256": signature["evaluator_source_sha256"],
                "executable_sha256": signature["executable_sha256"],
                "experiment_signature_sha256": hashlib.sha256(
                    json.dumps(signature, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "cases": args.cases, "same_world_within_case": True,
                "deterministic_rerun_count": len(manifest_runs),
                "scenario_seed_formula": "1000 + 17*case",
                "policy_seed_formula": "5000 + 31*case",
                "life_tape_cycle_days": 3, "runs": manifest_runs}
    if args.policy == "laya":
        cassette_copy = args.output / "laya_typed_probabilities.jsonl"
        cassette_tmp = cassette_copy.with_name(cassette_copy.name + ".partial")
        shutil.copyfile(args.laya_cassette, cassette_tmp)
        cassette_tmp.replace(cassette_copy)
        cassette_rows = [json.loads(line) for line in cassette_copy.read_text().splitlines()]
        if not cassette_rows:
            raise RuntimeError("Laya experiment produced no typed model cassette")
        revisions = {row.get("checkpoint_revision", "unrecorded") for row in cassette_rows}
        prompt_versions = {row.get("prompt_version", "unrecorded") for row in cassette_rows}
        if len(revisions) != 1 or len(prompt_versions) != 1:
            raise RuntimeError("Laya cassette mixed checkpoint or prompt versions")
        manifest["laya_checkpoint"] = signature["laya"]["checkpoint"]
        manifest["laya_checkpoint_revision"] = revisions.pop()
        manifest["laya_prompt_version"] = prompt_versions.pop()
        package_versions = {row.get("laya_version") for row in cassette_rows}
        if len(package_versions) != 1 or None in package_versions:
            raise RuntimeError("Laya cassette mixed or omitted package versions")
        manifest["laya_package_version"] = package_versions.pop()
        manifest["laya_protocol_version"] = signature["laya"]["protocol_version"]
        manifest["laya_proxy_source_sha256"] = signature["laya"]["proxy_source_sha256"]
        manifest["laya_cassette_initial_state"] = signature["cassette_initial_state"]
        manifest["laya_cassette_record_count"] = len(cassette_rows)
        manifest["laya_cassette_type_counts"] = dict(collections.Counter(
            row["type"] for row in cassette_rows))
        manifest["laya_cassette_sha256"] = hashlib.sha256(cassette_copy.read_bytes()).hexdigest()
    atomic_json(args.output / "manifest.json", manifest)
    report(args.output, args.days, args.cases, actors, axes, args.policy, mode)


if __name__ == "__main__":
    main()
