// Steam Classifier — wizard controller. Talks to the local Flask API.

const steps = [...document.querySelectorAll('.step')];
const segs  = [...document.querySelectorAll('.rail .seg')];
const back  = document.getElementById('back');
const next  = document.getElementById('next');
const ack   = document.getElementById('ack');

const apiKeyInput   = document.getElementById('api-key-input');
const steamIdInput  = document.getElementById('steam-id-input');
const profileInput  = document.getElementById('profile-input');
const lookupBtn     = document.getElementById('lookup-btn');
const lookupError   = document.getElementById('lookup-error');
const forgetLink    = document.getElementById('forget-link');
const setupBanner   = document.getElementById('setup-banner');
const setupBannerText = document.getElementById('setup-banner-text');
const setupError    = document.getElementById('setup-error');
const overwriteCheckbox = document.getElementById('overwrite-checkbox');
const previewError   = document.getElementById('preview-error');
const willChangeRows = document.getElementById('will-change-rows');
const unknownPreviewRows = document.getElementById('unknown-preview-rows');
const unknownRows    = document.getElementById('unknown-rows');
const countChange    = document.getElementById('count-change');
const countUnknown   = document.getElementById('count-unknown');
const countNoChange  = document.getElementById('count-nochange');
const applyLede      = document.getElementById('apply-lede');
const applyError      = document.getElementById('apply-error');
const summaryStats   = document.getElementById('summary-stats');
const backupLine      = document.getElementById('backup-line');

// 5 panels: 0..3 wizard, 4 = summary
let i = 0;
let maxStep = 0;
const labels = ['Next ›', 'Next ›', 'Next ›', 'Apply changes', 'Start over'];

// App state populated from the API.
let config = { api_key_set: false, steam_id: '', steam_path: '' };
let steamStatus = { running: true, cloud_found: false, accounts: [] };
let categoriesList = [];
let previewResult = { will_change: [], unknown: [], no_change: 0 };
let unknownSelections = {}; // app_id -> category_key
let applyResult = null;

function showError(el, message) {
  if (!el) return;
  if (message) {
    el.textContent = message;
    el.classList.add('show');
  } else {
    el.textContent = '';
    el.classList.remove('show');
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

async function apiGet(path) {
  const r = await fetch(path);
  const j = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, body: j };
}

async function apiPost(path, body, method = 'POST') {
  const r = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  const j = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, body: j };
}

async function apiDelete(path) {
  const r = await fetch(path, { method: 'DELETE' });
  const j = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, body: j };
}

function renderSetupBanner() {
  if (!steamStatus.running && steamStatus.cloud_found) {
    setupBanner.className = 'banner ok';
    setupBanner.querySelector('.ico').textContent = '✓';
    setupBannerText.textContent = 'Steam is closed on this PC, and your library file was found.';
  } else if (steamStatus.running) {
    setupBanner.className = 'banner warn';
    setupBanner.querySelector('.ico').textContent = '⚠';
    setupBannerText.textContent = 'Steam is currently open on this PC. Close it before applying any changes.';
  } else {
    setupBanner.className = 'banner warn';
    setupBanner.querySelector('.ico').textContent = '⚠';
    setupBannerText.textContent = "Your Steam library file wasn't found. Check the install path and try again.";
  }
}

function renderPreview() {
  countChange.textContent = previewResult.will_change.length;
  countUnknown.textContent = previewResult.unknown.length;
  countNoChange.textContent = previewResult.no_change;

  willChangeRows.innerHTML = previewResult.will_change.map((g) => {
    const fromHtml = g.from
      ? `<span class="cat-old">${escapeHtml(g.from)}</span>`
      : `<span class="cat-old none">Uncategorised</span>`;
    return `<div class="row">
      <div class="name">${escapeHtml(g.name)} <span class="appid">#${g.app_id}</span></div>
      <div class="change-map">${fromHtml}<span class="arrow">→</span><span class="cat-new">${escapeHtml(g.to_display)}</span></div>
    </div>`;
  }).join('') || '<p class="muted-note">Nothing to change.</p>';

  unknownPreviewRows.innerHTML = previewResult.unknown.map((g) => {
    return `<div class="row">
      <div class="name">${escapeHtml(g.name)} <span class="appid">#${g.app_id}</span></div>
      <div class="change-map cat-same">Not recognised &mdash; sorted next step</div>
    </div>`;
  }).join('') || '<p class="muted-note">Nothing unrecognised.</p>';
}

function renderUnknownStep() {
  if (previewResult.unknown.length === 0) {
    unknownRows.innerHTML = '<p class="muted-note">No new games to sort this time.</p>';
    return;
  }
  unknownRows.innerHTML = previewResult.unknown.map((g) => {
    const options = ['<option value="">Choose a category&hellip;</option>']
      .concat(categoriesList.map((c) => {
        const selected = unknownSelections[g.app_id] === c ? ' selected' : '';
        return `<option value="${escapeHtml(c)}"${selected}>${escapeHtml(c)}</option>`;
      }))
      .join('');
    return `<div class="row">
      <div class="name">${escapeHtml(g.name)} <span class="appid">#${g.app_id}</span></div>
      <select class="unknown-select" data-app-id="${g.app_id}" data-name="${escapeHtml(g.name)}">${options}</select>
    </div>`;
  }).join('');

  unknownRows.querySelectorAll('.unknown-select').forEach((sel) => {
    sel.addEventListener('change', () => {
      const appId = sel.dataset.appId;
      if (sel.value) {
        unknownSelections[appId] = sel.value;
      } else {
        delete unknownSelections[appId];
      }
    });
  });
}

function buildAssignments() {
  const assignments = {};
  previewResult.will_change.forEach((g) => {
    (assignments[g.to] = assignments[g.to] || []).push(g.app_id);
  });
  previewResult.unknown.forEach((g) => {
    const cat = unknownSelections[g.app_id];
    if (cat) {
      (assignments[cat] = assignments[cat] || []).push(g.app_id);
    }
  });
  return assignments;
}

function buildLearned() {
  const learned = {};
  previewResult.unknown.forEach((g) => {
    const cat = unknownSelections[g.app_id];
    if (cat) learned[g.name] = cat;
  });
  return learned;
}

function updateApplyLede() {
  const count = previewResult.will_change.length + Object.keys(unknownSelections).length;
  applyLede.textContent = `${count} game${count === 1 ? '' : 's'} will be sorted into collections. Your library file is backed up first.`;
}

function canApply() {
  return !!(ack && ack.checked) && steamStatus.running === false;
}

function render() {
  steps.forEach((s, k) => s.classList.toggle('show', k === i));
  segs.forEach((s, k) => {
    s.classList.toggle('active', k === i);
    s.classList.toggle('done', k < i || i === 4);
  });
  back.style.visibility = (i === 0 || i === 4) ? 'hidden' : 'visible';
  next.textContent = labels[i];
  next.className = 'btn ' + (i === 3 ? 'primary' : 'blue');
  if (i === 3) {
    next.disabled = !canApply();
  } else {
    next.disabled = false;
  }
}

async function loadInitialData() {
  const [cfgRes, statusRes, catsRes] = await Promise.all([
    apiGet('/api/config'),
    apiGet('/api/steam-status'),
    apiGet('/api/categories'),
  ]);
  if (cfgRes.ok) {
    config = cfgRes.body;
    steamIdInput.value = config.steam_id || '';
    if (config.api_key_set) {
      apiKeyInput.placeholder = '•••••••••••••••• (saved — enter a new key to replace it)';
    }
  }
  if (statusRes.ok) {
    steamStatus = statusRes.body;
    renderSetupBanner();
  }
  if (catsRes.ok) {
    categoriesList = catsRes.body.categories || [];
  }
  render();
}

async function refreshSteamStatus() {
  const res = await apiGet('/api/steam-status');
  if (res.ok) {
    steamStatus = res.body;
    renderSetupBanner();
  }
}

lookupBtn.addEventListener('click', async () => {
  showError(lookupError, '');
  const apiKey = apiKeyInput.value.trim();
  const profile = profileInput.value.trim();
  if (!apiKey) {
    showError(lookupError, 'Enter your Steam Web API key above first.');
    return;
  }
  if (!profile) {
    showError(lookupError, 'Enter a profile name or URL to look up.');
    return;
  }
  const res = await apiPost('/api/resolve-id', { api_key: apiKey, profile });
  if (res.ok) {
    steamIdInput.value = res.body.steam_id;
  } else {
    showError(lookupError, res.body.error || 'Could not resolve that profile.');
  }
});

forgetLink.addEventListener('click', async () => {
  await apiDelete('/api/config');
  config = { api_key_set: false, steam_id: '', steam_path: '' };
  apiKeyInput.value = '';
  apiKeyInput.placeholder = 'Paste your Steam Web API key';
  steamIdInput.value = '';
  showError(setupError, '');
});

overwriteCheckbox.addEventListener('change', async () => {
  await runPreview();
});

ack.addEventListener('change', render);

async function runPreview() {
  showError(previewError, '');
  const apiKey = apiKeyInput.value.trim();
  const steamId = steamIdInput.value.trim();
  const res = await apiPost('/api/preview', {
    api_key: apiKey,
    steam_id: steamId,
    overwrite: overwriteCheckbox.checked,
  });
  if (res.ok) {
    previewResult = res.body;
    unknownSelections = {};
    renderPreview();
    renderUnknownStep();
    updateApplyLede();
    return true;
  }
  showError(previewError, res.body.error || 'Could not build a preview.');
  return false;
}

async function goStep1to2() {
  showError(setupError, '');
  const apiKey = apiKeyInput.value.trim();
  const steamId = steamIdInput.value.trim();
  if (!apiKey) {
    showError(setupError, 'Enter your Steam Web API key to continue.');
    return false;
  }
  if (!steamId) {
    showError(setupError, 'Enter your 64-bit Steam ID, or use Look up above.');
    return false;
  }
  const saveRes = await apiPost('/api/config', {
    api_key: apiKey,
    steam_id: steamId,
    steam_path: config.steam_path || '',
  });
  if (!saveRes.ok) {
    showError(setupError, saveRes.body.error || 'Could not save your settings.');
    return false;
  }
  config.api_key_set = true;
  config.steam_id = steamId;
  return runPreview();
}

function goStep2to3() {
  showError(previewError, '');
  return true;
}

function goStep3to4() {
  updateApplyLede();
  return true;
}

async function goApply() {
  showError(applyError, '');
  if (!canApply()) return false;
  const res = await apiPost('/api/apply', {
    assignments: buildAssignments(),
    overwrite: overwriteCheckbox.checked,
    acknowledged: true,
    learned: buildLearned(),
  });
  if (res.ok) {
    applyResult = res.body;
    renderSummary();
    return true;
  }
  showError(applyError, res.body.error || 'Could not apply your changes.');
  return false;
}

function renderSummary() {
  const learnedCount = Object.keys(buildLearned()).length;
  const assigned = applyResult.assigned || 0;
  const noChange = previewResult.no_change || 0;
  summaryStats.innerHTML = `
    <div class="stat"><div class="v">${assigned}</div><div class="k">Categorised</div></div>
    <div class="stat"><div class="v">${learnedCount}</div><div class="k">Newly learned</div></div>
    <div class="stat"><div class="v">${noChange}</div><div class="k">Left as-is</div></div>
  `;
  backupLine.textContent = `Backup saved: ${applyResult.backup || ''}`;
}

function resetWizard() {
  i = 0;
  maxStep = 0;
  ack.checked = false;
  overwriteCheckbox.checked = false;
  previewResult = { will_change: [], unknown: [], no_change: 0 };
  unknownSelections = {};
  applyResult = null;
  showError(setupError, '');
  showError(previewError, '');
  showError(applyError, '');
  showError(lookupError, '');
  refreshSteamStatus();
  render();
}

next.addEventListener('click', async () => {
  if (i === 4) { resetWizard(); return; }
  if (i === 3) {
    if (!canApply()) return;
    next.disabled = true;
    const ok = await goApply();
    next.disabled = !canApply();
    if (!ok) return;
    i = 4;
    maxStep = Math.max(maxStep, i);
    render();
    return;
  }

  next.disabled = true;
  let ok = true;
  if (i === 0) ok = await goStep1to2();
  else if (i === 1) ok = goStep2to3();
  else if (i === 2) ok = goStep3to4();
  next.disabled = false;

  if (!ok) return;
  i = Math.min(i + 1, 4);
  maxStep = Math.max(maxStep, i);
  if (i === 3) await refreshSteamStatus();
  render();
});

back.addEventListener('click', () => {
  i = Math.max(i - 1, 0);
  render();
});

segs.forEach((s) => s.addEventListener('click', () => {
  const t = +s.dataset.seg;
  if (t <= 3 && t <= maxStep) {
    i = t;
    render();
  }
}));

loadInitialData();
