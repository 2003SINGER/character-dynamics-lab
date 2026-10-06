import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { assignmentFor, projectCase, projectRun, projectSnapshot } from "./export.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../../..");
const runId = process.env.PRESENTATION_RUN_ID || "comparison-final-contract-audit-20261007-01";
const runDir = path.join(ROOT, "outputs/praxish_utility_comparison_v0/runs", runId);
const rows = JSON.parse(fs.readFileSync(path.join(runDir, "case_results.json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x));
const seed = 42;

function fixedProjection(caseId) {
  const row = rows.find(x => x.case_id === caseId);
  assert.ok(row, `missing fixture case ${caseId}`);
  return projectCase(row, rows.indexOf(row) + 1, { A: "baseline", B: "praxish" });
}
function allText(node) { return node.textContent + node.children.map(allText).join(""); }
class FakeNode {
  constructor(tag = "div") { this.tagName = tag; this.children = []; this.listeners = {}; this.attributes = {}; this.value = ""; this.disabled = false; this._text = ""; }
  get options() { return this.children.filter(x => x.tagName === "option"); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; }
  addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); }
  setAttribute(key, value) { this.attributes[key] = value; }
  dispatch(type) { for (const fn of this.listeners[type] || []) fn({ target: this }); }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text; }
}
function runViewer(publicData, reviewerData) {
  const source = fs.readFileSync(path.join(HERE, "viewer.template.html"), "utf8")
    .replace("__PUBLIC_DATA__", JSON.stringify(publicData))
    .replace("__REVIEWER_DATA__", JSON.stringify(reviewerData));
  const script = source.match(/<script>\s*([\s\S]*?)\s*<\/script>/)?.[1];
  assert.ok(script, "inline viewer script not found");
  const ids = ["scene", "prev", "next", "play", "reveal", "position", "disclosure", "paneA", "paneB"];
  const nodes = Object.fromEntries(ids.map(id => [id, new FakeNode(id === "scene" ? "select" : "div")]));
  let timerCallback = null, cleared = false;
  const context = { document: { getElementById: id => nodes[id], createElement: tag => new FakeNode(tag) }, setInterval: fn => { timerCallback = fn; return 7; }, clearInterval: id => { assert.equal(id, 7); cleared = true; }, console };
  vm.runInNewContext(script, context, { timeout: 1000 });
  return { nodes, viewer: context.__presentationViewer, timer: () => timerCallback?.(), wasCleared: () => cleared };
}

test("public projector yields 11 identical and one raw-alias divergent case; labels are counterbalanced", () => {
  const a = projectRun(rows, seed), b = projectRun(rows, seed);
  assert.deepEqual(a, b);
  assert.deepEqual(a.summary, { case_count: 12, identical_case_pairs: 11, different_case_pairs: 1, identical_turn_pairs: 97, different_turn_pairs: 7 });
  const sideCounts = assignmentFor(seed, 12).reduce((counts, x) => { counts[x.A]++; return counts; }, { baseline: 0, praxish: 0 });
  assert.deepEqual(sideCounts, { baseline: 6, praxish: 6 });
  assert.ok(!JSON.stringify(a).includes("case_id") && !JSON.stringify(a).includes("praxish") && !JSON.stringify(a).includes("baseline"));
  const assignments = a.scenes.map((_, i) => projectCase(rows[i], i + 1, { A: "baseline", B: "praxish" }));
  assert.equal(assignments.length, 12);
  const viewer = fs.readFileSync(path.join(HERE, "viewer.template.html"), "utf8").toLowerCase();
  assert.ok(!viewer.includes("fetch(") && !viewer.includes("http://") && !viewer.includes("https://"));
});

test("no-request, request, and low-priority paired public trajectories remain reproducible", () => {
  for (const id of ["no_request", "request", "lowpriority"]) {
    const scene = fixedProjection(id);
    for (const frame of scene.turns) assert.deepEqual(frame.A, frame.B, id);
  }
  const no = fixedProjection("no_request");
  assert.equal(no.turns[1].A.action.label, "本回合无可执行动作");
  assert.equal(no.turns[1].A.actor, "访客 1");
  assert.equal(fixedProjection("request").turns[2].A.action.label, "回应访客请求");
  assert.equal(fixedProjection("request").turns[2].A.action.target, "访客 1");
  assert.deepEqual(fixedProjection("request").turns[1].A.events[0].targets, ["访客 1 → 员工 1"]);
  assert.equal(fixedProjection("lowpriority").turns[2].A.action.label, "完成备货");
});

test("raw alias displays recorded Cancel and downstream status/work divergence", () => {
  const scene = fixedProjection("request_cancellation_low_motivation");
  assert.equal(scene.turns[1].A.action.label, "等待回应");
  assert.equal(scene.turns[1].B.action.label, "取消请求");
  assert.equal(scene.turns[1].A.action.target, "员工 1");
  assert.equal(scene.turns[1].B.action.target, "员工 1");
  assert.equal(scene.turns[1].A.post.requests[0].status, "pending");
  assert.equal(scene.turns[1].B.post.requests[0].status, "cancelled");
  assert.equal(scene.turns[2].A.action.label, "回应访客请求");
  assert.equal(scene.turns[2].A.action.target, "访客 1");
  assert.equal(scene.turns[2].B.action.label, "完成备货");
  assert.equal(scene.turns[2].A.post.requests[0].status, "served");
  assert.equal(scene.turns[2].B.post.workers[0].phase, "complete");
});

test("multi-entity empty turns and adapted closed/reopened workspace remain visible", () => {
  const pairedRow = rows.find(x => x.case_id === "second_worker_visitor_pair");
  const paired = projectCase(pairedRow, rows.indexOf(pairedRow) + 1, { A: "baseline", B: "praxish" });
  assert.equal(paired.turns.length, 12);
  assert.deepEqual(paired.turns[0].A.pre.workers.map(x => x.label), ["员工 1", "员工 2"]);
  assert.equal(paired.turns[3].A.action.label, "本回合无可执行动作");
  assert.deepEqual(paired.turns[3].A.post.visitors.map(x => x.label), ["访客 1", "访客 2"]);
  const multiRow = rows.find(x => x.case_id === "multiple_requests_one_worker");
  const multi = projectCase(multiRow, rows.indexOf(multiRow) + 1, { A: "baseline", B: "praxish" });
  for (const side of ["A", "B"]) {
    const answerTargets = new Set(multi.turns.map(frame => frame[side].action).filter(a => a.label === "回应访客请求").map(a => a.target));
    assert.deepEqual([...answerTargets].sort(), ["访客 1", "访客 2"]);
  }
  const closed = fixedProjection("workspace_closure_adapted");
  assert.equal(closed.turns[2].A.pre.workspace, "closed");
  assert.equal(closed.turns[2].A.action.label, "本回合无可执行动作");
  assert.equal(closed.turns[6].A.pre.workspace, "open");
  assert.equal(closed.turns[6].A.action.label, "完成备货");
  assert.equal(closed.turns[6].A.post.workers[0].phase, "complete");
});

test("unknown actor, action, event, and fact fail loudly instead of disappearing", () => {
  const unknownActor = clone(rows.find(x => x.case_id === "no_request")); unknownActor.baseline.turns[0].actor = "stranger";
  assert.throws(() => projectCase(unknownActor, 1), /Unknown actor identity/);
  const unknownAction = clone(rows.find(x => x.case_id === "no_request")); unknownAction.baseline.turns[0].selected.template_id = "dance";
  assert.throws(() => projectCase(unknownAction, 1), /Unknown selected action/);
  const unknownPraxishAction = clone(rows.find(x => x.case_id === "no_request")); unknownPraxishAction.praxish.turns[0].selected.name = "worker: Dance and Cancel";
  assert.throws(() => projectCase(unknownPraxishAction, 1), /Unknown selected action/);
  const mismatchedActor = clone(rows.find(x => x.case_id === "no_request")); mismatchedActor.praxish.turns[0].selected.bindings.Actor = "visitor";
  assert.throws(() => projectCase(mismatchedActor, 1), /actor binding\/name does not match turn actor/);
  const mismatchedBaselineActor = clone(rows.find(x => x.case_id === "request")); mismatchedBaselineActor.baseline.turns[2].selected.binding.Worker = "worker2";
  assert.throws(() => projectCase(mismatchedBaselineActor, 1), /actor binding does not match turn actor/);
  const mismatchedTarget = clone(rows.find(x => x.case_id === "multiple_requests_one_worker"));
  const answer = mismatchedTarget.praxish.turns.find(t => t.selected?.name.includes("Answer"));
  answer.selected.bindings.Visitor = answer.selected.bindings.Visitor === "visitor" ? "visitor2" : "visitor";
  assert.throws(() => projectCase(mismatchedTarget, 1), /target binding mismatch|action-name target does not match binding/);
  const malformedBinding = clone(rows.find(x => x.case_id === "request")); delete malformedBinding.praxish.turns[2].selected.bindings;
  assert.throws(() => projectCase(malformedBinding, 1), /Malformed selected praxish binding/);
  const unknownEvent = clone(rows.find(x => x.case_id === "request")); unknownEvent.baseline.turns[1].applied_events[0].id = "surprise";
  assert.throws(() => projectCase(unknownEvent, 1), /Unknown event id/);
  assert.throws(() => projectSnapshot([["secret_fact", "x"]], "baseline", { entities: { workers: [], visitors: [] }, workerLabels: new Map(), visitorLabels: new Map(), workspaceApplicable: false }), /Unknown baseline fact/);
  const snapshotContext = { entities: { workers: ["worker"], visitors: [] }, workerLabels: new Map([["worker", "员工 1"]]), visitorLabels: new Map(), workspaceApplicable: false };
  assert.throws(() => projectSnapshot([["work_phase", "worker", "working"], ["work_phase", "worker", "complete"]], "baseline", snapshotContext), /Conflicting work-phase state/);
  const conflictingPraxish = [{ id: "work_phase", pattern: "practice.restock.worker.phase!Value", matches: [{ Value: "working" }, { Value: "complete" }] }];
  assert.throws(() => projectSnapshot(conflictingPraxish, "praxish", snapshotContext), /Conflicting work-phase state/);
});

test("viewer navigation, empty turn, playback, dropdown and optional source disclosure work without browser services", () => {
  const publicData = projectRun(rows, seed);
  const reviewerData = { source_key: { baseline: "Flat utility baseline", praxish: "Praxish AIIDE 2023 release" }, case_key: rows.map((r, i) => ({ label: publicData.scenes[i].label, case_id: r.case_id, A: i % 2 ? "baseline" : "praxish", B: i % 2 ? "praxish" : "baseline" })) };
  const { nodes, viewer, timer, wasCleared } = runViewer(publicData, reviewerData);
  assert.equal(viewer.getState().turnIndex, 0);
  assert.ok(!allText(nodes.disclosure).includes("baseline") && !allText(nodes.disclosure).includes("Praxish"));
  viewer.step(1); assert.equal(viewer.getState().turnIndex, 1);
  viewer.selectScene(0); viewer.step(1); assert.equal(nodes.paneA.children.some(x => allText(x).includes("本回合无可执行动作")), true);
  nodes.play.dispatch("click"); assert.equal(viewer.getState().playing, true); timer(); assert.equal(viewer.getState().turnIndex, 2);
  nodes.play.dispatch("click"); assert.equal(viewer.getState().playing, false); assert.equal(wasCleared(), true);
  nodes.scene.value = "1"; nodes.scene.dispatch("change"); assert.equal(viewer.getState().sceneIndex, 1); assert.equal(viewer.getState().turnIndex, 0);
  viewer.step(1);
  nodes.reveal.dispatch("click"); assert.equal(viewer.getState().reveal, true); assert.match(nodes.disclosure.textContent, /开发来源揭示/);
  assert.ok(allText(nodes.paneA).includes("参与角色：访客"));
  assert.ok(allText(nodes.paneA).includes("事件处理后／行动前状态"));
  assert.ok(allText(nodes.paneA).includes("访客 1 → 员工 1"));
  nodes.reveal.dispatch("click"); assert.equal(nodes.disclosure.textContent, "");
});

test("CLI preserves malformed-action failure and refuses to overwrite the presentation", () => {
  const runner = path.join(HERE, "export.mjs");
  const presentationId = `test-unknown-action-${process.pid}-${Date.now()}`;
  const outDir = path.join(ROOT, "outputs/praxish_utility_comparison_v0/presentation", presentationId);
  const args = [runner, "--run-id", runId, "--presentation-id", presentationId, "--presentation-seed", "4"];
  const failed = spawnSync(process.execPath, [...args, "--test-mutate-unknown-action"], { cwd: ROOT, encoding: "utf8" });
  assert.equal(failed.status, 1, failed.stderr);
  assert.equal(JSON.parse(fs.readFileSync(path.join(outDir, "manifest.json"), "utf8")).status, "failed");
  assert.match(fs.readFileSync(path.join(outDir, "error.json"), "utf8"), /Unknown selected action/);
  const before = fs.readFileSync(path.join(outDir, "manifest.json"));
  const second = spawnSync(process.execPath, args, { cwd: ROOT, encoding: "utf8" });
  assert.equal(second.status, 1);
  assert.deepEqual(fs.readFileSync(path.join(outDir, "manifest.json")), before);
});
