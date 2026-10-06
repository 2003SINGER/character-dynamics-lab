import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { readScenario, runScenario, verifyArtifact } from "../../Praxish_Activity_Pilot_v0/tools/pilot.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../../..");
const OUTPUT = path.join(ROOT, "outputs/praxish_utility_comparison_v0/runs");
const CONFIG = path.resolve(HERE, "..", "utility_baseline.json");
const CASES = path.resolve(HERE, "..", "cases.json");
const CONTRACT = path.resolve(HERE, "..", "world_contract.json");
const NONINTERACTIVE = path.join(ROOT, "outputs/praxish_activity_pilot_v0/source-cache/artifact/noninteractive");
const PILOT_DIR = path.resolve(HERE, "../../Praxish_Activity_Pilot_v0");
const sha = p => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const assert = (v, m) => { if (!v) throw new Error(m); };
const readJson = p => JSON.parse(fs.readFileSync(p, "utf8"));
const clone = x => JSON.parse(JSON.stringify(x));
const FACTS = {
  "practice.restock.worker.phase!waiting": ["work_phase", "worker", "waiting"],
  "practice.restock.worker.phase!working": ["work_phase", "worker", "working"],
  "practice.restock.worker.phase!complete": ["work_phase", "worker", "complete"],
  "practice.request.worker.visitor.status!pending": ["request_status", "worker", "visitor", "pending"],
  "practice.request.worker.visitor.status!served": ["request_status", "worker", "visitor", "served"],
  "practice.request.worker.visitor.status!cancelled": ["request_status", "worker", "visitor", "cancelled"]
};
const BASE_FACTS = [FACTS["practice.restock.worker.phase!waiting"]];
const LCG = seed => {
  const spec = readJson(CONTRACT).rng;
  assert(spec.algorithm === "LCG32" && spec.multiplier === 1664525 && spec.increment === 1013904223 && spec.modulus === 4294967296, "Unsupported RNG descriptor");
  let s = Number(seed) >>> 0;
  return () => { s = (Math.imul(s, spec.multiplier) + spec.increment) >>> 0; return s / spec.modulus; };
};
const canonical = x => Array.isArray(x) ? x.map(canonical) : x && typeof x === "object" ? Object.fromEntries(Object.keys(x).sort().map(k => [k, canonical(x[k])])) : x;
const eq = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

function term(pattern, binding) { return pattern.map(x => typeof x === "string" && /^\{[^}]+\}$/.test(x) ? binding[x.slice(1, -1)] : x); }
function unify(pattern, fact, initial = {}) {
  if (pattern.length !== fact.length) return null;
  const b = { ...initial };
  for (let i = 0; i < pattern.length; i++) {
    const x = pattern[i], y = fact[i];
    if (typeof x === "string" && /^\{[^}]+\}$/.test(x)) { const key = x.slice(1, -1); if (b[key] !== undefined && b[key] !== y) return null; b[key] = y; }
    else if (x !== y) return null;
  }
  return b;
}
function matchAll(pattern, facts, initial = {}) { return facts.flatMap(f => { const b = unify(pattern, f, initial); return b ? [b] : []; }); }

function enumerate(template, actor, facts, config, adapted) {
  let bindings = [{}];
  for (const [role, mode] of Object.entries(template.roles)) {
    const entities = config.roles[role] || [];
    const choices = entities;
    bindings = bindings.flatMap(b => choices.map(entity => ({ ...b, [role]: entity })));
  }
  const out = [];
  for (const binding of bindings) {
    if (template.actor_role && binding[template.actor_role] !== actor) continue;
    let partial = [binding];
    for (const pre of template.preconditions) partial = partial.flatMap(b => matchAll(term(pre.fact, b), facts, b));
    for (const b of partial) out.push({ template_id: template.id, practice_instance: template.practice_instance.replace(/\{([^}]+)\}/g, (_, key) => b[key]), roles: Object.fromEntries(Object.keys(template.roles).map(r => [r, b[r]])), binding: b });
  }
  return out;
}
function substitute(pattern, binding) { return pattern.map(x => typeof x === "string" && /^\{[^}]+\}$/.test(x) ? binding[x.slice(1, -1)] : x); }
function effectFacts(facts, cand, config) {
  const out = facts.map(clone);
  const t = config.action_templates.find(x => x.id === cand.template_id);
  for (const pat of t.delete) { const f = substitute(pat, cand.binding); const i = out.findIndex(x => eq(x, f)); if (i >= 0) out.splice(i, 1); }
  for (const pat of t.insert) { const f = substitute(pat, cand.binding); if (!out.some(x => eq(x, f))) out.push(f); }
  return out;
}
function scoreCandidate(cand, post, actor, goals, actorRole) {
  const details = [];
  let score = 0;
  for (const g of goals.filter(x => x.actor_role === actorRole)) {
    let count = 0;
    const initial = { actor };
    const matches = matchAll(g.match, post, initial);
    count = g.count_bindings ? matches.length : (matches.length ? 1 : 0);
    const contribution = g.weight * count;
    details.push({ goal_id: g.id, utility: g.weight, matches: count, absolute_score_contribution: contribution }); score += contribution;
  }
  return { ...cand, score, goal_scores: details };
}
function baselineConfig({ low = false, tie = false, cancellation = false, cancelLow = false, adapted = false, count = 1, multiRequests = false, configOverride = null } = {}) {
  const config = clone(configOverride || readJson(CONFIG));
  const casePrefs = readJson(CASES);
  if (low) config.goal_factors.find(g => g.id === "serve_visitor").weight = casePrefs.preferences.lowpriority.serve_visitor;
  if (tie) config.goal_factors.find(g => g.id === "serve_visitor").weight = casePrefs.tie_preferences.serve_visitor;
  if (cancellation) { config.action_templates.push(...config.extensions.cancel_request.action_templates); config.goal_factors.push(...config.extensions.cancel_request.goal_factors); }
  if (cancelLow && cancellation) config.goal_factors.find(g => g.id === "cancel_request").weight = casePrefs.preferences.cancel_low_motivation.cancel_request;
  if (adapted) config.action_templates.find(t => t.id === "finish_restocking").preconditions.push(config.extensions.workspace_filter.precondition);
  config.roles.Worker = count > 1 ? ["worker", "worker2"] : ["worker"];
  config.roles.Visitor = multiRequests ? ["visitor", "visitor2"] : count > 1 ? ["visitor", "visitor2"] : ["visitor"];
  return config;
}
function runBaseline(caseId, { seed, request = false, low = false, count = 1, adapted = false, tie = false, cancellation = false, cancelLow = false, closure = false, multiRequests = false, configOverride = null } = {}) {
  const config = baselineConfig({ low, tie, cancellation, cancelLow, adapted, count, multiRequests, configOverride });
  const facts = [];
  for (const w of config.roles.Worker) facts.push(["work_phase", w, "waiting"]);
  if (closure) facts.push(["workspace_open", "true"]);
  const turns = [];
  const rand = LCG(seed);
  const caseConfig = readJson(CASES);
  const actorOrder = caseConfig.actor_orders[caseId] || caseConfig.actor_orders.default;
  let actorIdx = -1;
  const totalTurns = caseConfig.case_turns?.[caseId] || caseConfig.turns;
  for (let turn = 0; turn < totalTurns; turn++) {
    const appliedEvents = [];
    if (request && turn === caseConfig.events.request.before_turn) for (let i = 0; i < (multiRequests ? 2 : count); i++) {
      const wi = multiRequests ? 0 : i;
      const before = clone(facts); facts.push(["request_status", config.roles.Worker[wi], config.roles.Visitor[i], "pending"]);
      appliedEvents.push({ id: i ? "second_visible_request" : "visible_request", facts_before: before, facts_after: clone(facts) });
    }
    if (closure && turn === caseConfig.events.close.before_turn) {
      const before = clone(facts); const i = facts.findIndex(f => eq(f, ["workspace_open", "true"])); if (i >= 0) facts.splice(i, 1);
      appliedEvents.push({ id: "workspace_closed", facts_before: before, facts_after: clone(facts) });
    }
    if (closure && turn === caseConfig.events.reopen.before_turn) { const before = clone(facts); facts.push(["workspace_open", "true"]); appliedEvents.push({ id: "workspace_reopened", facts_before: before, facts_after: clone(facts) }); }
    actorIdx = (actorIdx + 1) % actorOrder.length;
    const actor = actorOrder[actorIdx];
    const pre = clone(facts);
    const actorRole = Object.entries(config.roles).find(([, entities]) => entities.includes(actor))?.[0];
    let candidates = config.action_templates.filter(t => t.actor_role === actorRole)
      .flatMap(t => enumerate(t, actor, facts, config, adapted))
      .map(c => scoreCandidate(c, effectFacts(facts, c, config), actor, config.goal_factors, actorRole));
    if (!candidates.length) { turns.push({ turn, actor, applied_events: appliedEvents, pre_facts: pre, candidates: [], selected: null, post_facts: clone(facts) }); continue; }
    const max = Math.max(...candidates.map(c => c.score));
    const tops = candidates.filter(c => c.score === max);
    const picked = tops[Math.floor(rand() * tops.length)];
    const prior = clone(facts);
    facts.splice(0, facts.length, ...effectFacts(facts, picked, config));
    const rule = readJson(CONTRACT).hard_constraints.find(x => x.action === picked.template_id);
    const violation = closure && rule?.when.some(test => test === "workspace_open=false") && !facts.some(f => eq(f, ["workspace_open", "true"])) ? rule.violation : null;
    turns.push({ turn, actor, applied_events: appliedEvents, pre_facts: pre, candidates, selected: picked, post_facts: clone(facts), constraint_violation: violation, changed_facts: { before: prior, after: clone(facts) } });
  }
  return { case_id: caseId, seed, turns };
}

function scenarioFor(caseId, seed) {
  const caseConfig = readJson(CASES);
  const s = clone(readScenario()); s.seed = seed; s.turns = caseConfig.case_turns?.[caseId] || caseConfig.turns; s.conditions = { run: { events: [] } };
  s.characters.find(c => c.name === "worker").goals.find(g => g.id === "serve_visitor").conditions = ["practice.request.worker.Visitor.status!served"];
  const cancellationCase = ["request_cancellation", "request_cancellation_low_motivation", "cancellation_explicit_binding_workaround", "cancellation_explicit_binding_workaround_low_motivation"].includes(caseId);
  const request = ["request", "lowpriority", "equal_score_tie", "second_worker_visitor_pair", "multiple_requests_one_worker"].includes(caseId) || cancellationCase;
  if (request) s.conditions.run.events.push({ before_turn: caseConfig.events.request.before_turn, id: "visible_request", outcome: "insert practice.request.worker.visitor" });
  if (caseId === "lowpriority") s.characters.find(c => c.name === "worker").goals.find(g => g.id === "serve_visitor").utility = caseConfig.preferences.lowpriority.serve_visitor;
  if (caseId === "equal_score_tie") s.characters.find(c => c.name === "worker").goals.find(g => g.id === "serve_visitor").utility = caseConfig.tie_preferences.serve_visitor;
  if (["workspace_closure_unadapted", "workspace_closure_adapted"].includes(caseId)) {
    s.trace_fact_patterns.push({ id: "workspace", pattern: "world.workspace.state!Value" });
    s.initial_practice_instances.push("insert world.workspace.state!open");
    s.conditions.run.events.push({ before_turn: caseConfig.events.close.before_turn, id: "workspace_closed", outcome: "delete world.workspace.state" });
    s.conditions.run.events.push({ before_turn: caseConfig.events.reopen.before_turn, id: "workspace_reopened", outcome: "insert world.workspace.state!open" });
    if (caseId === "workspace_closure_adapted") s.practices.find(p => p.id === "restock").actions.find(a => a.name.includes("Finish restocking")).conditions.push("world.workspace.state!open");
  }
  if (cancellationCase) {
    const requestP = s.practices.find(p => p.id === "request");
    const conditions = ["eq Actor Visitor", "practice.request.Worker.Visitor.status!pending"];
    if (caseId.startsWith("cancellation_explicit_binding_workaround")) conditions.splice(1, 1, "practice.request.Worker.Visitor.status!Status", "eq Status pending");
    requestP.actions.push({ name: "[Actor]: Cancel [Worker]'s request", conditions, outcomes: ["delete practice.request.Worker.Visitor.status", "insert practice.request.Worker.Visitor.status!cancelled"] });
    const cancelUtility = caseId.includes("low_motivation") ? readJson(CASES).preferences.cancel_low_motivation.cancel_request : readJson(CASES).preferences.default.cancel_request;
    s.characters.find(c => c.name === "visitor").goals.push({ id: "cancel_request", utility: cancelUtility, conditions: ["practice.request.worker.visitor.status!cancelled"] });
  }
  if (caseId === "second_worker_visitor_pair") {
    const secondWorkerGoals = clone(s.characters[0].goals).map(g => ({ ...g, conditions: g.conditions.map(c => c.replaceAll("worker", "worker2")) }));
    s.characters.splice(1, 0, { name: "worker2", goals: secondWorkerGoals });
    s.characters.push({ name: "visitor2", goals: [] });
    s.initial_practice_instances.push("insert practice.restock.worker2");
    s.conditions.run.events.push({ before_turn: 1, id: "second_visible_request", outcome: "insert practice.request.worker2.visitor2" });
    s.trace_fact_patterns.push({ id: "work_phase_2", pattern: "practice.restock.worker2.phase!Value" }, { id: "request_status_2", pattern: "practice.request.worker2.visitor2.status!Value" });
  }
  if (caseId === "multiple_requests_one_worker") {
    s.characters.push({ name: "visitor2", goals: [] });
    s.conditions.run.events.push({ before_turn: caseConfig.events.request.before_turn, id: "second_visible_request", outcome: "insert practice.request.worker.visitor2" });
    s.trace_fact_patterns.push({ id: "request_status_2", pattern: "practice.request.worker.visitor2.status!Value" });
  }
  const order = caseConfig.actor_orders[caseId] || caseConfig.actor_orders.default;
  s.characters.sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
  return s;
}
function inspectRawCancellationAlias(scenario) {
  verifyArtifact();
  const sandbox = { console: { log() {}, warn() {}, error() {} }, __fixture: clone(scenario) };
  vm.createContext(sandbox);
  for (const name of ["db.js", "praxish.js"]) vm.runInContext(fs.readFileSync(path.join(NONINTERACTIVE, name), "utf8"), sandbox, { filename: name });
  const diagnostic = vm.runInContext(`(() => {
    const state = createPraxishState(); state.allChars = __fixture.characters;
    for (const practice of __fixture.practices) definePractice(state, clone(practice));
    for (const outcome of __fixture.initial_practice_instances) performOutcome(state, outcome);
    for (const event of __fixture.conditions.run.events.filter(e => e.before_turn === 1)) performOutcome(state, event.outcome);
    const candidates = getAllPossibleActions(state, "visitor");
    return { candidate_count: candidates.length, same_object_identity: candidates.length === 2 && candidates[0] === candidates[1], action_ids: candidates.map(c => c.actionID), names: candidates.map(c => c.name) };
  })()`, sandbox);
  return JSON.parse(JSON.stringify(diagnostic));
}
function runPraxish(caseId, seed, scenarioOverride = null) {
  const s = scenarioOverride || scenarioFor(caseId, seed);
  return runScenario("run", { scenario: s });
}
function actionId(name) {
  if (!name) return null;
  if (name.includes("Finish restocking")) return "finish_restocking";
  if (name.includes("Start restocking")) return "start_restocking";
  if (name.includes("Answer")) return "answer_request";
  if (name.includes("Wait for")) return "wait_for_answer";
  if (name.includes("Cancel")) return "cancel_request";
  return name.toLowerCase().replaceAll(" ", "_");
}
function normalizedPraxish(trace) {
  return trace.turns.map(t => {
    const selectedCandidate = t.selected && t.candidates.find(c => c.action_id === t.selected.action_id && c.instance_id === t.selected.instance_id && eq(c.roles, t.selected.roles));
    return { turn: t.turn, actor: t.actor, candidates: t.candidates.map(c => ({ id: actionId(c.name), instance_id: c.instance_id, score: c.score, roles: c.roles, goal_scores: c.goal_scores })), selected: t.selected && { id: actionId(t.selected.name), instance_id: t.selected.instance_id, score: t.selected.score_reported_by_original_tick, candidate_score: selectedCandidate?.score ?? null, roles: t.selected.roles } };
  });
}
function projectPraxishFacts(facts) {
  return facts.flatMap(f => f.matches.flatMap(bind => {
    if (f.id.startsWith("work_phase")) return [["work_phase", f.pattern.includes("worker2") ? "worker2" : "worker", bind.Value]];
    if (f.id.startsWith("request_status")) return [["request_status", f.pattern.includes("worker2") ? "worker2" : "worker", f.pattern.includes("visitor2") ? "visitor2" : "visitor", bind.Value]];
    if (f.id === "workspace") return bind.Value === "open" ? [["workspace_open", "true"]] : [];
    return [];
  }));
}
function projectBaselineFacts(facts) {
  return facts.filter(f => ["work_phase", "request_status", "workspace_open"].includes(f[0]));
}
function checkPair(caseId, baseline, praxis) {
  const issues = [];
  const pn = normalizedPraxish(praxis);
  if (baseline.turns.length !== pn.length) issues.push({ kind: "turn_length", baseline: baseline.turns.length, praxish: pn.length });
  for (let i = 0; i < Math.max(baseline.turns.length, pn.length); i++) {
    const b = baseline.turns[i], p = pn[i];
    if (!b || !p) continue;
    if (b.actor !== p.actor) issues.push({ turn: i, kind: "actor_order", baseline: b.actor, praxish: p.actor });
    const bc = b.candidates.map(c => ({ id: c.template_id, instance_id: c.practice_instance, score: c.score, roles: c.roles, goal_scores: c.goal_scores }));
    const pc = p.candidates.map(c => ({ id: c.id, instance_id: c.instance_id, score: c.score, roles: c.roles, goal_scores: c.goal_scores }));
    if (!eq(bc, pc)) issues.push({ turn: i, kind: "candidate_score_role_parity", baseline: bc, praxish: pc });
    const bsel = b.selected && { id: b.selected.template_id, instance_id: b.selected.practice_instance, score: b.selected.score, roles: b.selected.roles };
    const psel = p.selected && { id: p.selected.id, instance_id: p.selected.instance_id, score: p.selected.score, roles: p.selected.roles };
    if (p.selected && p.selected.score !== p.selected.candidate_score) issues.push({ turn: i, kind: "selected_reported_score_mismatch", selected: p.selected.score, candidate_score: p.selected.candidate_score, id: p.selected.id, instance_id: p.selected.instance_id });
    if (!eq(bsel, psel)) issues.push({ turn: i, kind: "selected_action_parity", baseline: bsel, praxish: psel });
    const bpre = projectBaselineFacts(b.pre_facts).sort((x,y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
    const ppre = projectPraxishFacts(praxis.turns[i].pre_facts).sort((x,y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
    if (!eq(bpre, ppre)) issues.push({ turn: i, kind: "pre_state_parity", baseline: bpre, praxish: ppre });
    const bfacts = projectBaselineFacts(b.post_facts).sort((x,y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
    const pfacts = projectPraxishFacts(praxis.turns[i].post_facts).sort((x,y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
    if (!eq(bfacts, pfacts)) issues.push({ turn: i, kind: "post_state_parity", baseline: bfacts, praxish: pfacts });
    const bevent = b.applied_events || [];
    const sortFacts = xs => xs.sort((x,y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
    const pevent = praxis.turns[i].event.map(e => ({ id: e.id, facts_before: sortFacts(projectPraxishFacts(e.facts_before)), facts_after: sortFacts(projectPraxishFacts(e.facts_after)) }));
    const projectedBevent = bevent.map(e => ({ id: e.id, facts_before: sortFacts(projectBaselineFacts(e.facts_before)), facts_after: sortFacts(projectBaselineFacts(e.facts_after)) }));
    if (!eq(projectedBevent, pevent)) issues.push({ turn: i, kind: "event_parity", baseline: projectedBevent, praxish: pevent });
  }
  return { case_id: caseId, passed: issues.length === 0, issues };
}
function auditPraxishConstraints(trace, closure) {
  const rules = readJson(CONTRACT).hard_constraints;
  return trace.turns.map(t => {
    const action = actionId(t.selected?.name);
    const closed = !projectPraxishFacts(t.pre_facts).some(f => f[0] === "workspace_open" && f[1] === "true");
    const rule = rules.find(r => r.action === action);
    return { turn: t.turn, action, violations: closure && closed && rule ? [{ rule_id: rule.id, message: rule.violation }] : [] };
  });
}
function workspaceBehaviorAudit(row, adapted) {
  const failures = [];
  const closed = new Set([1, 2, 3, 4]);
  for (const side of ["baseline", "praxish"]) {
    const turns = row[side].turns;
    const selected = t => side === "baseline" ? t.selected?.template_id || null : actionId(t.selected?.name) || null;
    const violationAt = t => side === "baseline" ? Boolean(t.constraint_violation) : row.praxish_constraint_audit.find(x => x.turn === t.turn)?.violations.length > 0;
    if (!adapted) {
      const witnessed = turns.some(t => closed.has(t.turn) && selected(t) === "finish_restocking" && violationAt(t));
      if (!witnessed) failures.push(`${side}: missing closed-workspace finish violation`);
      continue;
    }
    for (const t of turns.filter(x => closed.has(x.turn))) {
      if (selected(t) === "finish_restocking") failures.push(`${side}: finish selected while closed at turn ${t.turn}`);
      if (violationAt(t)) failures.push(`${side}: constraint violation while closed at turn ${t.turn}`);
    }
    const afterReopen = turns.find(t => t.turn >= 5 && selected(t) === "finish_restocking");
    if (!afterReopen) failures.push(`${side}: no finish after reopening`);
    else {
      const complete = side === "baseline"
        ? afterReopen.post_facts.some(f => f[0] === "work_phase" && f[1] === "worker" && f[2] === "complete")
        : projectPraxishFacts(afterReopen.post_facts).some(f => f[0] === "work_phase" && f[1] === "worker" && f[2] === "complete");
      if (!complete) failures.push(`${side}: work did not reach complete after reopening`);
    }
  }
  return { passed: failures.length === 0, failures };
}
function verifyDocumentedCancellationDivergence(rows, aliases) {
  const raw = rows.find(r => r.case_id === "request_cancellation");
  const low = rows.find(r => r.case_id === "request_cancellation_low_motivation");
  const failures = [];
  const issueSignature = row => row.parity.issues.map(i => `${i.turn}:${i.kind}`);
  if (!raw || !low) return { passed: false, failures: ["missing raw cancellation rows"] };
  const rawExpected = ["1:candidate_score_role_parity"];
  const lowExpected = ["1:candidate_score_role_parity", "1:selected_action_parity", "1:post_state_parity", "2:candidate_score_role_parity", "2:selected_action_parity", "2:pre_state_parity", "2:post_state_parity", "3:pre_state_parity", "3:post_state_parity", "4:candidate_score_role_parity", "4:selected_action_parity", "4:pre_state_parity", "4:post_state_parity", "5:pre_state_parity", "5:post_state_parity", "6:pre_state_parity", "6:post_state_parity", "7:pre_state_parity", "7:post_state_parity"];
  if (!eq(issueSignature(raw), rawExpected)) failures.push("raw cancellation issues differ from the sole documented turn-1 candidate alias");
  if (!eq(issueSignature(low), lowExpected)) failures.push("low-motivation cancellation issue chain differs from the documented alias propagation");
  const aliasValid = aliases.raw?.candidate_count === 2 && aliases.raw.same_object_identity === true && aliases.raw.action_ids?.length === 2 && aliases.raw.action_ids[0] === aliases.raw.action_ids[1] && aliases.raw.names?.every(n => n.includes("Cancel"));
  if (!aliasValid) failures.push("raw source identity probe did not confirm duplicate Cancel object alias");
  const actionTimeline = row => row.turns.map(t => row === raw.baseline || row === low.baseline ? t.selected?.template_id || null : actionId(t.selected?.name) || null);
  if (!eq(actionTimeline(raw.baseline), actionTimeline(raw.praxish))) failures.push("normal-preference raw cancellation public action timeline changed");
  const stateTimeline = (row, praxis) => row.turns.map(t => ({ pre: (praxis ? projectPraxishFacts(t.pre_facts) : projectBaselineFacts(t.pre_facts)).sort(), post: (praxis ? projectPraxishFacts(t.post_facts) : projectBaselineFacts(t.post_facts)).sort() }));
  if (!eq(stateTimeline(raw.baseline, false), stateTimeline(raw.praxish, true))) failures.push("normal-preference raw cancellation public fact timeline changed");
  const baselineTimeline = actionTimeline(low.baseline), praxishTimeline = actionTimeline(low.praxish);
  if (!eq(baselineTimeline, ["start_restocking", "wait_for_answer", "answer_request", null, "finish_restocking", null, null, null])) failures.push("low-motivation baseline action timeline no longer matches documented chain");
  if (!eq(praxishTimeline, ["start_restocking", "cancel_request", "finish_restocking", null, null, null, null, null])) failures.push("low-motivation Praxish action timeline no longer matches documented alias chain");
  const pendingWorking = [["request_status", "worker", "visitor", "pending"], ["work_phase", "worker", "working"]];
  const servedWorking = [["request_status", "worker", "visitor", "served"], ["work_phase", "worker", "working"]];
  const cancelledWorking = [["request_status", "worker", "visitor", "cancelled"], ["work_phase", "worker", "working"]];
  const servedComplete = [["request_status", "worker", "visitor", "served"], ["work_phase", "worker", "complete"]];
  const cancelledComplete = [["request_status", "worker", "visitor", "cancelled"], ["work_phase", "worker", "complete"]];
  const expectedBStates = [
    { pre: [["work_phase", "worker", "waiting"]], post: [["work_phase", "worker", "working"]] },
    { pre: pendingWorking, post: pendingWorking }, { pre: pendingWorking, post: servedWorking },
    { pre: servedWorking, post: servedWorking }, { pre: servedWorking, post: servedComplete },
    ...Array.from({ length: 3 }, () => ({ pre: servedComplete, post: servedComplete }))
  ];
  const expectedPStates = [
    { pre: [["work_phase", "worker", "waiting"]], post: [["work_phase", "worker", "working"]] },
    { pre: pendingWorking, post: cancelledWorking }, { pre: cancelledWorking, post: cancelledComplete },
    ...Array.from({ length: 5 }, () => ({ pre: cancelledComplete, post: cancelledComplete }))
  ];
  if (!eq(stateTimeline(low.baseline, false), expectedBStates)) failures.push("low-motivation baseline full fact chain changed");
  if (!eq(stateTimeline(low.praxish, true), expectedPStates)) failures.push("low-motivation Praxish full fact chain changed");
  const b1 = low.baseline.turns[1], p1 = low.praxish.turns[1];
  if (b1.selected?.template_id !== "wait_for_answer" || actionId(p1.selected?.name) !== "cancel_request" || !b1.post_facts.some(f => eq(f, ["request_status", "worker", "visitor", "pending"])) || !projectPraxishFacts(p1.post_facts).some(f => eq(f, ["request_status", "worker", "visitor", "cancelled"]))) failures.push("turn-1 low-motivation branch does not show Wait-vs-aliased-Cancel facts");
  const b2 = low.baseline.turns[2], p2 = low.praxish.turns[2];
  if (b2.selected?.template_id !== "answer_request" || actionId(p2.selected?.name) !== "finish_restocking" || !b2.post_facts.some(f => eq(f, ["request_status", "worker", "visitor", "served"])) || !projectPraxishFacts(p2.post_facts).some(f => eq(f, ["work_phase", "worker", "complete"]))) failures.push("turn-2 downstream state is not the documented causal consequence");
  return { passed: failures.length === 0, failures, raw_issue_signature: issueSignature(raw), low_issue_signature: issueSignature(low) };
}
function stablePublicTimeline(caseId, turns) { return { case: caseId, turns: turns.map(t => ({ turn: t.turn, actor: t.actor, action: t.selected?.template_id || actionId(t.selected?.name) || null })) }; }
function escapePointer(s) { return String(s).replaceAll("~", "~0").replaceAll("/", "~1"); }
function structuralDiff(before, after, pointer = "") {
  if (eq(before, after)) return [];
  if (Array.isArray(before) && Array.isArray(after)) {
    const ops = [];
    const common = Math.min(before.length, after.length);
    for (let i = 0; i < common; i++) ops.push(...structuralDiff(before[i], after[i], `${pointer}/${i}`));
    for (let i = before.length - 1; i >= after.length; i--) ops.push({ op: "remove", path: `${pointer}/${i}` });
    for (let i = common; i < after.length; i++) ops.push({ op: "add", path: `${pointer}/-`, value: clone(after[i]) });
    return ops;
  }
  if (before && after && typeof before === "object" && typeof after === "object" && !Array.isArray(before) && !Array.isArray(after)) {
    const ops = [];
    for (const key of Object.keys(before)) if (!(key in after)) ops.push({ op: "remove", path: `${pointer}/${escapePointer(key)}` });
    for (const key of Object.keys(after)) {
      const p = `${pointer}/${escapePointer(key)}`;
      if (!(key in before)) ops.push({ op: "add", path: p, value: clone(after[key]) });
      else ops.push(...structuralDiff(before[key], after[key], p));
    }
    return ops;
  }
  return [{ op: "replace", path: pointer || "", value: clone(after) }];
}
function applyDiff(source, ops) {
  const root = clone(source);
  for (const op of ops) {
    const tokens = op.path === "" ? [] : op.path.slice(1).split("/").map(x => x.replaceAll("~1", "/").replaceAll("~0", "~"));
    if (!tokens.length) return clone(op.value);
    const key = tokens.pop(); let parent = root;
    for (const token of tokens) parent = parent[Array.isArray(parent) ? Number(token) : token];
    if (Array.isArray(parent)) {
      if (op.op === "remove") parent.splice(Number(key), 1);
      else if (key === "-") parent.push(clone(op.value));
      else if (op.op === "add") parent.splice(Number(key), 0, clone(op.value));
      else parent[Number(key)] = clone(op.value);
    } else if (op.op === "remove") delete parent[key];
    else parent[key] = clone(op.value);
  }
  return root;
}
function scheduleInput(caseId, opts) {
  const d = readJson(CASES);
  const events = {};
  if (opts.request) events.request = d.events.request;
  if (opts.closure) { events.close = d.events.close; events.reopen = d.events.reopen; }
  return { case_id: caseId, seed: opts.seed, turns: d.case_turns?.[caseId] || d.turns, actor_order: d.actor_orders[caseId] || d.actor_orders.default, events };
}
function diffInputs(before, after) {
  const ops = structuralDiff(before, after);
  const rebuilt = applyDiff(before, ops);
  assert(eq(rebuilt, after), "Generated extension diff did not reconstruct after inputs");
  return ops;
}
function extensionInputs(id, opts, seed) {
  let beforePraxisId = "no_request";
  let beforeOpts = { seed, request: false };
  if (["request_cancellation", "multiple_requests_one_worker", "second_worker_visitor_pair", "equal_score_tie"].includes(id)) { beforePraxisId = "request"; beforeOpts = { seed, request: true }; }
  if (id === "request_cancellation_low_motivation") { beforePraxisId = "request_cancellation"; beforeOpts = { seed, request: true, cancellation: true }; }
  if (id === "cancellation_explicit_binding_workaround") { beforePraxisId = "request_cancellation"; beforeOpts = { seed, request: true, cancellation: true }; }
  if (id === "cancellation_explicit_binding_workaround_low_motivation") { beforePraxisId = "request_cancellation_low_motivation"; beforeOpts = { seed, request: true, cancellation: true, cancelLow: true }; }
  if (id === "workspace_closure_adapted") beforePraxisId = "workspace_closure_unadapted";
  if (id === "workspace_closure_unadapted") beforePraxisId = "no_request";
  if (id === "workspace_closure_adapted") beforeOpts = { seed, closure: true };
  if (id === "workspace_closure_unadapted") beforeOpts = { seed, request: false };
  const beforeConfig = baselineConfig(beforeOpts);
  const afterConfig = baselineConfig(opts);
  const beforeScenario = scenarioFor(beforePraxisId, seed);
  const before = { utility_baseline: beforeConfig, praxish_scenario: beforeScenario, shared_case_schedule: scheduleInput(beforePraxisId, beforeOpts), world_contract: readJson(CONTRACT) };
  const after = { utility_baseline: afterConfig, praxish_scenario: scenarioFor(id, seed), shared_case_schedule: scheduleInput(id, opts), world_contract: readJson(CONTRACT) };
  return { before, after, diff: diffInputs(before, after) };
}
function runNegativeControls(seed) {
  const records = [];
  const base = readJson(CONFIG);
  const badEffect = clone(base); badEffect.action_templates.find(t => t.id === "answer_request").insert = [["request_status", "{Worker}", "{Visitor}", "cancelled"]];
  const effectPair = checkPair("request", runBaseline("request", { seed, request: true, configOverride: badEffect }), runPraxish("request", seed));
  records.push({ id: "bad_effect", detected: !effectPair.passed, issues: effectPair.issues });
  const badRole = clone(base); badRole.action_templates.find(t => t.id === "answer_request").actor_role = "Visitor";
  const rolePair = checkPair("request", runBaseline("request", { seed, request: true, configOverride: badRole }), runPraxish("request", seed));
  records.push({ id: "bad_role", detected: !rolePair.passed, issues: rolePair.issues });
  const badFilter = clone(base); badFilter.action_templates.find(t => t.id === "finish_restocking").preconditions.push(badFilter.extensions.workspace_filter.precondition);
  const filterPair = checkPair("workspace_closure_unadapted", runBaseline("workspace_closure_unadapted", { seed, closure: true, configOverride: badFilter }), runPraxish("workspace_closure_unadapted", seed));
  records.push({ id: "bad_filter", detected: !filterPair.passed, issues: filterPair.issues });
  return records;
}
function validatePublicContract() {
  const c = readJson(CONTRACT);
  assert(c.actor_order === "round_robin_in_declared_character_order", "Unsupported actor-order contract");
  assert(c.utility === "sum over authored goals of weight times post-action absolute match count", "Unsupported utility contract");
  assert(c.hard_constraints.some(x => x.id === "closed_workspace_blocks_finish" && x.action === "finish_restocking"), "Missing closure constraint descriptor");
  assert(c.rng.algorithm === "LCG32" && c.rng.multiplier === 1664525 && c.rng.increment === 1013904223 && c.rng.modulus === 4294967296, "Unsupported RNG descriptor");
  return true;
}
function safeId(id) { assert(/^[A-Za-z0-9][A-Za-z0-9._-]{1,79}$/.test(id), `Unsafe run ID ${id}`); return id; }
function mainRun(runId, { injectFailureAfterArtifacts = false } = {}) {
  const runDir = path.join(OUTPUT, safeId(runId)); fs.mkdirSync(OUTPUT, { recursive: true }); fs.mkdirSync(runDir, { recursive: false });
  const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: ROOT, encoding: "utf8" });
  const inputPaths = [CONFIG, CASES, CONTRACT, path.join(HERE, "compare.test.mjs"), fileURLToPath(import.meta.url), path.join(PILOT_DIR, "tools/pilot.mjs"), path.join(PILOT_DIR, "scenario.json")];
  const manifest = { run_id: runId, status: "running", node_version: process.version, seed: readJson(CASES).seed, git_head: head.status === 0 ? head.stdout.trim() : null, execution_from_worktree: true, runner_sha256: sha(fileURLToPath(import.meta.url)), input_hashes: Object.fromEntries(inputPaths.map(p => [path.relative(ROOT, p), sha(p)])), source_pin: null, started_at: new Date().toISOString() };
  fs.writeFileSync(path.join(runDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n", { flag: "wx" });
  try {
    validatePublicContract();
    manifest.source_pin = verifyArtifact();
    const caseDoc = readJson(CASES);
    const cases = [...caseDoc.base_cases, ...caseDoc.extensions];
    const rows = [];
    const extensionRecords = {};
    for (const id of cases) {
      const cancellation = ["request_cancellation", "request_cancellation_low_motivation", "cancellation_explicit_binding_workaround", "cancellation_explicit_binding_workaround_low_motivation"].includes(id);
      const opts = { seed: caseDoc.seed, request: !["no_request", "workspace_closure_unadapted", "workspace_closure_adapted"].includes(id), low: id === "lowpriority", count: id === "second_worker_visitor_pair" ? 2 : 1, adapted: id === "workspace_closure_adapted", closure: id === "workspace_closure_unadapted" || id === "workspace_closure_adapted", multiRequests: id === "multiple_requests_one_worker", tie: id === "equal_score_tie", cancellation, cancelLow: id.includes("low_motivation"), workaround: id.startsWith("cancellation_explicit_binding_workaround") };
      const baseline = runBaseline(id, opts); const praxish = runPraxish(id, opts.seed);
      const row = { case_id: id, baseline, praxish, praxish_constraint_audit: auditPraxishConstraints(praxish, opts.closure), parity: checkPair(id, baseline, praxish) };
      if (opts.closure) row.workspace_behavior_audit = workspaceBehaviorAudit(row, opts.adapted);
      rows.push(row);
      if (caseDoc.extensions.includes(id)) extensionRecords[id] = extensionInputs(id, opts, opts.seed);
    }
    const tieSeeds = [];
    for (let seed = 0; seed < 32; seed++) {
      const b = runBaseline("equal_score_tie", { seed, request: true, tie: true });
      const p = runPraxish("equal_score_tie", seed);
      tieSeeds.push({ seed, parity: checkPair("equal_score_tie", b, p), baseline_actions: b.turns.map(t => t.selected?.template_id || null), praxish_actions: p.turns.map(t => t.selected?.name || null) });
    }
    const negativeControls = runNegativeControls(caseDoc.seed);
    const closure = rows.find(r => r.case_id === "workspace_closure_unadapted");
    const violation = closure.baseline.turns.find(t => t.constraint_violation);
    const extensionRoot = path.join(runDir, "extensions"); fs.mkdirSync(extensionRoot, { recursive: false });
    for (const [id, record] of Object.entries(extensionRecords)) {
      const dir = path.join(extensionRoot, id); fs.mkdirSync(dir, { recursive: false });
      fs.writeFileSync(path.join(dir, "before.json"), JSON.stringify(record.before, null, 2) + "\n", { flag: "wx" });
      fs.writeFileSync(path.join(dir, "after.json"), JSON.stringify(record.after, null, 2) + "\n", { flag: "wx" });
      fs.writeFileSync(path.join(dir, "diff.json"), JSON.stringify(record.diff, null, 2) + "\n", { flag: "wx" });
    }
    const rawCancelScenario = scenarioFor("request_cancellation", caseDoc.seed);
    const workaroundScenario = scenarioFor("cancellation_explicit_binding_workaround", caseDoc.seed);
    const lowWorkaroundScenario = scenarioFor("cancellation_explicit_binding_workaround_low_motivation", caseDoc.seed);
    const rawAlias = inspectRawCancellationAlias(rawCancelScenario);
    const workaroundAlias = inspectRawCancellationAlias(workaroundScenario);
    const lowWorkaroundAlias = inspectRawCancellationAlias(lowWorkaroundScenario);
    const cancelLowRow = rows.find(r => r.case_id === "request_cancellation_low_motivation");
    const cancelRows = [rows.find(r => r.case_id === "request_cancellation"), cancelLowRow];
    const workaroundRows = [rows.find(r => r.case_id === "cancellation_explicit_binding_workaround"), rows.find(r => r.case_id === "cancellation_explicit_binding_workaround_low_motivation")];
    const rawCand = cancelRows[0].praxish.turns[1].candidates;
    const lowBaseCand = cancelRows[1].baseline.turns[1].candidates;
    const lowPraxisCand = cancelRows[1].praxish.turns[1].candidates;
    const cancellationAudit = verifyDocumentedCancellationDivergence(rows, { raw: rawAlias });
    const expectedCancellationObservation = cancellationAudit.passed && rawCand.length === 2 && rawCand.every(c => c.action_id.includes("Cancel")) && eq(lowBaseCand.map(c => [c.template_id, c.score]), [["wait_for_answer", 0], ["cancel_request", -1]]) && lowPraxisCand.length === 2 && lowPraxisCand.every(c => c.action_id.includes("Cancel") && c.score === -1) && !workaroundAlias.same_object_identity && !lowWorkaroundAlias.same_object_identity && workaroundRows.every(r => r.parity.passed);
    assert(expectedCancellationObservation, `Cancellation alias observation/workaround did not match its explicitly tested signature: ${cancellationAudit.failures.join("; ")}`);
    cancelRows[0].result_kind = "observed_upstream_candidate_alias_failure";
    cancelRows[1].result_kind = "observed_upstream_candidate_alias_behavioral_divergence";
    fs.writeFileSync(path.join(runDir, "debug_evidence.json"), JSON.stringify({ closure_constraint_violation: violation || null, workspace_behavior_audits: rows.filter(r => r.workspace_behavior_audit).map(r => ({ case_id: r.case_id, ...r.workspace_behavior_audit })), praxish_constraint_audit: rows.filter(r => r.case_id.startsWith("workspace_closure")).map(r => ({ case_id: r.case_id, turns: r.praxish_constraint_audit })), upstream_cancellation_alias: rawAlias, cancellation_divergence_audit: cancellationAudit, explicit_binding_workaround_alias: workaroundAlias, low_motivation_workaround_alias: lowWorkaroundAlias, cancellation_low_motivation_behavior: cancelLowRow && { baseline_candidates: lowBaseCand.map(c => ({ id: c.template_id, score: c.score })), praxish_candidates: lowPraxisCand.map(c => ({ id: c.action_id, name: c.name, score: c.score })), baseline_selected: cancelLowRow.baseline.turns[1].selected?.template_id, praxish_selected: cancelLowRow.praxish.turns[1].selected?.name, parity: cancelLowRow.parity }, negative_controls: negativeControls, development_failures: "See tracked DEVELOPMENT_LOG.md; no human debugging time/count captured" }, null, 2) + "\n", { flag: "wx" });
    const timelines = rows.map(r => ({ baseline: stablePublicTimeline(r.case_id, r.baseline.turns), praxish: stablePublicTimeline(r.case_id, r.praxish.turns) }));
    const timelineMismatch = timelines.filter(x => !eq(x.baseline.turns, x.praxish.turns));
    const allowedTimelineDivergences = new Set(["request_cancellation_low_motivation"]);
    const unexpectedTimelineMismatches = timelineMismatch.filter(x => !allowedTimelineDivergences.has(x.baseline.case)).map(x => x.baseline.case);
    fs.writeFileSync(path.join(runDir, "typed_timeline.json"), JSON.stringify(timelines, null, 2) + "\n", { flag: "wx" });
    fs.writeFileSync(path.join(runDir, "case_results.json"), JSON.stringify(rows, null, 2) + "\n", { flag: "wx" });
    fs.writeFileSync(path.join(runDir, "tie_seeds.json"), JSON.stringify(tieSeeds, null, 2) + "\n", { flag: "wx" });
    if (injectFailureAfterArtifacts) throw new Error("Injected CLI preservation-test failure after all artifacts were written");
    const allowedObserved = new Set(["request_cancellation", "request_cancellation_low_motivation"]);
    const unexpectedParityFailures = rows.filter(r => !r.parity.passed && !allowedObserved.has(r.case_id)).map(r => r.case_id);
    const workspaceAuditsPassed = rows.filter(r => r.workspace_behavior_audit).every(r => r.workspace_behavior_audit.passed);
    const failed = unexpectedParityFailures.length || unexpectedTimelineMismatches.length || !cancellationAudit.passed || !workspaceAuditsPassed || tieSeeds.some(x => !x.parity.passed) || negativeControls.some(x => !x.detected);
    Object.assign(manifest, { status: failed ? "failed" : "succeeded_with_documented_upstream_behavioral_divergence", cases: cases.length, parity_failures: rows.filter(r => !r.parity.passed).map(r => r.case_id), expected_upstream_divergences_verified: [...allowedObserved], unexpected_parity_failures: unexpectedParityFailures, cancellation_signature_verified: expectedCancellationObservation, cancellation_divergence_audit: cancellationAudit, timeline_mismatches: timelineMismatch.map(x => x.baseline.case), unexpected_timeline_mismatches: unexpectedTimelineMismatches, negative_controls_detected: negativeControls.filter(x => x.detected).map(x => x.id), tie_seed_count: tieSeeds.length, workspace_behavior_audits_passed: workspaceAuditsPassed, closure_constraint_violations: { baseline: Boolean(violation), praxish: rows.find(r => r.case_id === "workspace_closure_unadapted").praxish_constraint_audit.some(t => t.violations.length) }, completed_at: new Date().toISOString() });
    fs.writeFileSync(path.join(runDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
    if (failed) throw new Error(`Parity or negative-control check failed; see ${runDir}`);
    process.stdout.write(`${runDir}\n`);
  } catch (e) {
    fs.writeFileSync(path.join(runDir, "error.json"), JSON.stringify({ message: e.message, stack: e.stack || null }, null, 2) + "\n", { flag: "wx" });
    if (manifest.status === "running") manifest.status = "failed";
    manifest.completed_at = new Date().toISOString(); fs.writeFileSync(path.join(runDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n"); throw e;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [cmd, ...args] = process.argv.slice(2);
  try {
    if (cmd === "run") { const i = args.indexOf("--run-id"); assert(i >= 0 && args[i + 1], "Usage: run --run-id <fresh-id>"); mainRun(args[i + 1], { injectFailureAfterArtifacts: args.includes("--test-fail-after-artifacts") }); }
    else if (cmd === "test") { const { spawnSync } = await import("node:child_process"); const r = spawnSync(process.execPath, ["--test", path.join(HERE, "compare.test.mjs")], { stdio: "inherit" }); if (r.status !== 0) process.exitCode = 1; }
    else { process.stderr.write("Usage: node tools/compare.mjs <test|run --run-id ID>\n"); process.exitCode = 2; }
  } catch (e) { process.stderr.write(`${e.stack || e}\n`); process.exitCode = 1; }
}

export { runBaseline, runPraxish, checkPair, scenarioFor, readJson, runNegativeControls, validatePublicContract, inspectRawCancellationAlias, applyDiff, workspaceBehaviorAudit, verifyDocumentedCancellationDivergence, auditPraxishConstraints };
