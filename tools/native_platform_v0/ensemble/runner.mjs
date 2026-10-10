import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import readline from 'node:readline';
import crypto from 'node:crypto';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../../_local_data/native_platform_v0/ensemble');
const example = path.join(root, 'examples/loversAndRivals');
const dataDir = path.join(example, 'data');
const names = ['schema', 'cast', 'triggerRules', 'volitionRules', 'actions', 'history'];
const raw = Object.fromEntries(names.map(n => [n, fs.readFileSync(path.join(dataDir, `${n}.json`), 'utf8')]));
const P5_PRESET_ENV = 'ENSEMBLE_P5_SOCIAL_PRESET';
const P5_PRESETS = Object.freeze({
  native_default_reject_v0: Object.freeze([]),
  hero_intelligence_30_v0: Object.freeze([
    Object.freeze({ category: 'attribute', type: 'intelligence', first: 'hero', value: 30 }),
  ]),
});
const p5Preset = process.env[P5_PRESET_ENV] ?? null;
if (p5Preset !== null && !Object.hasOwn(P5_PRESETS, p5Preset)) {
  throw new Error(`${P5_PRESET_ENV} must be one of the registered P5 social presets`);
}
const p5InitialFacts = p5Preset === null ? [] : P5_PRESETS[p5Preset];
const source = fs.readFileSync(path.join(example, 'ensemble.js'), 'utf8');
const context = { console: { log() {}, warn() {}, error() {} } };
vm.createContext(context);
const loaded = vm.runInContext(`(${JSON.stringify(raw)} && Object.fromEntries(Object.entries(${JSON.stringify(raw)}).map(([k,v]) => [k, JSON.parse(v)])))`, context);
vm.runInContext(source, context, { filename: 'official ensemble.js' });
const engine = context.ensemble;
engine.init();
const schema = engine.loadSocialStructure(loaded.schema);
const cast = engine.addCharacters(loaded.cast);
engine.addRules(loaded.triggerRules);
engine.addRules(loaded.volitionRules);
engine.addActions(loaded.actions);
engine.addHistory(loaded.history);
// P5's one optional initial-state patch is applied once, after pinned history
// loading and before any request can calculate volition. No runtime operation
// can change this preset; native action commits remain available below.
if (p5InitialFacts.length) {
  const initialFacts = validateFacts(p5InitialFacts);
  for (const fact of initialFacts) {
    engine.set(vm.runInContext(`JSON.parse(${JSON.stringify(JSON.stringify(fact))})`, context));
  }
}

const proposals = new Map();
const committed = new Set();
const settlementReceipts = new Set();
const proposalReceipts = new Map();
const sourceEvents = new Set();
const p4Requests = new Map();
const p4Responses = new Map();
let proposalSequence = 0;
let revision = 0;
function json(value) { return JSON.parse(JSON.stringify(value)); }
function reject(message) { return { ok: false, error: message }; }
function hasChar(id) { return cast.includes(id); }
function validateFacts(facts) {
  if (!Array.isArray(facts)) throw new Error('facts must be an array');
  const normalized = [];
  for (const f of facts) {
    if (!f || typeof f !== 'object' || !f.category || !f.type || !f.first || !Object.hasOwn(f, 'value')) throw new Error('invalid fact shape');
    if (!hasChar(f.first) || (f.second && !hasChar(f.second))) throw new Error('fact references unknown cast member');
    const spec = loaded.schema.schema.find(s => s.category === f.category);
    if (!spec || !spec.types.includes(f.type)) throw new Error('fact category/type is outside the example schema');
    if (spec.directionType === 'directed' && !f.second) throw new Error('directed fact requires second');
    if (spec.directionType === 'undirected' && f.second) throw new Error('undirected fact must not have second');
    if (spec.isBoolean ? typeof f.value !== 'boolean' : typeof f.value !== 'number') throw new Error('fact value has the wrong type for its schema');
    if (typeof f.value === 'number' && ((spec.minValue !== undefined && f.value < spec.minValue) || (spec.maxValue !== undefined && f.value > spec.maxValue))) throw new Error('fact value is outside schema bounds');
    normalized.push(f);
  }
  return normalized;
}
function propose(msg) {
  if (typeof msg.eventId !== 'string' || !msg.eventId.trim()) return reject('eventId is required to bind proposal to a source event');
  if (sourceEvents.has(msg.eventId)) return reject('eventId already used');
  if (!hasChar(msg.actor) || !hasChar(msg.responder)) return reject('unknown actor or responder');
  if (p5Preset !== null && Array.isArray(msg.facts) && msg.facts.length > 0) {
    return reject('P5 initial social preset is immutable; runtime facts are forbidden');
  }
  if (p5Preset !== null && msg.facts !== undefined && !Array.isArray(msg.facts)) {
    return reject('facts must be an array');
  }
  const facts = validateFacts(msg.facts ?? []);
  if (facts.length) revision++;
  for (const fact of facts) engine.set(vm.runInContext(`JSON.parse(${JSON.stringify(JSON.stringify(fact))})`, context));
  const before = json(engine.getSocialRecordCopyAtTimestep());
  const volitions = engine.calculateVolition(cast);
  const relevant = [];
  for (let v = volitions.getFirst(msg.actor, msg.responder); v; v = volitions.getNext(msg.actor, msg.responder)) relevant.push(json(v));
  const boundActions = engine.getActions(msg.actor, msg.responder, volitions, cast, 20, 100);
  const actions = boundActions.map(a => json(a));
  const proposalId = `p${++proposalSequence}:${encodeURIComponent(msg.eventId)}`;
  sourceEvents.add(msg.eventId);
  proposals.set(proposalId, { boundActions, revision, eventId: msg.eventId });
  const after = json(engine.getSocialRecordCopyAtTimestep());
  return { ok: true, proposalId, eventId: msg.eventId, recordRevision: revision, actor: msg.actor, responder: msg.responder, volitions: json(relevant), actions, socialRecordUnchanged: JSON.stringify(before) === JSON.stringify(after), trace: { stage: 'proposal', calls: ['calculateVolition', 'getActions'], doActionCalled: false, triggerCalled: false, nextStepCalled: false } };
}
function commit(msg) {
  if (typeof msg.proposalId !== 'string' || !proposals.has(msg.proposalId)) return reject('unknown proposalId');
  if (msg.settlementStatus !== 'settled' || msg.settledActionName !== msg.actionName) return reject('commit requires settlementStatus=settled and matching settledActionName');
  const proposal = proposals.get(msg.proposalId);
  if (committed.has(msg.proposalId)) {
    if (msg.eventId !== proposal.eventId) return reject('commit eventId does not match proposal source event');
    if (!proposal.boundActions.some(a => a.name === msg.actionName)) return reject('actionName was not proposed');
    if (msg.settlementReceiptId !== proposalReceipts.get(msg.proposalId)) return reject('duplicate commit must reuse its original settlement receipt');
    return { ok: true, duplicate: true, proposalId: msg.proposalId, eventId: msg.eventId, actionName: msg.actionName, trace: { doActionCalled: false, triggerCalled: false, nextStepCalled: false } };
  }
  const check = validateCommit(proposal, msg);
  if (!check.ok) return check;
  if (typeof msg.settlementReceiptId !== 'string' || !msg.settlementReceiptId.trim()) return reject('settlementReceiptId is required after actual external settlement');
  if (settlementReceipts.has(msg.settlementReceiptId)) return reject('settlementReceiptId already committed');
  const secret = process.env.ENSEMBLE_BRIDGE_SECRET;
  if (!secret || typeof msg.settlementProof !== 'string') return reject('trusted bridge settlement proof is required');
  const signed = JSON.stringify([msg.proposalId, msg.eventId, msg.actionName, msg.settlementReceiptId]);
  const expected = crypto.createHmac('sha256', secret).update(signed).digest('hex');
  const supplied = Buffer.from(msg.settlementProof, 'hex');
  const wanted = Buffer.from(expected, 'hex');
  if (supplied.length !== wanted.length || !crypto.timingSafeEqual(supplied, wanted)) return reject('settlement proof does not match this proposal and receipt');
  const chosen = check.chosen;
  engine.doAction(chosen);
  engine.runTriggerRules(cast);
  const after = json(engine.getSocialRecordCopyAtTimestep());
  engine.setupNextTimeStep();
  committed.add(msg.proposalId);
  settlementReceipts.add(msg.settlementReceiptId);
  proposalReceipts.set(msg.proposalId, msg.settlementReceiptId);
  revision++;
  return { ok: true, proposalId: msg.proposalId, eventId: proposal.eventId, recordRevision: revision, actionName: chosen.name, socialRecord: after, trace: { stage: 'commit', calls: ['doAction', 'runTriggerRules', 'setupNextTimeStep'], doActionCalled: true, triggerCalled: true, nextStepCalled: true } };
}
function validateCommit(proposal, msg) {
  if (proposal.revision !== revision) return reject('stale proposal: source social-record revision changed');
  if (msg.eventId !== proposal.eventId) return reject('commit eventId does not match proposal source event');
  const chosen = proposal.boundActions.find(a => a.name === msg.actionName);
  if (!chosen) return reject('actionName was not proposed');
  if (msg.settledActionName !== undefined && msg.settledActionName !== msg.actionName) return reject('settled action does not match actionName');
  if (msg.settlementStatus !== undefined && msg.settlementStatus !== 'settled') return reject('settlementStatus must be settled');
  return { ok: true, chosen };
}
function authorize(msg) {
  if (typeof msg.proposalId !== 'string' || !proposals.has(msg.proposalId)) return reject('unknown proposalId');
  const proposal = proposals.get(msg.proposalId);
  if (msg.eventId !== proposal.eventId) return reject('commit eventId does not match proposal source event');
  const chosen = proposal.boundActions.find(a => a.name === msg.actionName);
  if (!chosen) return reject('actionName was not proposed');
  if (msg.settledActionName !== undefined && msg.settledActionName !== msg.actionName) return reject('settled action does not match actionName');
  if (committed.has(msg.proposalId)) return { ok: true, duplicate: true, proposalId: msg.proposalId, eventId: msg.eventId, actionName: chosen.name, trace: { stage: 'pre-settlement authorization', calls: ['validateCommittedIdentity'], doActionCalled: false, triggerCalled: false, nextStepCalled: false } };
  const result = validateCommit(proposal, msg);
  if (!result.ok) return result;
  return { ok: true, proposalId: msg.proposalId, eventId: msg.eventId, actionName: result.chosen.name, recordRevision: revision, trace: { stage: 'pre-settlement authorization', calls: ['validateCommit'], doActionCalled: false, triggerCalled: false, nextStepCalled: false } };
}

// P4-only request/response operations. The P4 caller keeps the physical note
// and receipt in Evennia; these operations expose no responder decision to the
// initiator and do not alter the pinned source data or initial social record.
function requestNote(msg) {
  if (typeof msg.requestId !== 'string' || !msg.requestId.trim()) return reject('requestId is required');
  if (typeof msg.eventId !== 'string' || !msg.eventId.trim()) return reject('eventId is required');
  if (msg.actor !== 'hero' || msg.responder !== 'love') return reject('P4 note request requires hero to love');
  if (p4Requests.has(msg.requestId) || sourceEvents.has(msg.eventId)) return reject('request or source event already used');
  const before = json(engine.getSocialRecordCopyAtTimestep());
  const volitions = engine.calculateVolition(cast);
  const relevant = [];
  for (let v = volitions.getFirst(msg.actor, msg.responder); v; v = volitions.getNext(msg.actor, msg.responder)) {
    const row = json(v);
    if (row.category === 'feeling' && row.type === 'closeness' && row.intentType === true) relevant.push(row);
  }
  const positive = relevant.filter(v => Number(v.weight) > 0);
  if (!positive.length) return { ok: true, status: 'NO_CANDIDATE', requestId: msg.requestId,
    eventId: msg.eventId, actor: msg.actor, responder: msg.responder,
    native_intents: relevant, trace: { calls: ['calculateVolition'], getActionsCalled: false,
      doActionCalled: false, triggerCalled: false, nextStepCalled: false } };
  positive.sort((a, b) => Number(b.weight) - Number(a.weight));
  const chosenIntent = positive[0];
  p4Requests.set(msg.requestId, { eventId: msg.eventId, actor: msg.actor,
    responder: msg.responder, intent: chosenIntent, responded: false });
  sourceEvents.add(msg.eventId);
  const after = json(engine.getSocialRecordCopyAtTimestep());
  return { ok: true, status: 'PROPOSED', requestId: msg.requestId, eventId: msg.eventId,
    actor: msg.actor, responder: msg.responder, native_intent: chosenIntent,
    native_intents: relevant, socialRecordUnchanged: JSON.stringify(before) === JSON.stringify(after),
    trace: { calls: ['calculateVolition'], getActionsCalled: false, doActionCalled: false,
      triggerCalled: false, nextStepCalled: false } };
}

function respondNote(msg) {
  if (typeof msg.requestId !== 'string' || typeof msg.eventId !== 'string') return reject('requestId and eventId are required');
  const request = p4Requests.get(msg.requestId);
  if (!request) return reject('unknown note request');
  if (request.responded) return reject('note request already received a response');
  if (msg.actor !== request.actor || msg.responder !== request.responder) return reject('response roles do not match the physical note request');
  const volitions = engine.calculateVolition(cast);
  const responderVolitions = [];
  for (let v = volitions.getFirst(msg.responder, msg.actor); v; v = volitions.getNext(msg.responder, msg.actor)) {
    const row = json(v);
    if (row.category === 'feeling' && row.type === 'closeness') responderVolitions.push(row);
  }
  const boundActions = engine.getActions(msg.actor, msg.responder, volitions, cast, 20, 100);
  const nativeCandidates = boundActions;
  if (!nativeCandidates.length) {
    request.responded = true;
    return { ok: true, status: 'NO_CANDIDATE', requestId: msg.requestId, eventId: msg.eventId,
      actor: msg.actor, responder: msg.responder, responderVolitions,
      native_candidates: [], trace: { calls: ['calculateVolition', 'getActions'], doActionCalled: false,
        triggerCalled: false, nextStepCalled: false } };
  }
  const weights = nativeCandidates.map(a => Number(a.weight));
  if (weights.some(w => !Number.isFinite(w))) return reject('native note response has invalid weight');
  const best = Math.max(...weights);
  const winners = nativeCandidates.filter(a => Number(a.weight) === best);
  const noteWinners = winners.filter(a => String(a.lineage || '').includes('RAISECLOSENESS-WRITELOVENOTE'));
  if (!noteWinners.length) {
    request.responded = true;
    return { ok: true, status: 'UNSUPPORTED_NATIVE_ACTION', requestId: msg.requestId,
      eventId: msg.eventId, actor: msg.actor, responder: msg.responder,
      responderVolitions, native_candidates: nativeCandidates.map(a => json(a)),
      native_winning_tie_names: winners.map(a => a.name),
      unsupported_native_winners: winners.map(a => a.name),
      trace: { calls: ['calculateVolition', 'getActions'], doActionCalled: false,
        triggerCalled: false, nextStepCalled: false } };
  }
  const digest = crypto.createHash('sha256').update(`${msg.requestId}|${msg.eventId}`).digest();
  const index = digest.readUInt32BE(0) % noteWinners.length;
  const selected = noteWinners[index];
  const proposalId = `p4:${encodeURIComponent(msg.requestId)}:response`;
  const proposal = { boundActions: [selected], revision, eventId: msg.eventId };
  proposals.set(proposalId, proposal);
  request.responded = true;
  p4Responses.set(msg.requestId, { proposalId, actionName: selected.name });
  return { ok: true, status: 'PROPOSED', requestId: msg.requestId, eventId: msg.eventId,
    actor: msg.actor, responder: msg.responder, responderVolitions,
    native_candidates: nativeCandidates.map(a => json(a)), selected: json(selected),
    proposalId, recordRevision: revision,
    decision: selected.isAccept === true ? 'accepted' : 'rejected',
    selection: { rule: 'max_native_weight_then_seeded_request_tie', winning_weight: best,
      native_winning_tie_names: winners.map(a => a.name),
      supported_note_winning_tie_names: noteWinners.map(a => a.name),
      unsupported_native_winners: winners.filter(a => !noteWinners.includes(a)).map(a => a.name),
      selected_index: index, selected_name: selected.name },
    trace: { calls: ['calculateVolition', 'getActions'], doActionCalled: false,
      triggerCalled: false, nextStepCalled: false } };
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  try {
    const msg = JSON.parse(line);
    let result;
    if (msg.op === 'hello') result = { ok: true, p5Preset,
      initialFacts: json(p5InitialFacts), initialStateApplied: p5Preset !== null };
    else if (msg.op === 'propose') result = propose(msg);
    else if (msg.op === 'authorize') result = authorize(msg);
    else if (msg.op === 'commit') result = commit(msg);
    else if (msg.op === 'request_note') result = requestNote(msg);
    else if (msg.op === 'respond_note') result = respondNote(msg);
    else result = reject('op must be propose, authorize, commit, request_note, or respond_note');
    process.stdout.write(JSON.stringify(result) + '\n');
  } catch (e) { process.stdout.write(JSON.stringify(reject(e.message)) + '\n'); }
}
