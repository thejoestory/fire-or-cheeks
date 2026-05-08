/* ═══════════════════════════════════════════════
   Fire or Cheeks — Frontend JS
   ═══════════════════════════════════════════════ */

// ── Shared WebSocket helper ────────────────────────────────────────────────

function openWS(gameCode, onMessage) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const rootPath = (window.ROOT_PATH || '').replace(/\/$/, '');
  const url = `${proto}//${location.host}${rootPath}/ws/${gameCode}`;
  let ws;
  let closed = false;

  function connect() {
    ws = new WebSocket(url);
    ws.addEventListener('message', (evt) => {
      try { onMessage(JSON.parse(evt.data)); } catch(e) {}
    });
    ws.addEventListener('close', () => {
      if (!closed) setTimeout(connect, 2000);
    });
  }
  connect();
  return { close() { closed = true; ws && ws.close(); } };
}

// ── Toast ──────────────────────────────────────────────────────────────────

function showToast(msg, type = 'info', duration = 2800) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ── Helpers ────────────────────────────────────────────────────────────────

function qs(sel) { return document.querySelector(sel); }
function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function setStyle(id, prop, val) { const el = document.getElementById(id); if (el) el.style[prop] = val; }
function show(id) { const el = document.getElementById(id); if (el) el.classList.remove('hidden'); }
function hide(id) { const el = document.getElementById(id); if (el) el.classList.add('hidden'); }
function setDisabled(id, val) { const el = document.getElementById(id); if (el) el.disabled = val; }

function updateBars(fire, cheeks, total, firePct, cheeksPct, prefix = '') {
  setStyle(prefix + 'bar-fire',   'width', firePct + '%');
  setStyle(prefix + 'bar-cheeks', 'width', cheeksPct + '%');
  setText(prefix + 'num-fire',    fire);
  setText(prefix + 'num-cheeks',  cheeks);
  setText(prefix + 'pct-fire',    firePct + '%');
  setText(prefix + 'pct-cheeks',  cheeksPct + '%');
  setText(prefix + 'vote-total',  total + ' vote' + (total !== 1 ? 's' : ''));
}

// ════════════════════════════════════════════════
//  HOST PAGE
// ════════════════════════════════════════════════

function initHost() {
  const gameCode = document.getElementById('game-code')?.value;
  const pin = document.getElementById('host-pin')?.value;
  if (!gameCode || !pin) return;

  // WebSocket
  openWS(gameCode, (msg) => handleHostMessage(msg, gameCode, pin));

  // New round form
  const form = document.getElementById('new-round-form');
  if (form) form.addEventListener('submit', (e) => handleNewRound(e, gameCode, pin));

  // Image preview
  const imgInput = document.getElementById('image-input');
  if (imgInput) {
    imgInput.addEventListener('change', () => {
      const file = imgInput.files[0];
      if (!file) return;
      const preview = document.getElementById('image-preview');
      const wrap = document.getElementById('image-preview-wrap');
      preview.src = URL.createObjectURL(file);
      wrap.classList.remove('hidden');
    });
  }
  const clearBtn = document.getElementById('clear-image');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      const imgInput = document.getElementById('image-input');
      imgInput.value = '';
      const wrap = document.getElementById('image-preview-wrap');
      wrap.classList.add('hidden');
    });
  }

  // Control buttons
  document.getElementById('start-btn')?.addEventListener('click', () => hostAction(gameCode, pin, 'start'));
  document.getElementById('stop-btn')?.addEventListener('click',  () => hostAction(gameCode, pin, 'stop'));
  document.getElementById('reveal-btn')?.addEventListener('click', () => hostAction(gameCode, pin, 'reveal'));
}

async function handleNewRound(e, gameCode, pin) {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById('new-round-btn');
  btn.disabled = true;
  btn.textContent = 'Creating...';

  const fd = new FormData(form);
  try {
    const res = await fetch(`/api/host/${gameCode}/round/new`, { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Error creating round', 'cheeks'); }
    else {
      showToast(`Round ${data.round_number} created!`, 'fire');
      form.reset();
      document.getElementById('image-preview-wrap')?.classList.add('hidden');
    }
  } catch(err) {
    showToast('Network error', 'cheeks');
  }
  btn.disabled = false;
  btn.textContent = '➕ Create Round';
}

async function hostAction(gameCode, pin, action) {
  const fd = new FormData();
  fd.append('pin', pin);
  const res = await fetch(`/api/host/${gameCode}/round/${action}`, { method: 'POST', body: fd });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    showToast(data.detail || `Failed: ${action}`, 'cheeks');
  }
}

function handleHostMessage(msg, gameCode, pin) {
  switch (msg.type) {
    case 'round_new':
      renderRoundNew(msg);
      break;
    case 'voting_started':
      updateRoundStatus('voting');
      setDisabled('start-btn', true);
      setDisabled('stop-btn', false);
      setDisabled('reveal-btn', true);
      break;
    case 'voting_closed':
      updateRoundStatus('closed');
      setDisabled('start-btn', true);
      setDisabled('stop-btn', true);
      setDisabled('reveal-btn', false);
      break;
    case 'results_revealed':
      updateRoundStatus('revealed');
      updateBars(msg.fire, msg.cheeks, msg.total, msg.fire_pct, msg.cheeks_pct);
      showVerdict(msg.verdict);
      setDisabled('start-btn', true);
      setDisabled('stop-btn', true);
      setDisabled('reveal-btn', true);
      break;
    case 'vote_update':
      updateBars(msg.fire, msg.cheeks, msg.total, msg.fire_pct, msg.cheeks_pct);
      break;
    case 'player_joined':
      setText('pc-num', msg.player_count);
      showToast(`${msg.display_name} joined!`, 'info', 2000);
      break;
  }
}

function renderRoundNew(msg) {
  const display = document.getElementById('round-display');
  if (!display) return;

  const imgHtml = msg.image_path
    ? `<div class="round-image-wrap"><img src="${msg.image_path}" class="round-image" alt="Round image" /></div>`
    : '';
  const promptHtml = msg.prompt
    ? `<div class="round-prompt" id="round-prompt">${escHtml(msg.prompt)}</div>`
    : '';

  display.innerHTML = `
    <div class="round-header">
      <span class="round-badge">Round ${msg.round_number}</span>
      <span class="round-status-badge status-pending" id="status-badge">PENDING</span>
    </div>
    ${imgHtml}
    ${promptHtml}
    <div class="vote-bars" id="vote-bars">
      <div class="vote-bar-row">
        <span class="vote-label fire-label">🔥 FIRE</span>
        <div class="bar-track"><div class="bar-fill bar-fire" id="bar-fire" style="width:0%"></div></div>
        <span class="vote-num" id="num-fire">0</span>
        <span class="vote-pct" id="pct-fire">0%</span>
      </div>
      <div class="vote-bar-row">
        <span class="vote-label cheeks-label">🍑 CHEEKS</span>
        <div class="bar-track"><div class="bar-fill bar-cheeks" id="bar-cheeks" style="width:0%"></div></div>
        <span class="vote-num" id="num-cheeks">0</span>
        <span class="vote-pct" id="pct-cheeks">0%</span>
      </div>
      <div class="vote-total" id="vote-total">0 votes</div>
    </div>
    <div class="verdict hidden" id="verdict"></div>
  `;

  setDisabled('start-btn', false);
  setDisabled('stop-btn', true);
  setDisabled('reveal-btn', true);
}

function updateRoundStatus(status) {
  const badge = document.getElementById('status-badge');
  if (badge) {
    badge.className = `round-status-badge status-${status}`;
    badge.textContent = status.toUpperCase();
  }
}

function showVerdict(verdict) {
  const el = document.getElementById('verdict');
  if (!el) return;
  el.textContent = verdict;
  el.classList.remove('hidden');
}

// ════════════════════════════════════════════════
//  PLAY PAGE
// ════════════════════════════════════════════════

function initPlay() {
  const gameCode = document.getElementById('game-code')?.value;
  if (!gameCode) return;
  openWS(gameCode, handlePlayMessage);
}

function castVote(value) {
  const gameCode = document.getElementById('game-code')?.value;
  if (!gameCode) return;
  const fd = new FormData();
  fd.append('vote_value', value);
  fetch(`/api/vote/${gameCode}`, { method: 'POST', body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        // Update button styles
        const firBtn  = document.getElementById('btn-fire');
        const chkBtn  = document.getElementById('btn-cheeks');
        if (firBtn) firBtn.classList.toggle('voted', value === 'fire');
        if (chkBtn) chkBtn.classList.toggle('voted', value === 'cheeks');
        // Update message
        const msg = document.getElementById('voted-msg');
        if (msg) {
          msg.classList.remove('hidden');
          msg.innerHTML = `You voted <strong>${value.toUpperCase()}</strong> — you can change it until voting closes.`;
        }
      } else {
        showToast(data.detail || 'Vote failed', 'cheeks');
      }
    })
    .catch(() => showToast('Network error', 'cheeks'));
}

function handlePlayMessage(msg) {
  const main = document.getElementById('play-main');
  if (!main) return;

  switch (msg.type) {
    case 'voting_started':
      renderPlayVoting(main, msg);
      break;
    case 'voting_closed':
      renderPlayClosed(main);
      break;
    case 'results_revealed':
      renderPlayRevealed(main, msg);
      break;
    case 'round_new':
      renderPlayWaiting(main);
      break;
  }
}

function renderPlayWaiting(main) {
  main.innerHTML = `
    <div class="waiting-screen">
      <div class="waiting-icon">⏳</div>
      <h2>Waiting for host...</h2>
      <p>Hang tight — the host is setting up the next round.</p>
    </div>
  `;
}

function renderPlayVoting(main, msg) {
  const imgHtml = msg.image_path
    ? `<div class="play-image-wrap"><img src="${msg.image_path}" class="play-image" alt="Round image" /></div>`
    : '';
  const promptHtml = msg.prompt
    ? `<div class="play-prompt">${escHtml(msg.prompt)}</div>`
    : '';
  main.innerHTML = `
    <div class="voting-screen">
      ${imgHtml}
      ${promptHtml}
      <div class="vote-buttons" id="vote-buttons">
        <button class="vote-btn vote-fire" id="btn-fire" onclick="castVote('fire')">🔥<br><span>FIRE</span></button>
        <button class="vote-btn vote-cheeks" id="btn-cheeks" onclick="castVote('cheeks')">🍑<br><span>CHEEKS</span></button>
      </div>
      <div class="voted-msg hidden" id="voted-msg">You voted — you can change it until voting closes.</div>
    </div>
  `;
}

function renderPlayClosed(main) {
  // preserve image/prompt from voting screen if possible
  const currentImgEl = main.querySelector('.play-image');
  const currentPromptEl = main.querySelector('.play-prompt');
  const imgHtml = currentImgEl ? `<div class="play-image-wrap play-image-wrap-sm">${currentImgEl.outerHTML}</div>` : '';
  const promptHtml = currentPromptEl ? currentPromptEl.outerHTML : '';
  main.innerHTML = `
    <div class="closed-screen">
      ${imgHtml}
      ${promptHtml}
      <div class="voting-closed-msg">
        <span>🔒 Voting closed</span>
        <p>Waiting for results...</p>
      </div>
    </div>
  `;
}

function renderPlayRevealed(main, msg) {
  const currentImgEl = main.querySelector('.play-image');
  const currentPromptEl = main.querySelector('.play-prompt');
  const imgHtml = currentImgEl ? `<div class="play-image-wrap play-image-wrap-sm">${currentImgEl.outerHTML}</div>` : '';
  const promptHtml = currentPromptEl ? currentPromptEl.outerHTML : '';
  main.innerHTML = `
    <div class="revealed-screen">
      ${imgHtml}
      ${promptHtml}
      <div class="result-bars">
        <div class="result-row">
          <span class="result-label fire-label">🔥 FIRE</span>
          <div class="bar-track"><div class="bar-fill bar-fire" style="width:${msg.fire_pct}%"></div></div>
          <span class="result-pct">${msg.fire_pct}%</span>
        </div>
        <div class="result-row">
          <span class="result-label cheeks-label">🍑 CHEEKS</span>
          <div class="bar-track"><div class="bar-fill bar-cheeks" style="width:${msg.cheeks_pct}%"></div></div>
          <span class="result-pct">${msg.cheeks_pct}%</span>
        </div>
      </div>
      <div class="verdict play-verdict animate-verdict">${escHtml(msg.verdict)}</div>
    </div>
  `;
}

// ════════════════════════════════════════════════
//  DISPLAY PAGE
// ════════════════════════════════════════════════

function initDisplay() {
  const gameCode = document.getElementById('game-code')?.value;
  if (!gameCode) return;
  openWS(gameCode, handleDisplayMessage);
}

function handleDisplayMessage(msg) {
  const main = document.getElementById('display-main');
  if (!main) return;

  switch (msg.type) {
    case 'round_new':
      renderDisplayRound(main, msg);
      break;
    case 'voting_started':
      updateDisplayStatus('voting');
      renderDisplayBars(0, 0, 0, 0, 0);
      break;
    case 'voting_closed':
      updateDisplayStatus('closed');
      break;
    case 'results_revealed':
      updateDisplayStatus('revealed');
      renderDisplayBars(msg.fire, msg.cheeks, msg.total, msg.fire_pct, msg.cheeks_pct);
      showDisplayVerdict(msg.verdict);
      break;
    case 'vote_update':
      renderDisplayBars(msg.fire, msg.cheeks, msg.total, msg.fire_pct, msg.cheeks_pct);
      break;
    case 'player_joined':
      showToast(`${msg.display_name} joined! (${msg.player_count} total)`, 'info', 2000);
      break;
  }
}

function renderDisplayRound(main, msg) {
  const imgHtml = msg.image_path
    ? `<div class="display-image-wrap"><img src="${msg.image_path}" class="display-image" alt="Round image" /></div>`
    : '';
  const promptHtml = msg.prompt
    ? `<div class="display-prompt" id="d-prompt">${escHtml(msg.prompt)}</div>`
    : '';
  main.innerHTML = `
    <div class="display-round" id="display-round">
      <div class="display-round-header">
        <span class="round-badge">Round ${msg.round_number}</span>
        <span class="round-status-badge status-pending" id="d-status-badge">PENDING</span>
      </div>
      ${imgHtml}
      ${promptHtml}
      <div class="display-bars" id="d-bars"></div>
      <div class="display-verdict hidden" id="d-verdict"></div>
    </div>
  `;
}

function updateDisplayStatus(status) {
  const badge = document.getElementById('d-status-badge');
  if (badge) {
    badge.className = `round-status-badge status-${status}`;
    badge.textContent = status.toUpperCase();
  }
  // Show bars section once voting starts
  if (status === 'voting') {
    const bars = document.getElementById('d-bars');
    if (bars && !bars.innerHTML.trim()) renderDisplayBars(0, 0, 0, 0, 0);
  }
}

function renderDisplayBars(fire, cheeks, total, firePct, cheeksPct) {
  const bars = document.getElementById('d-bars');
  if (!bars) return;
  bars.innerHTML = `
    <div class="d-bar-row">
      <span class="d-bar-label fire-label">🔥 FIRE</span>
      <div class="bar-track bar-track-lg">
        <div class="bar-fill bar-fire" id="d-bar-fire" style="width:${firePct}%"></div>
      </div>
      <span class="d-bar-count" id="d-num-fire">${fire}</span>
    </div>
    <div class="d-bar-row">
      <span class="d-bar-label cheeks-label">🍑 CHEEKS</span>
      <div class="bar-track bar-track-lg">
        <div class="bar-fill bar-cheeks" id="d-bar-cheeks" style="width:${cheeksPct}%"></div>
      </div>
      <span class="d-bar-count" id="d-num-cheeks">${cheeks}</span>
    </div>
    <div class="d-total">${total} vote${total !== 1 ? 's' : ''}</div>
  `;
}

function showDisplayVerdict(verdict) {
  const el = document.getElementById('d-verdict');
  if (!el) return;
  el.textContent = verdict;
  el.classList.remove('hidden');
  el.classList.add('animate-verdict');
}

// ── Util ───────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
