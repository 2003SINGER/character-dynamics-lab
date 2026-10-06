import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { readScenario, runOriginalDemo, runScenario, verifyArtifact } from "./pilot.mjs";

const PILOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function workerTurn(trace, turn) {
  return trace.turns.find(item => item.turn === turn && item.actor === "worker");
}

test("pinned release archive and unmodified upstream files match recorded hashes", () => {
  const source = verifyArtifact();
  assert.equal(source.tag, "aiide-23");
  assert.equal(source.commit, "4729b0c469a7ecb423622f543ca116315616a76b");
  assert.deepEqual(Object.keys(source.files).sort(), ["db.js", "praxish.js", "tests.js"]);
});

test("the request event changes the worker's candidate set through practice state", () => {
  const baseline = workerTurn(runScenario("no_request"), 2);
  const requested = workerTurn(runScenario("request"), 2);
  assert.deepEqual(baseline.candidates.map(action => action.name), ["worker: Finish restocking"]);
  assert.deepEqual(requested.candidates.map(action => action.name).sort(), [
    "worker: Answer visitor's request",
    "worker: Finish restocking"
  ]);
  assert.equal(requested.event.length, 0);
  assert.equal(requested.pre_facts.find(fact => fact.id === "request_status").matches[0].Value, "pending");
});

test("actor-role conditions prevent the visitor from taking worker actions", () => {
  const requested = runScenario("request");
  const visitorTurn = requested.turns.find(item => item.turn === 1 && item.actor === "visitor");
  assert.deepEqual(visitorTurn.candidates.map(action => action.name), ["visitor: Wait for worker to answer"]);
  assert.ok(visitorTurn.candidates.every(action => action.bindings.Actor === "visitor"));
  assert.deepEqual(visitorTurn.candidates[0].roles, { Worker: "worker", Visitor: "visitor" });
  assert.ok(!visitorTurn.candidates.some(action => action.practice_id === "restock"));
});

test("the original tick selects only a maximum absolute-score candidate", () => {
  for (const condition of ["no_request", "request"]) {
    const trace = runScenario(condition);
    for (const turn of trace.turns.filter(item => item.actor === "worker" && item.candidates.length > 0)) {
      const maximum = Math.max(...turn.candidates.map(action => action.score));
      const selectedCandidate = turn.candidates.find(action =>
        action.action_id === turn.selected.action_id &&
        action.instance_id === turn.selected.instance_id &&
        JSON.stringify(action.bindings) === JSON.stringify(turn.selected.bindings)
      );
      assert.ok(selectedCandidate, `selected action missing from candidate list at ${condition} turn ${turn.turn}`);
      assert.equal(turn.selected.score_reported_by_original_tick, selectedCandidate.score);
      assert.equal(selectedCandidate.score, maximum);
      assert.equal(selectedCandidate.score, selectedCandidate.goal_scores.reduce((sum, goal) => sum + goal.absolute_score_contribution, 0));
    }
  }
});

test("answering preserves work-in-progress and the worker later finishes it", () => {
  const requested = runScenario("request");
  const answerTurn = workerTurn(requested, 2);
  const finishTurn = workerTurn(requested, 4);
  assert.equal(answerTurn.selected.name, "worker: Answer visitor's request");
  assert.equal(answerTurn.pre_facts.find(fact => fact.id === "work_phase").matches[0].Value, "working");
  assert.equal(answerTurn.post_facts.find(fact => fact.id === "work_phase").matches[0].Value, "working");
  assert.equal(answerTurn.post_facts.find(fact => fact.id === "request_status").matches[0].Value, "served");
  assert.equal(finishTurn.selected.name, "worker: Finish restocking");
  assert.equal(finishTurn.post_facts.find(fact => fact.id === "work_phase").matches[0].Value, "complete");
});

test("lower authored request priority changes the same scenario's selected action", () => {
  const lowPriority = runScenario("request", { preferenceVariant: "low_request_priority" });
  const turn2 = workerTurn(lowPriority, 2);
  const turn4 = workerTurn(lowPriority, 4);
  assert.equal(turn2.selected.name, "worker: Finish restocking");
  assert.equal(turn2.candidates.find(action => action.name === "worker: Finish restocking").score, 5);
  assert.equal(turn2.candidates.find(action => action.name === "worker: Answer visitor's request").score, 2);
  assert.equal(turn4.selected.name, "worker: Answer visitor's request");
  assert.equal(turn4.selected.score_reported_by_original_tick, 6);
  assert.equal(lowPriority.preference_variant, "low_request_priority");
});

test("same seed produces byte-equivalent typed traces", () => {
  for (const condition of ["no_request", "request"]) {
    assert.deepEqual(runScenario(condition), runScenario(condition));
  }
});

test("event only creates request activity; it does not prescribe the worker response", () => {
  const trace = runScenario("request");
  const requestEvent = trace.turns.flatMap(turn => turn.event).find(event => event.id === "visitor_arrives_with_request");
  assert.equal(requestEvent.outcome, "insert practice.request.worker.visitor");
  assert.ok(!requestEvent.outcome.includes("served"));
  assert.equal(requestEvent.facts_after.find(fact => fact.id === "request_status").matches[0].Value, "pending");
});

test("tracked paired-choice excerpt matches a fresh generated trace", () => {
  const examplePath = path.join(PILOT_DIR, "examples", "paired_choice_excerpt.json");
  const example = JSON.parse(fs.readFileSync(examplePath, "utf8"));
  const baseline = workerTurn(runScenario("no_request"), example.worker_choice_turn);
  const requestedTrace = runScenario("request");
  const requested = workerTurn(requestedTrace, example.worker_choice_turn);
  const later = workerTurn(requestedTrace, example.request.later_worker_choice_turn);
  const event = requestedTrace.turns.flatMap(turn => turn.event).find(item => item.id === "visitor_arrives_with_request");

  assert.deepEqual(baseline.candidates.map(item => ({ name: item.name, roles: item.roles, score: item.score })), example.no_request.candidates.map(({ name, roles, score }) => ({ name, roles, score })));
  assert.equal(baseline.selected.name, example.no_request.selected);
  assert.equal(baseline.post_facts.find(fact => fact.id === "work_phase").matches[0].Value, example.no_request.post_facts.work_phase);
  assert.equal(event.outcome, example.request_event.outcome);
  assert.equal(requested.selected.name, example.request.selected);
  assert.deepEqual(requested.candidates.map(item => ({ name: item.name, roles: item.roles, score: item.score })), example.request.candidates.map(({ name, roles, score }) => ({ name, roles, score })));
  assert.equal(requested.post_facts.find(fact => fact.id === "work_phase").matches[0].Value, example.request.post_facts.work_phase);
  assert.equal(later.selected.name, example.request.later_selected);
  assert.equal(later.post_facts.find(fact => fact.id === "work_phase").matches[0].Value, example.request.later_post_facts.work_phase);
});

test("the original noninteractive demo runs from its three release scripts and repeats identically", () => {
  const first = runOriginalDemo(readScenario().seed);
  const second = runOriginalDemo(readScenario().seed);
  assert.deepEqual(first.phases, [
    "PRACTICE TEST: greet",
    "PRACTICE TEST: tendBar",
    "PRACTICE TEST: ticTacToe",
    "PRACTICE TEST: jukebox"
  ]);
  assert.equal(first.logs.length, 83);
  assert.deepEqual(first.logs, second.logs);
  assert.deepEqual(first.final_db, second.final_db);
  assert.equal(first.final_db_sha256, second.final_db_sha256);
});

test("isolated CLI run without the pinned source fails and preserves failure evidence", () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "praxish-missing-source-test-"));
  try {
    const pilotRoot = path.join(tempRoot, "02_实验", "Praxish_Activity_Pilot_v0");
    const toolsRoot = path.join(pilotRoot, "tools");
    fs.mkdirSync(toolsRoot, { recursive: true });
    fs.copyFileSync(path.join(PILOT_DIR, "tools", "pilot.mjs"), path.join(toolsRoot, "pilot.mjs"));
    fs.copyFileSync(path.join(PILOT_DIR, "scenario.json"), path.join(pilotRoot, "scenario.json"));

    const runId = `missing-source-${process.pid}`;
    const cliPath = path.join(toolsRoot, "pilot.mjs");
    const result = spawnSync(process.execPath, [cliPath, "run", "--run-id", runId], { encoding: "utf8" });
    const runDir = path.join(tempRoot, "outputs", "praxish_activity_pilot_v0", "runs", runId);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Missing upstream release archive/);
    const manifestPath = path.join(runDir, "run_manifest.json");
    const errorPath = path.join(runDir, "error.json");
    const manifestBefore = fs.readFileSync(manifestPath, "utf8");
    const errorBefore = fs.readFileSync(errorPath, "utf8");
    assert.equal(JSON.parse(manifestBefore).status, "failed");
    assert.match(JSON.parse(errorBefore).message, /Missing upstream release archive/);

    const duplicate = spawnSync(process.execPath, [cliPath, "run", "--run-id", runId], { encoding: "utf8" });
    assert.equal(duplicate.status, 1);
    assert.match(duplicate.stderr, /EEXIST/);
    assert.equal(fs.readFileSync(manifestPath, "utf8"), manifestBefore);
    assert.equal(fs.readFileSync(errorPath, "utf8"), errorBefore);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});
