const clone = (value) => JSON.parse(JSON.stringify(value));

function log(state, kind, message, payload = {}) {
  state.provenance.unshift({ tick: state.world.tick, kind, message, payload });
}

function currentPlaceId(state) {
  return state.world.actors.A.location;
}

function refreshPlaceView(state, placeId, source) {
  const place = state.world.places[placeId];
  state.observation.placeViews[placeId] = {
    placeId,
    label: place.label,
    status: 'fresh',
    observedAt: state.world.tick,
    source,
    fields: clone(place.fields),
  };
  log(state, 'observation', `O_A 刷新 ${place.label} 的完整可观察字段`, { placeId, source });
}

function refreshCurrentPlace(state, source) {
  refreshPlaceView(state, currentPlaceId(state), source);
}

function ageOtherPlaceViews(state) {
  for (const [placeId, view] of Object.entries(state.observation.placeViews)) {
    if (placeId === currentPlaceId(state)) continue;
    const age = state.world.tick - view.observedAt;
    view.status = age >= 3 ? 'unknown' : 'stale';
  }
}

export function createInitialState() {
  const state = {
    world: {
      tick: 0,
      actors: { A: { location: 'room', health: 'normal' } },
      places: {
        room: {
          label: 'A 的房间',
          fields: {
            doorOpen: true,
            lampOn: true,
            phoneUnread: 1,
            bedOccupied: false,
            deskNote: '明天要交的作业',
          },
        },
        corridor: {
          label: '走廊',
          fields: {
            roomDoorOpen: true,
            corridorLight: true,
            notice: '无新通知',
          },
        },
      },
    },
    observation: { actorId: 'A', placeViews: {} },
    self: {
      fatigue: 0.35,
      anxiety: 0.15,
      activeGoal: '休息并决定是否查看消息',
      decisionMode: '未决定',
    },
    profile: {
      conflictAvoidance: '待具体机制决定',
      deadlineSensitivity: '待具体机制决定',
      note: 'P 在 v0 先固定；此处只展示其数据所有权。',
    },
    provenance: [],
  };
  refreshCurrentPlace(state, 'initial-place-observation');
  return state;
}

export function applyVisiblePlaceEvent(state) {
  const placeId = currentPlaceId(state);
  const place = state.world.places[placeId];
  if (placeId === 'room') {
    place.fields.lampOn = !place.fields.lampOn;
    log(state, 'world-event', `W：房间灯被切换为 ${place.fields.lampOn ? '开' : '关'}`, { placeId });
  } else {
    place.fields.corridorLight = !place.fields.corridorLight;
    log(state, 'world-event', `W：走廊灯被切换为 ${place.fields.corridorLight ? '开' : '关'}`, { placeId });
  }
  // 当前 demo 的场所设计假设：角色在场所内时，整个场所的可观察字段可整体流入 O。
  refreshCurrentPlace(state, 'visible-place-event');
}

export function applyHiddenCorridorEvent(state) {
  const corridor = state.world.places.corridor;
  corridor.fields.notice = corridor.fields.notice === '无新通知' ? '有人刚贴了一张便签' : '无新通知';
  log(state, 'world-event', 'W：走廊公告状态变化', { placeId: 'corridor' });
  if (currentPlaceId(state) === 'corridor') refreshPlaceView(state, 'corridor', 'visible-place-event');
}

// 占位接口：日后替换为 LLM + schema、appraisal rule 或 learned operator。
export function semanticStateOperator(state, delta, source = 'manual-fixture') {
  for (const [key, amount] of Object.entries(delta)) {
    if (typeof state.self[key] === 'number') state.self[key] = Math.max(0, Math.min(1, state.self[key] + amount));
  }
  log(state, 'state-delta', `ΔS 占位更新：${Object.entries(delta).map(([k, v]) => `${k} ${v >= 0 ? '+' : ''}${v}`).join(', ')}`, { delta, source });
}

export function advanceTime(state) {
  state.world.tick += 1;
  semanticStateOperator(state, { fatigue: 0.04 }, 'time-fixture');
  refreshCurrentPlace(state, 'ambient-place-refresh');
  ageOtherPlaceViews(state);
  log(state, 'time', '时间推进一格；当前场所整体刷新，离开场所的 O 视图开始变旧', {});
}

export function getActionCandidates(state) {
  const placeId = currentPlaceId(state);
  const candidates = [];
  if (placeId === 'room') {
    if (state.world.places.room.fields.doorOpen) candidates.push({ id: 'close-door', label: '关上房门' });
    candidates.push({ id: 'look-phone', label: '查看手机' });
    candidates.push({ id: 'rest-bed', label: '坐到床边休息' });
    candidates.push({ id: 'leave-room', label: '走到走廊' });
  } else {
    candidates.push({ id: 'return-room', label: '回到房间' });
    candidates.push({ id: 'wait-corridor', label: '在走廊停留' });
  }
  return candidates;
}

// 占位策略：只展示 action interface，不代表已选定的状态→行为机制。
export function rankActions(state) {
  const candidates = getActionCandidates(state);
  const base = Object.fromEntries(candidates.map(({ id }) => [id, 1]));
  if (state.self.fatigue > 0.45 && base['rest-bed'] !== undefined) base['rest-bed'] += 1.2;
  if (state.self.anxiety > 0.35 && base['close-door'] !== undefined) base['close-door'] += 1.0;
  if (state.world.places.room.fields.phoneUnread > 0 && base['look-phone'] !== undefined) base['look-phone'] += 0.8;
  const total = Object.values(base).reduce((sum, value) => sum + value, 0);
  return candidates.map((candidate) => ({ ...candidate, probability: base[candidate.id] / total })).sort((a, b) => b.probability - a.probability);
}

export function applyAction(state, actionId) {
  const allowed = getActionCandidates(state).some((action) => action.id === actionId);
  if (!allowed) {
    log(state, 'world-reject', `W 拒绝不可执行动作：${actionId}`, { actionId });
    return;
  }

  const room = state.world.places.room;
  switch (actionId) {
    case 'close-door':
      room.fields.doorOpen = false;
      state.world.places.corridor.fields.roomDoorOpen = false;
      log(state, 'action', 'A 选择：关上房门；W 结算门状态', { actionId, effect: 'room.doorOpen=false' });
      break;
    case 'look-phone':
      room.fields.phoneUnread = 0;
      state.self.decisionMode = '已查看消息，等待具体语义更新器解释';
      log(state, 'action', 'A 选择：查看手机；W 结算未读消息状态', { actionId, effect: 'room.phoneUnread=0' });
      break;
    case 'rest-bed':
      room.fields.bedOccupied = true;
      state.self.decisionMode = '休息';
      log(state, 'action', 'A 选择：坐到床边休息', { actionId, effect: 'room.bedOccupied=true' });
      break;
    case 'leave-room':
      state.world.actors.A.location = 'corridor';
      state.self.decisionMode = '离开房间';
      log(state, 'action', 'A 选择：走到走廊；W 更新 A 的位置', { actionId, effect: 'A.location=corridor' });
      break;
    case 'return-room':
      state.world.actors.A.location = 'room';
      state.self.decisionMode = '回到房间';
      log(state, 'action', 'A 选择：回到房间；W 更新 A 的位置', { actionId, effect: 'A.location=room' });
      break;
    case 'wait-corridor':
      state.self.decisionMode = '停留观察';
      log(state, 'action', 'A 选择：在走廊停留', { actionId, effect: 'none' });
      break;
  }
  refreshCurrentPlace(state, 'action-settlement');
  ageOtherPlaceViews(state);
}
