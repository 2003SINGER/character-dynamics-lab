import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { runBaseline, runPraxish, checkPair, scenarioFor, readJson, runNegativeControls, inspectRawCancellationAlias, applyDiff, workspaceBehaviorAudit, verifyDocumentedCancellationDivergence, auditPraxishConstraints } from "./compare.mjs";
import { verifyArtifact } from "../../Praxish_Activity_Pilot_v0/tools/pilot.mjs";

test("pinned Praxish source is verified without edits", () => { assert.equal(verifyArtifact().tag, "aiide-23"); });
test("base paired cases have matching candidates, scores, and actor order", () => {
  for (const [id, opts] of [["no_request", {}], ["request", { request: true }], ["lowpriority", { request: true, low: true }]]) {
    assert.equal(checkPair(id, runBaseline(id, { seed: "0x5eed1234", ...opts }), runPraxish(id, "0x5eed1234")).passed, true, id);
  }
});
test("selected score and binding are checked against the exact selected instance", () => {
  const b = runBaseline("request", { seed: "0x5eed1234", request: true });
  const p = runPraxish("request", "0x5eed1234");
  p.turns[2].selected.score_reported_by_original_tick += 1;
  const badScore = checkPair("request", b, p);
  assert.ok(badScore.issues.some(i => i.kind === "selected_reported_score_mismatch"));
  p.turns[2].selected.score_reported_by_original_tick -= 1;
  p.turns[2].selected.roles.Visitor = "visitor2";
  assert.equal(checkPair("request", b, p).passed, false);
});
test("request changes eligible actions without prescribing selection", () => {
  const no = runBaseline("no_request", { seed: 1 }); const yes = runBaseline("request", { seed: 1, request: true });
  assert.ok(!no.turns[2].candidates.some(c => c.template_id === "answer_request"));
  assert.ok(yes.turns[2].candidates.some(c => c.template_id === "answer_request"));
});
test("authored role binding prevents visitors from using worker actions", () => {
  const trace = runBaseline("request", { seed: 1, request: true });
  assert.ok(trace.turns[1].candidates.every(c => c.template_id === "wait_for_answer"));
});
test("multiple requests multiply absolute goal matches and share templates", () => {
  const config = readJson(new URL("../utility_baseline.json", import.meta.url));
  assert.equal(config.action_templates.filter(x => x.id === "answer_request").length, 1);
  const b = runBaseline("second_worker_visitor_pair", { seed: 1, request: true, count: 2 });
  assert.equal(b.turns.length, 12);
  assert.ok(b.turns.some(t => t.post_facts.some(f => f[0] === "work_phase" && f[1] === "worker2" && f[2] === "complete")));
  const pairPraxis = runPraxish("second_worker_visitor_pair", 1);
  assert.equal(checkPair("second_worker_visitor_pair", b, pairPraxis).passed, true);
  const pairFinal = pairPraxis.turns.at(-1).post_facts.flatMap(f => f.matches.map(m => [f.id, m.Value]));
  assert.ok(pairFinal.some(([id, phase]) => id === "work_phase_2" && phase === "complete"));
  const multi = runBaseline("multiple_requests_one_worker", { seed: 1, request: true, multiRequests: true });
  const answerWithTwoServed = multi.turns.flatMap(t => t.candidates).find(c => c.template_id === "answer_request" && c.goal_scores.some(g => g.matches === 2));
  assert.equal(answerWithTwoServed?.goal_scores.find(g => g.goal_id === "serve_visitor")?.absolute_score_contribution, 20);
  assert.equal(multi.turns.length, 12);
  assert.ok(multi.turns.some(t => t.post_facts.filter(f => f[0] === "request_status" && f[3] === "served").length === 2 && t.post_facts.some(f => f[0] === "work_phase" && f[2] === "complete")));
  assert.equal(checkPair("multiple_requests_one_worker", multi, runPraxish("multiple_requests_one_worker", 1)).passed, true);
});
test("low-priority and equal-score conditions are authored preference changes", () => {
  const defaultRun = runBaseline("request", { seed: 1, request: true });
  const lowRun = runBaseline("lowpriority", { seed: 1, request: true, low: true });
  assert.notEqual(defaultRun.turns[2].selected.template_id, lowRun.turns[2].selected.template_id);
  const tied = runBaseline("equal_score_tie", { seed: 1, request: true, tie: true });
  const scored = tied.turns[2].candidates.filter(x => x.score === Math.max(...tied.turns[2].candidates.map(y => y.score)));
  assert.equal(scored.length, 2);
});
test("equal-score tie is reproducible and explores both choices over 32 seeds", () => {
  const choices = new Set();
  for (let seed = 0; seed < 32; seed++) {
    const a = runBaseline("equal_score_tie", { seed, request: true, tie: true });
    const b = runBaseline("equal_score_tie", { seed, request: true, tie: true });
    const p = runPraxish("equal_score_tie", seed);
    assert.deepEqual(a, b); assert.equal(checkPair("equal_score_tie", a, p).passed, true, `seed ${seed}`); choices.add(a.turns[2].selected.template_id);
  }
  assert.deepEqual([...choices].sort(), ["answer_request", "finish_restocking"]);
});
test("workspace contract is witnessed on both sides and adaptation blocks only while closed", () => {
  const rawB = runBaseline("workspace_closure_unadapted", { seed: "0x5eed1234", closure: true });
  const rawP = runPraxish("workspace_closure_unadapted", "0x5eed1234");
  const rawRow = { baseline: rawB, praxish: rawP, praxish_constraint_audit: auditPraxishConstraints(rawP, true) };
  assert.equal(workspaceBehaviorAudit(rawRow, false).passed, true);
  const adaptedScenario = scenarioFor("workspace_closure_adapted", "0x5eed1234");
  assert.ok(adaptedScenario.practices.find(p => p.id === "restock").actions.find(a => a.name.includes("Finish")).conditions.includes("world.workspace.state!open"));
  const adaptedB = runBaseline("workspace_closure_adapted", { seed: "0x5eed1234", closure: true, adapted: true });
  const adaptedP = runPraxish("workspace_closure_adapted", "0x5eed1234");
  const adaptedRow = { baseline: adaptedB, praxish: adaptedP, praxish_constraint_audit: auditPraxishConstraints(adaptedP, true) };
  assert.equal(workspaceBehaviorAudit(adaptedRow, true).passed, true);
  assert.ok(adaptedB.turns.some(t => t.turn >= 5 && t.selected?.template_id === "finish_restocking" && t.post_facts.some(f => f[0] === "work_phase" && f[2] === "complete")));
  assert.ok(adaptedP.turns.some(t => t.turn >= 5 && t.selected?.name.includes("Finish restocking") && t.post_facts.some(f => f.id === "work_phase" && f.matches.some(m => m.Value === "complete"))));
  // Remove both authored eligibility conditions: parity alone could pass, but the public contract must fail.
  const badConfig = readJson(new URL("../utility_baseline.json", import.meta.url));
  const finish = badConfig.action_templates.find(t => t.id === "finish_restocking");
  finish.preconditions.push(badConfig.extensions.workspace_filter.precondition);
  finish.preconditions = finish.preconditions.filter(p => !p.fact.includes("workspace_open"));
  const badScenario = scenarioFor("workspace_closure_adapted", "0x5eed1234");
  const badAction = badScenario.practices.find(p => p.id === "restock").actions.find(a => a.name.includes("Finish"));
  badAction.conditions = badAction.conditions.filter(c => !c.includes("world.workspace.state!open"));
  const sharedBadB = runBaseline("workspace_closure_adapted", { seed: "0x5eed1234", closure: true, configOverride: badConfig });
  const sharedBadP = runPraxish("workspace_closure_adapted", "0x5eed1234", badScenario);
  const sharedBadRow = { baseline: sharedBadB, praxish: sharedBadP, praxish_constraint_audit: auditPraxishConstraints(sharedBadP, true) };
  assert.equal(checkPair("workspace_closure_adapted", sharedBadB, sharedBadP).passed, true);
  assert.equal(workspaceBehaviorAudit(sharedBadRow, true).passed, false);
});
test("cancellation and second pair scenarios reuse declarative practices", () => {
  const cancel = scenarioFor("request_cancellation", "0x5eed1234");
  assert.ok(cancel.practices.find(p => p.id === "request").actions.some(a => a.name.includes("Cancel")));
  const pair = scenarioFor("second_worker_visitor_pair", "0x5eed1234");
  assert.deepEqual(pair.characters.map(c => c.name), ["worker", "worker2", "visitor", "visitor2"]);
});
test("raw cancellation alias and low-motivation behavior are reproduced; explicit binding restores parity", () => {
  const rawScenario = scenarioFor("request_cancellation", "0x5eed1234");
  const alias = inspectRawCancellationAlias(rawScenario);
  assert.equal(alias.candidate_count, 2); assert.equal(alias.same_object_identity, true);
  assert.deepEqual(alias.action_ids, ["[Actor]: Cancel [Worker]'s request", "[Actor]: Cancel [Worker]'s request"]);
  const lowB = runBaseline("request_cancellation_low_motivation", { seed: "0x5eed1234", request: true, cancellation: true, cancelLow: true });
  const lowP = runPraxish("request_cancellation_low_motivation", "0x5eed1234");
  assert.equal(lowB.turns[1].selected.template_id, "wait_for_answer");
  assert.match(lowP.turns[1].selected.name, /Cancel/);
  assert.equal(checkPair("request_cancellation_low_motivation", lowB, lowP).passed, false);
  const rawB = runBaseline("request_cancellation", { seed: "0x5eed1234", request: true, cancellation: true });
  const rawP = runPraxish("request_cancellation", "0x5eed1234");
  const normalRow = { case_id: "request_cancellation", baseline: rawB, praxish: rawP, parity: checkPair("request_cancellation", rawB, rawP) };
  const lowRow = { case_id: "request_cancellation_low_motivation", baseline: lowB, praxish: lowP, parity: checkPair("request_cancellation_low_motivation", lowB, lowP) };
  const aliasAudit = { raw: alias };
  assert.equal(verifyDocumentedCancellationDivergence([normalRow, lowRow], aliasAudit).passed, true);
  lowRow.parity.issues.push({ turn: 6, kind: "selected_reported_score_mismatch" });
  assert.equal(verifyDocumentedCancellationDivergence([normalRow, lowRow], aliasAudit).passed, false, "later-turn corruption must not be whitelisted");
  lowRow.parity.issues.pop();
  lowRow.parity.issues.push({ turn: 1, kind: "selected_reported_score_mismatch" });
  assert.equal(verifyDocumentedCancellationDivergence([normalRow, lowRow], aliasAudit).passed, false, "extra turn-1 score mismatch must not be whitelisted");
  lowRow.parity.issues.pop();
  const workaroundB = runBaseline("cancellation_explicit_binding_workaround", { seed: "0x5eed1234", request: true, cancellation: true });
  const workaroundP = runPraxish("cancellation_explicit_binding_workaround", "0x5eed1234");
  assert.equal(inspectRawCancellationAlias(scenarioFor("cancellation_explicit_binding_workaround", "0x5eed1234")).same_object_identity, false);
  assert.equal(checkPair("cancellation_explicit_binding_workaround", workaroundB, workaroundP).passed, true);
  const lowWorkaroundB = runBaseline("cancellation_explicit_binding_workaround_low_motivation", { seed: "0x5eed1234", request: true, cancellation: true, cancelLow: true });
  const lowWorkaroundP = runPraxish("cancellation_explicit_binding_workaround_low_motivation", "0x5eed1234");
  assert.equal(checkPair("cancellation_explicit_binding_workaround_low_motivation", lowWorkaroundB, lowWorkaroundP).passed, true);
  assert.equal(lowWorkaroundB.turns[1].selected.template_id, "wait_for_answer");
});
test("negative controls execute corrupted baselines and parity gate detects each", () => {
  assert.deepEqual(runNegativeControls("0x5eed1234").map(x => [x.id, x.detected]), [["bad_effect", true], ["bad_role", true], ["bad_filter", true]]);
});
test("CLI preserves failed evidence and refuses to overwrite a run ID", () => {
  const dir = path.dirname(fileURLToPath(import.meta.url));
  const runner = path.join(dir, "compare.mjs");
  const repo = path.resolve(dir, "../../..");
  const id = `test-preserve-${Date.now().toString(36)}`;
  const run = () => spawnSync(process.execPath, [runner, "run", "--run-id", id, "--test-fail-after-artifacts"], { cwd: repo, encoding: "utf8" });
  const first = run(); assert.equal(first.status, 1);
  const out = path.join(repo, "outputs/praxish_utility_comparison_v0/runs", id);
  assert.equal(JSON.parse(fs.readFileSync(path.join(out, "manifest.json"), "utf8")).status, "failed");
  assert.ok(fs.existsSync(path.join(out, "error.json")));
  assert.ok(fs.existsSync(path.join(out, "case_results.json")));
  const extensionRoot = path.join(out, "extensions");
  for (const name of fs.readdirSync(extensionRoot)) {
    const ext = path.join(extensionRoot, name);
    assert.deepEqual(applyDiff(JSON.parse(fs.readFileSync(path.join(ext, "before.json"), "utf8")), JSON.parse(fs.readFileSync(path.join(ext, "diff.json"), "utf8"))), JSON.parse(fs.readFileSync(path.join(ext, "after.json"), "utf8")));
  }
  const manifestHash = fs.readFileSync(path.join(out, "manifest.json"));
  assert.equal(run().status, 1);
  assert.deepEqual(fs.readFileSync(path.join(out, "manifest.json")), manifestHash);
});
