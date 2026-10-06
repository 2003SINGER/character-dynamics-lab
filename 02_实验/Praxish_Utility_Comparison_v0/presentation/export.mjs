import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../../..");
const RUNS = path.join(ROOT, "outputs/praxish_utility_comparison_v0/runs");
const PRESENTATIONS = path.join(ROOT, "outputs/praxish_utility_comparison_v0/presentation");
const TEMPLATE = path.join(HERE, "viewer.template.html");
const sha256 = value => crypto.createHash("sha256").update(value).digest("hex");
const fileHash = p => sha256(fs.readFileSync(p));
const json = value => JSON.stringify(value, null, 2) + "\n";
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

const ACTIONS = new Map([
  ["start_restocking", "开始备货"], ["finish_restocking", "完成备货"],
  ["answer_request", "回应访客请求"], ["wait_for_answer", "等待回应"],
  ["cancel_request", "取消请求"]
]);
const EVENTS = new Map([
  ["visible_request", "访客提出请求"], ["second_visible_request", "另一位访客提出请求"],
  ["workspace_closed", "工作区关闭"], ["workspace_reopened", "工作区重新开放"]
]);
const PHASES = new Set(["waiting", "working", "complete"]);
const REQUESTS = new Set(["pending", "served", "cancelled"]);

function person(value, expectedRole) {
  assert(typeof value === "string", `Malformed ${expectedRole} identity`);
  const match = /^(worker|visitor)([0-9]*)$/.exec(value);
  assert(match && match[1] === expectedRole, `Unknown ${expectedRole} identity: ${value}`);
  return { id: value, role: expectedRole, ordinal: Number(match[2] || 1) };
}
function identifyFromPattern(id, pattern) {
  if (id.startsWith("work_phase")) {
    const match = /^practice\.restock\.(worker[0-9]*)\.phase!Value$/.exec(pattern || "");
    assert(match, `Unknown work-phase pattern: ${pattern}`);
    return { workers: [person(match[1], "worker")], visitors: [], pairs: [] };
  }
  if (id.startsWith("request_status")) {
    const match = /^practice\.request\.(worker[0-9]*)\.(visitor[0-9]*)\.status!Value$/.exec(pattern || "");
    assert(match, `Unknown request-status pattern: ${pattern}`);
    return { workers: [person(match[1], "worker")], visitors: [person(match[2], "visitor")], pairs: [[match[1], match[2]]] };
  }
  if (id === "workspace") {
    assert(pattern === "world.workspace.state!Value", `Unknown workspace pattern: ${pattern}`);
    return { workers: [], visitors: [], pairs: [] };
  }
  throw new Error(`Unknown fact projection type: ${id}`);
}
function factsToEntries(facts, source) {
  assert(Array.isArray(facts), "Facts must be an array");
  if (source === "baseline") {
    return facts.map(f => {
      assert(Array.isArray(f), "Malformed baseline fact tuple");
      if (f.length === 3 && f[0] === "work_phase") {
        person(f[1], "worker"); assert(PHASES.has(f[2]), `Unknown work phase: ${f[2]}`);
        return { kind: "work", worker: f[1], value: f[2] };
      }
      if (f.length === 4 && f[0] === "request_status") {
        person(f[1], "worker"); person(f[2], "visitor"); assert(REQUESTS.has(f[3]), `Unknown request status: ${f[3]}`);
        return { kind: "request", worker: f[1], visitor: f[2], value: f[3] };
      }
      if (f.length === 2 && f[0] === "workspace_open" && f[1] === "true") return { kind: "workspace", value: "open" };
      throw new Error(`Unknown baseline fact: ${JSON.stringify(f)}`);
    });
  }
  assert(source === "praxish", `Unknown data source: ${source}`);
  return facts.flatMap(record => {
    assert(record && typeof record === "object" && Array.isArray(record.matches), "Malformed Praxish fact record");
    const descriptor = identifyFromPattern(record.id, record.pattern);
    return record.matches.map(match => {
      assert(match && typeof match.Value === "string", `Malformed value binding in ${record.id}`);
      if (record.id.startsWith("work_phase")) {
        assert(PHASES.has(match.Value), `Unknown work phase: ${match.Value}`);
        return { kind: "work", worker: descriptor.workers[0].id, value: match.Value };
      }
      if (record.id.startsWith("request_status")) {
        assert(REQUESTS.has(match.Value), `Unknown request status: ${match.Value}`);
        return { kind: "request", worker: descriptor.workers[0].id, visitor: descriptor.visitors[0].id, value: match.Value };
      }
      assert(match.Value === "open", `Unknown workspace state: ${match.Value}`);
      return { kind: "workspace", value: "open" };
    });
  });
}
function discoverEntities(turns, source) {
  const workers = new Set(), visitors = new Set(), pairs = new Set();
  const addActor = actor => {
    assert(typeof actor === "string", "Missing actor identity");
    const role = /^(worker|visitor)[0-9]*$/.exec(actor)?.[1];
    assert(role, `Unknown actor identity: ${actor}`);
    (role === "worker" ? workers : visitors).add(actor);
  };
  const addFacts = facts => {
    const entries = factsToEntries(facts, source);
    for (const entry of entries) {
      if (entry.worker) workers.add(entry.worker);
      if (entry.visitor) visitors.add(entry.visitor);
      if (entry.kind === "request") pairs.add(`${entry.worker}\u0000${entry.visitor}`);
    }
    if (source === "praxish") for (const record of facts) {
      const parsed = identifyFromPattern(record.id, record.pattern);
      parsed.workers.forEach(x => workers.add(x.id)); parsed.visitors.forEach(x => visitors.add(x.id));
      parsed.pairs.forEach(([w, v]) => pairs.add(`${w}\u0000${v}`));
    }
  };
  for (const turn of turns) {
    addActor(turn.actor);
    addFacts(turn.pre_facts); addFacts(turn.post_facts);
    const events = source === "baseline" ? turn.applied_events || [] : turn.event || [];
    for (const event of events) { addFacts(event.facts_before); addFacts(event.facts_after); }
  }
  return { workers: [...workers].sort(entitySort), visitors: [...visitors].sort(entitySort), pairs: [...pairs].sort() };
}
function entitySort(a, b) {
  const pa = /^(worker|visitor)([0-9]*)$/.exec(a), pb = /^(worker|visitor)([0-9]*)$/.exec(b);
  return pa[1].localeCompare(pb[1]) || Number(pa[2] || 1) - Number(pb[2] || 1);
}
function labelMap(entities, prefix) { return new Map(entities.map((id, i) => [id, `${prefix}${i + 1}`])); }
function setConsistent(map, key, value, kind) {
  if (map.has(key) && map.get(key) !== value) throw new Error(`Conflicting ${kind} state for ${key}: ${map.get(key)} vs ${value}`);
  map.set(key, value);
}
function projectSnapshot(facts, source, context) {
  const entries = factsToEntries(facts, source);
  const work = new Map(), requests = new Map();
  let workspaceOpen = false;
  for (const entry of entries) {
    if (entry.kind === "work") setConsistent(work, entry.worker, entry.value, "work-phase");
    if (entry.kind === "request") setConsistent(requests, `${entry.worker}\u0000${entry.visitor}`, entry.value, "request");
    if (entry.kind === "workspace") workspaceOpen = true;
  }
  return {
    workers: context.entities.workers.map(id => ({ label: context.workerLabels.get(id), phase: work.get(id) || null })),
    visitors: context.entities.visitors.map(id => ({ label: context.visitorLabels.get(id) })),
    requests: [...requests.entries()].map(([key, status]) => {
      const [worker, visitor] = key.split("\u0000");
      return { worker: context.workerLabels.get(worker), visitor: context.visitorLabels.get(visitor), status };
    }).sort((a, b) => a.worker.localeCompare(b.worker) || a.visitor.localeCompare(b.visitor)),
    workspace: context.workspaceApplicable ? (workspaceOpen ? "open" : "closed") : null
  };
}
function normalizeAction(turn, source, context) {
  if (!turn.selected) return { label: "本回合无可执行动作", target: null };
  let key = null, actorFromName = null, targetFromName = null;
  if (source === "baseline") key = turn.selected.template_id;
  else {
    const name = turn.selected.name;
    if (typeof name !== "string") throw new Error("Malformed selected Praxish action");
    let match;
    if ((match = /^(worker[0-9]*): Start restocking$/.exec(name))) { key = "start_restocking"; actorFromName = match[1]; }
    else if ((match = /^(worker[0-9]*): Finish restocking$/.exec(name))) { key = "finish_restocking"; actorFromName = match[1]; }
    else if ((match = /^(worker[0-9]*): Answer (visitor[0-9]*)'s request$/.exec(name))) { key = "answer_request"; actorFromName = match[1]; targetFromName = match[2]; }
    else if ((match = /^(visitor[0-9]*): Wait for (worker[0-9]*) to answer$/.exec(name))) { key = "wait_for_answer"; actorFromName = match[1]; targetFromName = match[2]; }
    else if ((match = /^(visitor[0-9]*): Cancel (worker[0-9]*)'s request$/.exec(name))) { key = "cancel_request"; actorFromName = match[1]; targetFromName = match[2]; }
  }
  assert(ACTIONS.has(key), `Unknown selected action: ${source === "baseline" ? key : turn.selected?.name}`);
  const actorRole = ["start_restocking", "finish_restocking", "answer_request"].includes(key) ? "Worker" : "Visitor";
  const targetRole = key === "answer_request" ? "Visitor" : ["wait_for_answer", "cancel_request"].includes(key) ? "Worker" : null;
  const binding = source === "baseline" ? turn.selected.binding : turn.selected.bindings;
  const roles = turn.selected.roles;
  assert(binding && typeof binding === "object" && !Array.isArray(binding), `Malformed selected ${source} binding for ${key}`);
  assert(roles && typeof roles === "object" && !Array.isArray(roles), `Malformed selected ${source} roles for ${key}`);
  if (source === "baseline") {
    assert(binding[actorRole] === turn.actor && roles[actorRole] === turn.actor, `Selected-action actor binding does not match turn actor: ${turn.actor}`);
  } else {
    assert(binding.Actor === turn.actor && actorFromName === turn.actor, `Selected-action actor binding/name does not match turn actor: ${turn.actor}`);
    assert(binding[actorRole] === turn.actor && roles[actorRole] === turn.actor, `Selected-action role binding does not match turn actor: ${turn.actor}`);
  }
  let target = null;
  if (targetRole) {
    const targetId = source === "baseline" ? binding[targetRole] : targetFromName;
    person(targetId, targetRole === "Worker" ? "worker" : "visitor");
    assert(binding[targetRole] === targetId && roles[targetRole] === targetId, `Selected-action target binding mismatch for ${key}`);
    if (source === "praxish") assert(targetFromName === binding[targetRole], `Praxish action-name target does not match binding for ${key}`);
    const targetLabels = targetRole === "Worker" ? context.workerLabels : context.visitorLabels;
    target = targetLabels.get(targetId);
    assert(target, `Selected-action target is not in projected roster: ${targetId}`);
  }
  return { label: ACTIONS.get(key), target };
}
function normalizeEvent(event, source, context) {
  assert(EVENTS.has(event.id), `Unknown event id: ${event.id}`);
  const before = projectSnapshot(event.facts_before, source, context);
  const after = projectSnapshot(event.facts_after, source, context);
  const beforeRequests = new Set(before.requests.map(r => `${r.worker}\u0000${r.visitor}\u0000${r.status}`));
  const targets = after.requests.filter(r => !beforeRequests.has(`${r.worker}\u0000${r.visitor}\u0000${r.status}`)).map(r => `${r.visitor} → ${r.worker}`);
  return { label: EVENTS.get(event.id), targets, before, after };
}
function projectTurn(turn, source, context) {
  const role = person(turn.actor, /^(worker)/.test(turn.actor) ? "worker" : "visitor").role;
  const label = role === "worker" ? context.workerLabels.get(turn.actor) : context.visitorLabels.get(turn.actor);
  assert(label, `Actor was not included in projected roster: ${turn.actor}`);
  const events = source === "baseline" ? turn.applied_events || [] : turn.event || [];
  return {
    turn: turn.turn,
    actor: label,
    action: normalizeAction(turn, source, context),
    pre: projectSnapshot(turn.pre_facts, source, context),
    events: events.map(event => normalizeEvent(event, source, context)),
    post: projectSnapshot(turn.post_facts, source, context)
  };
}
function projectCase(row, caseNumber, assignment = { A: "baseline", B: "praxish" }) {
  assert(row && row.baseline && row.praxish, "Malformed paired case row");
  const sources = { A: assignment.A, B: assignment.B };
  for (const side of ["A", "B"]) assert(["baseline", "praxish"].includes(sources[side]), `Unknown source for ${side}`);
  const turns = { baseline: row.baseline.turns, praxish: row.praxish.turns };
  assert(Array.isArray(turns.baseline) && Array.isArray(turns.praxish) && turns.baseline.length === turns.praxish.length, `Turn count mismatch in ${row.case_id}`);
  const roster = {
    workers: [...new Set(["baseline", "praxish"].flatMap(s => discoverEntities(turns[s], s).workers))].sort(entitySort),
    visitors: [...new Set(["baseline", "praxish"].flatMap(s => discoverEntities(turns[s], s).visitors))].sort(entitySort)
  };
  const workspaceApplicable = ["baseline", "praxish"].some(source => turns[source].some(t => {
    const allEvents = source === "baseline" ? t.applied_events || [] : t.event || [];
    return (source === "praxish" && [...(t.pre_facts || []), ...(t.post_facts || [])].some(f => f.id === "workspace")) || allEvents.some(e => e.id.startsWith("workspace_"));
  }));
  const contexts = {};
  for (const source of ["baseline", "praxish"]) contexts[source] = { entities: roster, workerLabels: labelMap(roster.workers, "员工 "), visitorLabels: labelMap(roster.visitors, "访客 "), workspaceApplicable };
  const frames = [];
  for (let i = 0; i < turns.baseline.length; i++) {
    const b = projectTurn(turns.baseline[i], "baseline", contexts.baseline);
    const p = projectTurn(turns.praxish[i], "praxish", contexts.praxish);
    assert(b.turn === p.turn && b.actor === p.actor, `Unaligned turn/actor at ${row.case_id}:${i}`);
    frames.push({ turn: b.turn, A: projectTurn(turns[sources.A][i], sources.A, contexts[sources.A]), B: projectTurn(turns[sources.B][i], sources.B, contexts[sources.B]) });
  }
  return { label: `场景 ${String(caseNumber).padStart(2, "0")}`, turns: frames };
}
function assignmentFor(seed, caseCount) {
  let state = Number(seed);
  assert(Number.isSafeInteger(state) && state >= 0 && state <= 0xffffffff, "Presentation seed must be an unsigned 32-bit integer");
  const assignments = [];
  for (let i = 0; i < caseCount; i++) {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    assignments.push(state & 1 ? { A: "baseline", B: "praxish" } : { A: "praxish", B: "baseline" });
  }
  return assignments;
}
function projectRun(caseResults, presentationSeed) {
  assert(Array.isArray(caseResults) && caseResults.length === 12, "Expected the complete 12-case DEVELOPMENT input");
  const assignments = assignmentFor(presentationSeed, caseResults.length);
  const cases = caseResults.map((row, i) => projectCase(row, i + 1, assignments[i]));
  let samePairs = 0, differentPairs = 0, identicalCases = 0, differentCases = 0;
  for (const scene of cases) {
    let caseDifferent = false;
    for (const frame of scene.turns) {
      const { A, B } = frame;
      if (same({ actor: A.actor, action: A.action, pre: A.pre, events: A.events, post: A.post }, { actor: B.actor, action: B.action, pre: B.pre, events: B.events, post: B.post })) samePairs++;
      else { differentPairs++; caseDifferent = true; }
    }
    if (caseDifferent) differentCases++; else identicalCases++;
  }
  assert(differentPairs > 0, "No public behavioral difference was found in the supplied cases");
  assert(identicalCases === 11 && differentCases === 1, `Expected 11 identical and 1 divergent case pair, observed ${identicalCases} and ${differentCases}`);
  return { dataset: "DEVELOPMENT", scenes: cases, summary: { case_count: cases.length, identical_case_pairs: identicalCases, different_case_pairs: differentCases, identical_turn_pairs: samePairs, different_turn_pairs: differentPairs } };
}
function parseArgs(argv) {
  const values = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith("--")) throw new Error(`Unexpected argument: ${argv[i]}`);
    const key = argv[i].slice(2);
    if (key === "test-mutate-unknown-action") { values[key] = true; continue; }
    assert(argv[i + 1] && !argv[i + 1].startsWith("--"), `Missing value for --${key}`);
    values[key] = argv[++i];
  }
  assert(values["run-id"] && values["presentation-id"] && values["presentation-seed"] !== undefined, "Usage: node presentation/export.mjs --run-id RUN --presentation-id FRESH_ID --presentation-seed UINT32");
  return values;
}
function safeId(id) { assert(/^[A-Za-z0-9][A-Za-z0-9._-]{1,79}$/.test(id), `Unsafe id: ${id}`); return id; }
function inlineJson(value) { return JSON.stringify(value).replaceAll("<", "\\u003c").replaceAll(">", "\\u003e").replaceAll("&", "\\u0026"); }
function writeExclusive(file, contents) { fs.writeFileSync(file, contents, { flag: "wx" }); }
function main(values) {
  const runId = safeId(values["run-id"]), presentationId = safeId(values["presentation-id"]);
  const seed = Number(values["presentation-seed"]);
  const inputDir = path.join(RUNS, runId), manifestPath = path.join(inputDir, "manifest.json"), resultsPath = path.join(inputDir, "case_results.json");
  assert(fs.existsSync(manifestPath) && fs.existsSync(resultsPath), `Comparison run is incomplete: ${runId}`);
  const sourceManifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  assert(sourceManifest.status === "succeeded_with_documented_upstream_behavioral_divergence", `Comparison run is not successful: ${sourceManifest.status}`);
  const outDir = path.join(PRESENTATIONS, presentationId);
  fs.mkdirSync(PRESENTATIONS, { recursive: true }); fs.mkdirSync(outDir, { recursive: false });
  const head = execFileSync("git", ["rev-parse", "HEAD"], { cwd: ROOT, encoding: "utf8" }).trim();
  const manifest = {
    presentation_id: presentationId, status: "running", dataset: "DEVELOPMENT", presentation_seed: seed,
    input_run_id: runId, input_hashes: { comparison_manifest_sha256: fileHash(manifestPath), case_results_sha256: fileHash(resultsPath) },
    generator_sha256: fileHash(fileURLToPath(import.meta.url)), template_sha256: fileHash(TEMPLATE), git_head: head,
    output_files: ["viewer.html", "reviewer_metadata.json"], started_at: new Date().toISOString()
  };
  writeExclusive(path.join(outDir, "manifest.json"), json(manifest));
  try {
    const rows = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
    if (values["test-mutate-unknown-action"]) rows[0].baseline.turns[0].selected.template_id = "test_only_unknown_action";
    const assignments = assignmentFor(seed, rows.length);
    const publicData = projectRun(rows, seed);
    const reviewerMetadata = {
      note: "DEVELOPMENT-only identity key. The page is inspectable and revealable; this is not a blinded participant study.",
      input_run_id: runId, presentation_seed: seed,
      source_key: { baseline: "Flat parameterized utility baseline", praxish: "Praxish AIIDE 2023 release" },
      case_key: rows.map((row, i) => ({ label: `场景 ${String(i + 1).padStart(2, "0")}`, case_id: row.case_id, A: assignments[i].A, B: assignments[i].B }))
    };
    const template = fs.readFileSync(TEMPLATE, "utf8");
    const html = template.replace("__PUBLIC_DATA__", inlineJson(publicData)).replace("__REVIEWER_DATA__", inlineJson(reviewerMetadata));
    assert(!html.includes("__PUBLIC_DATA__") && !html.includes("__REVIEWER_DATA__"), "Viewer template placeholders were not fully replaced");
    writeExclusive(path.join(outDir, "viewer.html"), html);
    writeExclusive(path.join(outDir, "reviewer_metadata.json"), json(reviewerMetadata));
    Object.assign(manifest, { status: "succeeded", scene_count: publicData.summary.case_count, identical_case_pairs: publicData.summary.identical_case_pairs, different_case_pairs: publicData.summary.different_case_pairs, identical_turn_pairs: publicData.summary.identical_turn_pairs, different_turn_pairs: publicData.summary.different_turn_pairs, completed_at: new Date().toISOString() });
    fs.writeFileSync(path.join(outDir, "manifest.json"), json(manifest));
    process.stdout.write(`${outDir}\n`);
  } catch (error) {
    writeExclusive(path.join(outDir, "error.json"), json({ message: error.message, stack: error.stack || null }));
    Object.assign(manifest, { status: "failed", completed_at: new Date().toISOString() });
    fs.writeFileSync(path.join(outDir, "manifest.json"), json(manifest));
    throw error;
  }
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))) {
  try { main(parseArgs(process.argv.slice(2))); }
  catch (error) { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; }
}

export { factsToEntries, discoverEntities, projectSnapshot, projectCase, assignmentFor, projectRun };
