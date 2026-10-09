import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';

let assertions = 0;
function check(fn) { fn(); assertions++; }
const first = 'p1:event-1';
const second = 'p3:event-3';
const input = [
  { op: 'propose', eventId: 'event-1', actor: 'hero', responder: 'love', facts: [] },
  { op: 'propose', eventId: 'bad-actor', actor: 'nobody', responder: 'love', facts: [] },
  { op: 'propose', eventId: 'invalid-batch', actor: 'hero', responder: 'love', facts: [
    { category: 'feeling', type: 'closeness', first: 'hero', second: 'love', value: 5 },
    { category: 'made-up', type: 'bad', first: 'hero', value: true }
  ] },
  { op: 'propose', eventId: 'event-2', actor: 'hero', responder: 'love', facts: [] },
  { op: 'propose', eventId: 'event-3', actor: 'hero', responder: 'love', facts: [{ category: 'feeling', type: 'closeness', first: 'hero', second: 'love', value: 5 }] },
  { op: 'authorize', proposalId: second, eventId: 'event-3', actionName: 'writeLoveNoteReject' },
  { op: 'commit', proposalId: first, eventId: 'event-1', settlementStatus: 'settled', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99' },
  { op: 'commit', proposalId: second, eventId: 'event-3', settlementStatus: 'pending', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99' },
  { op: 'commit', proposalId: 'bad', eventId: 'event-3', settlementStatus: 'settled', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99' },
  { op: 'commit', proposalId: second, eventId: 'event-3', settlementStatus: 'settled', settledActionName: 'kissFail', actionName: 'not-proposed', settlementReceiptId: '#99' },
  { op: 'commit', proposalId: second, eventId: 'wrong-event', settlementStatus: 'settled', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99' },
  { op: 'commit', proposalId: second, eventId: 'event-3', settlementStatus: 'settled', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99', settlementProof: '00'.repeat(32) },
  { op: 'commit', proposalId: second, eventId: 'event-3', settlementStatus: 'settled', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99' },
  { op: 'authorize', proposalId: second, eventId: 'event-3', actionName: 'writeLoveNoteReject' },
  { op: 'commit', proposalId: second, eventId: 'event-3', settlementStatus: 'settled', settledActionName: 'writeLoveNoteReject', actionName: 'writeLoveNoteReject', settlementReceiptId: '#99' },
  { op: 'propose', eventId: 'event-4', actor: 'hero', responder: 'love', facts: [] }
].map(x => {
  if (x.op === 'commit' && x.settlementReceiptId) {
    const signed = JSON.stringify([x.proposalId, x.eventId, x.actionName, x.settlementReceiptId]);
    x.settlementProof ??= crypto.createHmac('sha256', 'selftest-only-secret').update(signed).digest('hex');
  }
  return JSON.stringify(x);
}).join('\n') + '\n';
const run = spawnSync(process.execPath, [new URL('./runner.mjs', import.meta.url).pathname], { input, encoding: 'utf8', env: { ...process.env, ENSEMBLE_BRIDGE_SECRET: 'selftest-only-secret' } });
check(() => assert.equal(run.status, 0, run.stderr));
const out = run.stdout.trim().split('\n').map(JSON.parse);
check(() => assert.equal(out.length, input.trim().split('\n').length));
check(() => assert.equal(out[0].ok, true));
check(() => assert.equal(out[0].proposalId, first));
check(() => assert.equal(out[0].trace.doActionCalled, false));
check(() => assert.equal(out[1].ok, false));
check(() => assert.equal(out[2].ok, false));
check(() => assert.equal(out[3].ok, true));
check(() => assert.equal(out[3].volitions.find(v => v.first === 'hero' && v.second === 'love')?.weight, 20));
check(() => assert.equal(out[4].ok, true));
check(() => assert.equal(out[4].proposalId, second));
check(() => assert.equal(out[4].volitions.find(v => v.first === 'hero' && v.second === 'love')?.weight, 25));
check(() => assert.equal(out[5].ok, true));
check(() => assert.equal(out[6].ok, false));
check(() => assert.match(out[6].error, /stale proposal/));
check(() => assert.equal(out[7].ok, false));
check(() => assert.equal(out[8].ok, false));
check(() => assert.equal(out[9].ok, false));
check(() => assert.equal(out[10].ok, false));
check(() => assert.equal(out[11].ok, false));
check(() => assert.match(out[11].error, /proof/));
check(() => assert.equal(out[12].ok, true));
check(() => assert.equal(out[12].trace.doActionCalled, true));
check(() => assert.equal(out[13].ok, true));
check(() => assert.equal(out[13].duplicate, true));
check(() => assert.equal(out[14].duplicate, true));
check(() => assert.equal(out[14].trace.doActionCalled, false));
check(() => assert.equal(out[15].proposalId, 'p4:event-4'));
process.stdout.write(JSON.stringify({ suite: 'wrapper interface self-tests (not official upstream tests)', assertions, status: 'PASS' }, null, 2) + '\n');
