import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const PILOT_DIR = path.resolve(path.dirname(SCRIPT_PATH), "..");
const REPO_ROOT = path.resolve(PILOT_DIR, "../..");
const OUTPUT_ROOT = path.join(REPO_ROOT, "outputs", "praxish_activity_pilot_v0");
const SOURCE_ROOT = path.join(OUTPUT_ROOT, "source-cache");
const ZIP_PATH = path.join(SOURCE_ROOT, "Praxish_AIIDE2023_Artifact.zip");
const EXTRACTED_ROOT = path.join(SOURCE_ROOT, "artifact");
const NONINTERACTIVE_ROOT = path.join(EXTRACTED_ROOT, "noninteractive");
const SCENARIO_PATH = path.join(PILOT_DIR, "scenario.json");

export const PIN = {
  tag: "aiide-23",
  commit: "4729b0c469a7ecb423622f543ca116315616a76b",
  archiveSha256: "a5418432db8f2af8387a8eead2e4ad1392465833d862eda9273c614b883a8c77",
  files: {
    "db.js": "acb98656dcc0fe461ba7d6b2875bd3429ae4068735b1795297a5722d0469c46c",
    "praxish.js": "ef2f77999b08dd24c9893a531ae2096ef33189a9cf46bf342d024ffa44e1c088",
    "tests.js": "7b9a41281ec8620d43bcf0062b39cbcbaad22349483fe9cae55b3ef823486947"
  }
};

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function readScenario() {
  return JSON.parse(fs.readFileSync(SCENARIO_PATH, "utf8"));
}

export function verifyArtifact() {
  assert(fs.existsSync(ZIP_PATH), `Missing upstream release archive: ${ZIP_PATH}; run the fetch command first.`);
  const actualArchiveHash = sha256(ZIP_PATH);
  assert(actualArchiveHash === PIN.archiveSha256, `Archive hash mismatch: expected ${PIN.archiveSha256}, got ${actualArchiveHash}`);
  for (const [name, expected] of Object.entries(PIN.files)) {
    const actualPath = path.join(NONINTERACTIVE_ROOT, name);
    assert(fs.existsSync(actualPath), `Missing upstream file: ${actualPath}`);
    const actual = sha256(actualPath);
    assert(actual === expected, `${name} hash mismatch: expected ${expected}, got ${actual}`);
  }
  return {
    tag: PIN.tag,
    commit: PIN.commit,
    archive_sha256: actualArchiveHash,
    files: Object.fromEntries(Object.keys(PIN.files).map(name => [name, sha256(path.join(NONINTERACTIVE_ROOT, name))]))
  };
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { encoding: "utf8", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed (${result.status}):\n${result.stderr || result.stdout}`);
  }
  return result.stdout;
}

export function fetchArtifact() {
  if (fs.existsSync(SOURCE_ROOT)) {
    if (fs.existsSync(ZIP_PATH) && fs.existsSync(EXTRACTED_ROOT)) {
      return { status: "already_present", artifact: verifyArtifact() };
    }
    if (fs.existsSync(ZIP_PATH) && !fs.existsSync(EXTRACTED_ROOT) && sha256(ZIP_PATH) === PIN.archiveSha256) {
      const staging = fs.mkdtempSync(path.join(os.tmpdir(), "praxish-aiide23-extract-"));
      try {
        const stagedExtracted = path.join(staging, "artifact");
        fs.mkdirSync(stagedExtracted);
        run("unzip", ["-q", ZIP_PATH, "-d", stagedExtracted]);
        for (const [name, expected] of Object.entries(PIN.files)) {
          const extracted = path.join(stagedExtracted, "noninteractive", name);
          assert(fs.existsSync(extracted) && sha256(extracted) === expected, `Extracted ${name} failed hash validation`);
        }
        fs.renameSync(stagedExtracted, EXTRACTED_ROOT);
        return { status: "extracted_and_verified", artifact: verifyArtifact() };
      } finally {
        fs.rmSync(staging, { recursive: true, force: true });
      }
    }
    throw new Error(`Refusing to overwrite partial or unverified source directory: ${SOURCE_ROOT}`);
  }

  fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
  const staging = fs.mkdtempSync(path.join(os.tmpdir(), "praxish-aiide23-fetch-"));
  try {
    run("gh", ["release", "download", PIN.tag, "--repo", "mkremins/praxish", "--dir", staging, "--pattern", "*.zip"]);
    const stagedZip = path.join(staging, "Praxish_AIIDE2023_Artifact.zip");
    assert(fs.existsSync(stagedZip), "Release download did not produce Praxish_AIIDE2023_Artifact.zip");
    assert(sha256(stagedZip) === PIN.archiveSha256, "Downloaded release archive did not match the pinned SHA-256");
    const stagedExtracted = path.join(staging, "artifact");
    fs.mkdirSync(stagedExtracted);
    run("unzip", ["-q", stagedZip, "-d", stagedExtracted]);
    for (const [name, expected] of Object.entries(PIN.files)) {
      const extracted = path.join(stagedExtracted, "noninteractive", name);
      assert(fs.existsSync(extracted) && sha256(extracted) === expected, `Extracted ${name} failed hash validation`);
    }
    fs.mkdirSync(SOURCE_ROOT);
    fs.copyFileSync(stagedZip, ZIP_PATH, fs.constants.COPYFILE_EXCL);
    fs.renameSync(stagedExtracted, EXTRACTED_ROOT);
    return { status: "downloaded_and_verified", artifact: verifyArtifact() };
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
}

function seededMath(seed) {
  let state = Number(seed) >>> 0;
  const math = Object.create(Math);
  math.random = () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
  return math;
}

function makeRuntime() {
  const logs = [];
  const sandbox = {
    console: {
      log: (...values) => logs.push({ level: "log", values: values.map(safeValue) }),
      warn: (...values) => logs.push({ level: "warn", values: values.map(safeValue) }),
      error: (...values) => logs.push({ level: "error", values: values.map(safeValue) })
    }
  };
  vm.createContext(sandbox);
  for (const name of ["db.js", "praxish.js"]) {
    vm.runInContext(fs.readFileSync(path.join(NONINTERACTIVE_ROOT, name), "utf8"), sandbox, { filename: name });
  }
  vm.runInContext(
    `(() => { const original = randNth; randNth = function(items) { const picked = original(items); if (typeof globalThis.__onPick === "function") globalThis.__onPick(picked); return picked; }; })();`,
    sandbox,
    { filename: "pilot_observer.js" }
  );
  return { sandbox, logs };
}

function safeValue(value) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean" || value === null) return value;
  try { return JSON.parse(JSON.stringify(value)); } catch { return String(value); }
}

function snapshotFacts(sandbox, state, patterns) {
  return patterns.map(({ id, pattern }) => {
    const matches = sandbox.unify(pattern, state.db, {}).map(bindings => ({ ...bindings }));
    return { id, pattern, matches };
  });
}

function describeBindings(action) {
  const metadata = new Set(["practiceID", "instanceID", "actionID", "name", "score"]);
  return Object.fromEntries(Object.entries(action).filter(([key]) => !metadata.has(key)));
}

function scoreCandidate(sandbox, state, actor, action) {
  const originalDb = state.db;
  state.db = sandbox.clone(originalDb);
  try {
    sandbox.performAction(state, action);
    const roleNames = state.practiceDefs[action.practiceID].roles;
    const goalScores = actor.goals.map(goal => {
      const matches = sandbox.query(state.db, goal.conditions, {}).length;
      return {
        goal_id: goal.id,
        utility: goal.utility,
        matches,
        absolute_score_contribution: goal.utility * matches
      };
    });
    return {
      action_id: action.actionID,
      practice_id: action.practiceID,
      instance_id: action.instanceID,
      name: action.name,
      roles: Object.fromEntries(roleNames.map(role => [role, action[role]])),
      bindings: describeBindings(action),
      goal_scores: goalScores,
      score: goalScores.reduce((total, goal) => total + goal.absolute_score_contribution, 0)
    };
  } finally {
    state.db = originalDb;
  }
}

function selectedDescriptor(state, action) {
  if (!action) return null;
  const roleNames = state.practiceDefs[action.practiceID].roles;
  return {
    action_id: action.actionID,
    practice_id: action.practiceID,
    instance_id: action.instanceID,
    name: action.name,
    roles: Object.fromEntries(roleNames.map(role => [role, action[role]])),
    bindings: describeBindings(action),
    score_reported_by_original_tick: Number.isFinite(action.score) ? action.score : null
  };
}

export function runScenario(conditionId, options = {}) {
  verifyArtifact();
  const scenario = structuredClone(options.scenario || readScenario());
  if (options.preferenceVariant) {
    const variant = scenario.authored_preference_variants?.[options.preferenceVariant];
    assert(variant, `Unknown authored preference variant: ${options.preferenceVariant}`);
    for (const character of scenario.characters) {
      if (character.name !== "worker") continue;
      for (const goal of character.goals) {
        const override = variant.worker_goal_utility_overrides?.[goal.id];
        if (override !== undefined) goal.utility = override;
      }
    }
  }
  const condition = scenario.conditions[conditionId];
  assert(condition, `Unknown scenario condition: ${conditionId}`);
  const { sandbox, logs } = makeRuntime();
  sandbox.Math = seededMath(scenario.seed);
  const state = sandbox.createPraxishState();
  state.allChars = scenario.characters.map(character => structuredClone(character));
  for (const practice of scenario.practices) sandbox.definePractice(state, structuredClone(practice));
  for (const outcome of scenario.initial_practice_instances) sandbox.performOutcome(state, outcome);

  const eventsByTurn = new Map();
  for (const event of condition.events) {
    const list = eventsByTurn.get(event.before_turn) || [];
    list.push(event);
    eventsByTurn.set(event.before_turn, list);
  }

  const turns = [];
  for (let turn = 0; turn < scenario.turns; turn++) {
    const appliedEvents = [];
    for (const event of eventsByTurn.get(turn) || []) {
      const before = snapshotFacts(sandbox, state, scenario.trace_fact_patterns);
      sandbox.performOutcome(state, event.outcome);
      const after = snapshotFacts(sandbox, state, scenario.trace_fact_patterns);
      appliedEvents.push({ id: event.id, outcome: event.outcome, facts_before: before, facts_after: after });
    }

    const actorIndex = (state.actorIdx + 1) % state.allChars.length;
    const actor = state.allChars[actorIndex];
    const preFacts = snapshotFacts(sandbox, state, scenario.trace_fact_patterns);
    const rawCandidates = sandbox.getAllPossibleActions(state, actor.name);
    const candidates = rawCandidates.map(action => scoreCandidate(sandbox, state, actor, action));
    let picked = null;
    sandbox.__onPick = action => { picked = action; };
    const priorLogCount = logs.length;
    sandbox.tick(state);
    sandbox.__onPick = null;
    const runtimeMessages = logs.slice(priorLogCount);
    const postFacts = snapshotFacts(sandbox, state, scenario.trace_fact_patterns);

    turns.push({
      turn,
      event: appliedEvents,
      actor: actor.name,
      pre_facts: preFacts,
      candidates,
      selected: selectedDescriptor(state, picked),
      post_facts: postFacts,
      runtime_messages: runtimeMessages
    });
  }

  const trace = {
    trace_schema_version: 1,
    evidence_kind: "pilot_generated_typed_trace",
    source: {
      release_tag: PIN.tag,
      commit: PIN.commit,
      archive_sha256: PIN.archiveSha256,
      upstream_files: PIN.files,
      upstream_source_modified: false,
      license_status: "no license file found in the downloaded release artifact or the pinned tag; local inspection only"
    },
    scenario_id: scenario.scenario_id,
    condition: conditionId,
    preference_variant: options.preferenceVariant || "default",
    seed: scenario.seed,
    activities: scenario.practices.map(practice => ({
      practice_id: practice.id,
      name: practice.name,
      roles: practice.roles,
      action_templates: practice.actions.map(action => action.name)
    })),
    scoring_semantics: "absolute satisfied-goal value: utility multiplied by post-action match count, summed across goals",
    turns
  };
  return JSON.parse(JSON.stringify(trace));
}

export function runOriginalDemo(seed = readScenario().seed) {
  const artifact = verifyArtifact();
  const logs = [];
  const sandbox = {
    Math: seededMath(seed),
    console: {
      log: (...values) => logs.push({ level: "log", values: values.map(safeValue) }),
      warn: (...values) => logs.push({ level: "warn", values: values.map(safeValue) }),
      error: (...values) => logs.push({ level: "error", values: values.map(safeValue) })
    }
  };
  vm.createContext(sandbox);
  for (const name of ["db.js", "praxish.js", "tests.js"]) {
    vm.runInContext(fs.readFileSync(path.join(NONINTERACTIVE_ROOT, name), "utf8"), sandbox, { filename: name });
  }
  const finalDb = JSON.parse(vm.runInContext("JSON.stringify(testPraxishState.db)", sandbox));
  const phases = logs
    .filter(entry => entry.values[0]?.startsWith?.("PRACTICE TEST:"))
    .map(entry => entry.values[0]);
  return JSON.parse(JSON.stringify({
    seed,
    artifact,
    phases,
    logs,
    final_db: finalDb,
    final_db_sha256: crypto.createHash("sha256").update(JSON.stringify(finalDb)).digest("hex")
  }));
}

function ensureRunId(value) {
  const runId = value || new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  assert(/^[A-Za-z0-9][A-Za-z0-9._-]{1,79}$/.test(runId), `Unsafe run ID: ${runId}`);
  return runId;
}

function initialManifest(runId, command, seed) {
  return {
    run_id: runId,
    command,
    status: "running",
    generated_at_utc: new Date().toISOString(),
    node_version: process.version,
    seed,
    scenario_file: "02_实验/Praxish_Activity_Pilot_v0/scenario.json",
    scenario_sha256: sha256(SCENARIO_PATH),
    runner_sha256: sha256(SCRIPT_PATH),
    artifact_pin: { tag: PIN.tag, commit: PIN.commit, expected_archive_sha256: PIN.archiveSha256 },
    browser_ui_verified: false
  };
}

function createRun(runId, command, seed) {
  const runDir = path.join(OUTPUT_ROOT, "runs", runId);
  fs.mkdirSync(path.dirname(runDir), { recursive: true });
  fs.mkdirSync(runDir, { recursive: false });
  const manifest = initialManifest(runId, command, seed);
  fs.writeFileSync(path.join(runDir, "run_manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, { flag: "wx" });
  return { runDir, manifest };
}

function finishRun(runDir, manifest, status, extra = {}) {
  Object.assign(manifest, extra, { status, finished_at_utc: new Date().toISOString() });
  fs.writeFileSync(path.join(runDir, "run_manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
}

function failRun(runDir, manifest, error) {
  try {
    fs.writeFileSync(path.join(runDir, "error.json"), `${JSON.stringify({
      error_name: error.name || "Error",
      message: String(error.message || error),
      stack: error.stack || null,
      failed_at_utc: new Date().toISOString()
    }, null, 2)}\n`, { flag: "wx" });
    finishRun(runDir, manifest, "failed");
  } catch (recordError) {
    process.stderr.write(`Could not fully record run failure: ${recordError}\n`);
  }
}

function runCommand(args) {
  const runIdArg = args.indexOf("--run-id");
  const runId = ensureRunId(runIdArg >= 0 ? args[runIdArg + 1] : undefined);
  if (runIdArg >= 0) assert(args[runIdArg + 1], "--run-id requires a value");
  const scenario = readScenario();
  const { runDir, manifest } = createRun(runId, "paired_scenario", scenario.seed);
  try {
    const artifact = verifyArtifact();
    const traces = {};
    for (const condition of Object.keys(scenario.conditions)) {
      traces[condition] = runScenario(condition);
      fs.writeFileSync(path.join(runDir, `${condition}.trace.json`), `${JSON.stringify(traces[condition], null, 2)}\n`, { flag: "wx" });
    }
    finishRun(runDir, manifest, "succeeded", { artifact, conditions: Object.keys(traces) });
    process.stdout.write(`${runDir}\n`);
  } catch (error) {
    failRun(runDir, manifest, error);
    throw error;
  }
}

function originalCommand(args) {
  const runIdArg = args.indexOf("--run-id");
  assert(runIdArg >= 0 && args[runIdArg + 1], "Usage: original --run-id <ID>");
  const runId = ensureRunId(args[runIdArg + 1]);
  const seed = readScenario().seed;
  const { runDir, manifest } = createRun(runId, "original_noninteractive_demo", seed);
  const originalDir = path.join(runDir, "original_demo");
  try {
    fs.mkdirSync(originalDir, { recursive: false });
    const result = runOriginalDemo(seed);
    fs.writeFileSync(path.join(originalDir, "console_log.jsonl"), `${result.logs.map(item => JSON.stringify(item)).join("\n")}\n`, { flag: "wx" });
    fs.writeFileSync(path.join(originalDir, "final_db.json"), `${JSON.stringify(result.final_db, null, 2)}\n`, { flag: "wx" });
    fs.writeFileSync(path.join(originalDir, "original_manifest.json"), `${JSON.stringify({
      execution: "original_release_scripts_in_order_db_js_praxish_js_tests_js",
      seed: result.seed,
      log_records: result.logs.length,
      phases: result.phases,
      final_db_sha256: result.final_db_sha256,
      artifact: result.artifact,
      browser_ui_verified: false
    }, null, 2)}\n`, { flag: "wx" });
    finishRun(runDir, manifest, "succeeded", { phases: result.phases, original_log_records: result.logs.length, final_db_sha256: result.final_db_sha256 });
    process.stdout.write(`${runDir}\n`);
  } catch (error) {
    failRun(runDir, manifest, error);
    throw error;
  }
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (command === "fetch") {
    process.stdout.write(`${JSON.stringify(fetchArtifact(), null, 2)}\n`);
  } else if (command === "run") {
    runCommand(args);
  } else if (command === "original") {
    originalCommand(args);
  } else if (command === "test") {
    const result = spawnSync(process.execPath, ["--test", path.join(PILOT_DIR, "tools", "pilot.test.mjs")], { stdio: "inherit" });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Node test run failed with status ${result.status}`);
  } else {
    process.stderr.write("Usage: node tools/pilot.mjs <fetch|run [--run-id ID]|original --run-id ID|test>\n");
    process.exitCode = 2;
  }
}

const isMain = (() => {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(process.argv[1]) === fs.realpathSync(SCRIPT_PATH);
  } catch {
    return path.resolve(process.argv[1]) === SCRIPT_PATH;
  }
})();
if (isMain) {
  main().catch(error => {
    process.stderr.write(`${error.stack || error}\n`);
    process.exitCode = 1;
  });
}
