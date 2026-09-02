import {
  advanceTime,
  applyAction,
  applyHiddenCorridorEvent,
  applyVisiblePlaceEvent,
  createInitialState,
  rankActions,
  semanticStateOperator,
} from './core.js';

let state = createInitialState();

const $ = (selector) => document.querySelector(selector);
const pretty = (value) => JSON.stringify(value, null, 2);

function statusText(view) {
  return view.status === 'fresh' ? '新鲜' : view.status === 'stale' ? '陈旧' : '未知';
}

function renderRoom() {
  const place = state.world.places[state.world.actors.A.location];
  $('#room-title').textContent = `${place.label} · A 当前在这里`;
  $('#room-scene').innerHTML = Object.entries(place.fields)
    .map(([key, value]) => `<span class="object"><b>${key}</b><small>${String(value)}</small></span>`)
    .join('');
}

function renderActions() {
  const ranked = rankActions(state);
  $('#action-list').innerHTML = ranked.map((action) => `
    <button class="action" data-action="${action.id}">
      <span>${action.label}</span><strong>${Math.round(action.probability * 100)}%</strong>
    </button>`).join('');
  document.querySelectorAll('[data-action]').forEach((button) => {
    button.addEventListener('click', () => { applyAction(state, button.dataset.action); render(); });
  });
}

function renderObservation() {
  const entries = Object.values(state.observation.placeViews);
  $('#observation-list').innerHTML = entries.map((view) => `
    <article class="observation ${view.status}">
      <header><b>${view.label}</b><span>${statusText(view)}</span></header>
      <small>tick ${view.observedAt} · ${view.source}</small>
      <pre>${pretty(view.fields)}</pre>
    </article>`).join('') || '<p>还没有观察记录。</p>';
}

function renderLog() {
  $('#provenance-list').innerHTML = state.provenance.map((item) => `
    <li><span>t${item.tick} · ${item.kind}</span>${item.message}</li>`).join('');
}

function render() {
  $('#tick').textContent = state.world.tick;
  $('#world-json').textContent = pretty(state.world);
  $('#self-json').textContent = pretty(state.self);
  $('#profile-json').textContent = pretty(state.profile);
  renderRoom();
  renderObservation();
  renderActions();
  renderLog();
}

$('#visible-event').addEventListener('click', () => { applyVisiblePlaceEvent(state); render(); });
$('#hidden-event').addEventListener('click', () => { applyHiddenCorridorEvent(state); render(); });
$('#time').addEventListener('click', () => { advanceTime(state); render(); });
$('#delta').addEventListener('click', () => { semanticStateOperator(state, { anxiety: 0.12 }, 'manual-demo-fixture'); render(); });
$('#reset').addEventListener('click', () => { state = createInitialState(); render(); });

render();
