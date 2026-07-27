(() => {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const missionMap = {
    'Repository Review': 'reviewWorkspace',
    'Pull Request Review': 'reviewChangedFiles',
    'Release Verification': 'finalProof',
    'Battle Comparison': 'battleTests',
    'Final Proof': 'finalProof',
    'IDE Review': 'ideBenchContract',
    'Custom Mission': 'v2Mission',
  };
  const officers = [
    ['Cpl', 'Coordinates permanent officers'],
    ['Quartermaster', 'Capacity + weapons + loadout'],
    ['Scout', 'Repository discovery'],
    ['Engineer', 'Construction + contracts'],
    ['Medic', 'Diagnosis + safe repair'],
    ['Mechanic', 'Runtime + concurrency'],
    ['Analyst', 'Root causes + disagreement'],
    ['Judge', 'Evidence adjudication'],
    ['Hermes', 'Accurate delivery'],
    ['Archivist', 'Verified experience'],
    ['Challenger', 'Battle opposition'],
    ['Commander', 'Mission authority'],
  ];
  const weapons = [
    'Static Analysis',
    'Regression Tests',
    'Security Scanner',
    'Permanent Officer Reasoning',
    'Verified Experience Retrieval',
    'Recurrence Detection',
    'Optional Model Reasoning',
    'Battle Compare',
    'Evidence Export',
    'IDE Contract Probe',
  ];
  let state = {
    status: 'Standing By',
    workspace: 'sergeant',
    branch: '—',
    history: [],
    last: null,
    platform: 'IDE',
    settings: {
      policy: 'disabled',
      provider: 'disabled',
      baseUrl: '',
      model: '',
      protocol: 'auto',
      council: 'adaptive',
      maxRounds: 2,
      maxMembers: 5,
    },
  };

  const send = (payload) => {
    try {
      if (typeof window.sergeantHostSend === 'function') {
        window.sergeantHostSend(JSON.stringify(payload));
        return true;
      }
    } catch (error) {
      notice(error.message, true);
    }
    return false;
  };

  function notice(message, error = false) {
    const element = $('#hostNotice');
    element.textContent = message || '';
    element.classList.toggle('show', Boolean(message));
    element.classList.toggle('error', error);
  }

  function page(id) {
    $$('.page').forEach((element) => element.classList.toggle('active', element.id === id));
    $$('[data-page]').forEach((button) => button.classList.toggle('active', button.dataset.page === id));
  }

  function phase(progress) {
    const percentage = Math.max(0, Math.min(100, Number(progress) || 0));
    $('#progressBar').style.width = `${percentage}%`;
    $('#dashboardPhase').style.width = `${percentage}%`;
    $('#progressPct').textContent = `${percentage}%`;
    const labels = ['Mission Started', 'Evidence Collected', 'Officer Review', 'Evidence Challenge', 'Sergeant Report'];
    $('#timeline').innerHTML = labels.map((label, index) => {
      const cutoff = (index + 1) * 20;
      const className = percentage >= cutoff ? 'done' : percentage > index * 20 ? 'running' : '';
      return `<div class="${className}">${percentage >= cutoff ? '✓' : index + 1} ${label}</div>`;
    }).join('');
  }

  function ensureCouncilControls() {
    if ($('#cplMaxRoundsInput')) return;
    const council = $('#llmCouncilSelect');
    if (!council) return;
    const row = document.createElement('div');
    row.className = 'form-grid';
    row.innerHTML = '<label>Maximum Optional Rounds<input id="cplMaxRoundsInput" type="number" min="1" max="6" value="2"></label><label>Maximum Optional Models<input id="cplMaxMembersInput" type="number" min="1" max="12" value="5"></label>';
    council.closest('.form-grid')?.after(row);
  }

  function selectedSettings() {
    ensureCouncilControls();
    return {
      policy: $('#llmPolicySelect').value,
      provider: $('#providerSelect').value,
      baseUrl: $('#llmBaseUrlInput').value.trim(),
      model: $('#llmModelInput').value.trim(),
      protocol: $('#llmProtocolSelect').value,
      council: $('#llmCouncilSelect').value,
      maxRounds: Math.max(1, Math.min(6, Number($('#cplMaxRoundsInput').value) || 2)),
      maxMembers: Math.max(1, Math.min(12, Number($('#cplMaxMembersInput').value) || 5)),
    };
  }

  function modelSupportEnabled(settings = selectedSettings()) {
    return settings.policy !== 'disabled' && settings.provider !== 'disabled';
  }

  function cplRouteLabel(settings = selectedSettings()) {
    const provider = settings.provider || 'disabled';
    const model = settings.model || 'provider selection';
    if (!modelSupportEnabled(settings)) return 'Disabled · model-free permanent officers';
    return `Optional · ${settings.council || 'adaptive'} · ${provider} · ${model} · ${settings.maxRounds || 2}r/${settings.maxMembers || 5}m`;
  }

  function synchronizeOptionalCheckbox(settings = selectedSettings()) {
    const control = $('#optionalModelReasoning');
    if (control) control.checked = modelSupportEnabled(settings);
    const indicator = $('#optionalModelState');
    if (indicator) {
      indicator.textContent = modelSupportEnabled(settings) ? 'ENABLED' : 'DISABLED';
      indicator.className = modelSupportEnabled(settings) ? 'pass' : 'work';
    }
  }

  function saveCplSettings() {
    const settings = selectedSettings();
    state.settings = { ...state.settings, ...settings };
    $('#semanticRoute').textContent = cplRouteLabel(settings);
    synchronizeOptionalCheckbox(settings);
    missionSummary();
    send({ type: 'saveSettings', settings });
  }

  function applySettings(settings = {}) {
    ensureCouncilControls();
    state.settings = { ...state.settings, ...settings };
    const mappings = [
      ['#llmPolicySelect', 'policy'],
      ['#providerSelect', 'provider'],
      ['#llmBaseUrlInput', 'baseUrl'],
      ['#llmModelInput', 'model'],
      ['#llmProtocolSelect', 'protocol'],
      ['#llmCouncilSelect', 'council'],
      ['#cplMaxRoundsInput', 'maxRounds'],
      ['#cplMaxMembersInput', 'maxMembers'],
    ];
    for (const [selector, key] of mappings) {
      const element = $(selector);
      if (element && state.settings[key] !== undefined && state.settings[key] !== null) {
        const requested = String(state.settings[key]);
        element.value = key === 'provider' && requested === 'fcc' ? 'cpl' : requested;
      }
    }
    $('#semanticRoute').textContent = cplRouteLabel(state.settings);
    synchronizeOptionalCheckbox(state.settings);
  }

  function missionSummary() {
    const mission = $('input[name="level"]:checked')?.value || 'Repository Review';
    const settings = selectedSettings();
    const enabled = modelSupportEnabled(settings);
    $('#missionSummary').innerHTML = [
      ['Mission', mission],
      ['Workspace', state.workspace],
      ['Priority', $('#priority').value],
      ['Permissions', 'Read + Proof'],
      ['Permanent Officers', 'Model-free formation ready', 'pass'],
      ['Optional Model Support', cplRouteLabel(settings), enabled ? 'pass' : 'work'],
      ['Optional Limits', enabled ? `${settings.maxRounds} rounds · ${settings.maxMembers} models` : 'Not applicable'],
      ['Sergeant', 'Final authority', 'pass'],
    ].map(([label, value, className = '']) => (
      `<div class="row"><span>${label}</span><b class="${className}">${value}</b></div>`
    )).join('');
  }

  function renderOfficers() {
    const card = (officer, index) => `<div class="officer"><b>${officer[0]}</b><small>${officer[1]}</small><div class="row"><span>Status</span><b class="${index < 8 ? 'pass' : 'work'}">${index < 8 ? 'READY' : 'IDLE'}</b></div></div>`;
    $('#officers').innerHTML = officers.map(card).join('');
    $('#dashboardOfficers').innerHTML = officers.slice(0, 5).map(card).join('');
    $('#armoury').innerHTML = weapons.map((weapon) => `<div class="weapon"><b>${weapon}</b><small>Available weapon · permission gated · evidence output.</small><div class="row"><span>Status</span><b class="${weapon === 'Optional Model Reasoning' ? 'work' : 'pass'}">${weapon === 'Optional Model Reasoning' ? 'OPT-IN' : 'READY'}</b></div></div>`).join('');
  }

  function renderConfidence() {
    const rows = [
      ['Deterministic Evidence', 98],
      ['Permanent Officer Coverage', 96],
      ['Judge Admission Discipline', 94],
      ['Verified Experience', 92],
      ['Sergeant Authority', 100],
    ];
    $('#confidence').innerHTML = rows.map((row) => `<div class="confidence-line"><span>${row[0]}</span><span class="bar"><i style="width:${row[1]}%"></i></span><b>${row[1]}%</b></div>`).join('');
  }

  function renderDoctrine() {
    const cards = [
      ['Model-Free Core', 'Cpl and the permanent officers review repositories without requiring a provider login, model API, local model or GPU.'],
      ['Evidence First', 'Static findings, runtime proof, officer findings, UI behavior, docs proof, API results and conflicts are gathered before claims.'],
      ['Permanent Officers', 'Every officer receives universal training, owns a specialty, retrieves verified experience and can request a safer rebrief.'],
      ['Optional Model Support', 'One model or a bounded multi-model council may deepen a named question only after the owner enables it. Models are support engines, not officers or votes.'],
      ['Verified Experience', 'Only human/Judge-confirmed outcomes update Cpl, officers, optional model support and weapon experience. Raw model opinions never become doctrine.'],
      ['Anti-Repeat', 'Applicable previous experience must influence the next mission or Cpl records why it could not be reused. Recurrence triggers stronger prevention proof.'],
      ['Cross Verification', 'Evidence sources are compared and disagreements are investigated rather than averaged away.'],
      ['Finish, Then Prove', 'Complete the intended implementation, review it, freeze it, then perform clean-clone and runtime proof.'],
      ['Claims Match Implementation', 'Documentation and marketing claims are checked against actual behavior before release.'],
    ];
    $('#doctrineCards').innerHTML = cards.map((card) => `<div class="evidence"><h3>${card[0]}</h3><p>${card[1]}</p></div>`).join('');
    const roadmap = [
      ['Operations', 'Live mission monitoring, reusable templates and multi-repository operations.'],
      ['Battle Calibration', 'Larger verified battle history, optional model reliability and confidence calibration.'],
      ['Review Collaboration', 'Collaborative reviews, replay and shared audit trails.'],
      ['Knowledge / Learning', 'Knowledge base integration, analytics and recurring-issue trends.'],
      ['Plugin / Weapon SDK', 'Permission-gated analysis weapons with defined inputs, outputs and evidence formats.'],
    ];
    $('#roadmapCards').innerHTML = roadmap.map((card) => `<div class="evidence"><h3>${card[0]}</h3><p>${card[1]}</p><b class="work">POST‑V2</b></div>`).join('');
    const guide = ['What is Sergeant?', 'Model-Free Review Doctrine', 'How Sergeant Reviews', 'Mission System', 'Cpl Coordination', 'Permanent Officers', 'Optional Model Reasoning', 'Optional Council Limits', 'Verified Experience', 'Armoury', 'Evidence', 'Battle Testing', 'Safety', 'FAQ'];
    $('#guideCards').innerHTML = guide.map((title) => `<div class="guide"><b>${title}</b><p>Explains how ${title.toLowerCase()} fits Owner → Sergeant → Cpl → Permanent Officers → Armoury → Evidence → Judge → Sergeant Verdict, with optional models only after explicit opt-in.</p></div>`).join('');
  }

  function settings(tab = 'general') {
    const enabled = modelSupportEnabled(state.settings);
    const providerDetails = [
      'Sergeant core: model-free permanent officers',
      `Optional model support: ${enabled ? 'enabled' : 'disabled'}`,
      `Policy: ${state.settings.policy || 'disabled'}`,
      `Engine route: ${state.settings.provider || 'disabled'}`,
      `Optional model: ${state.settings.model || 'none selected'}`,
      `Protocol: ${state.settings.protocol || 'auto'}`,
      `Optional depth: ${state.settings.council || 'adaptive'}`,
      `Maximum optional rounds: ${state.settings.maxRounds || 2}`,
      `Maximum optional models: ${state.settings.maxMembers || 5}`,
      'API credentials: environment only',
      'Final authority: Sergeant',
    ];
    const map = {
      general: ['Auto-save reports', 'Confirm before launch', 'Show commander summary', 'Model-free review is the default'],
      providers: providerDetails,
      writer: ['Disabled by default', 'Draft patch only', 'Human approval required', 'Never auto-merge'],
      permissions: ['Owner approval gates', 'Read-only default', 'Final proof confirmation'],
      ide: ['Workspace awareness', 'Active file', 'Git branch', 'Changed files', 'Python / Git / virtual environment'],
      github: ['Repository status', 'PR comments planned', 'Commit evidence'],
      battle: ['Battle comparison', 'UI proof checks', 'Regression baseline', 'Permanent-officer and optional-model outcomes'],
      debug: ['Runtime logs', 'Bridge diagnostics', 'Optional model rounds and final gaps', 'Optional route status through sergeant cpl-status'],
      advanced: ['Export UI contract', 'Reset local evidence', 'Owner-selected required model policy', 'Maximum bounded optional council'],
    };
    $$('#settingTabs button').forEach((button) => button.classList.toggle('active', button.dataset.tab === tab));
    $('#settingsContent').innerHTML = (map[tab] || []).map((item) => `<div class="setting"><span>${item}</span><span class="toggle"></span></div>`).join('');
  }

  function renderEvidence() {
    const findings = state.last?.findings || state.last?.payload?.cpl_review?.findings || [];
    const defaults = [
      ['Static Evidence', 'Repository structure, changed files and source findings.'],
      ['Runtime Evidence', 'Command exit status and captured runtime output.'],
      ['Permanent Officer Evidence', 'Grounded reports, disagreements, falsifiers and officer rebriefs.'],
      ['Experience Evidence', 'Verified and rejected prior outcomes supplied to Cpl and the permanent officers.'],
      ['Recurrence Evidence', 'Previous incidents and the stronger prevention proof required when an issue returns.'],
      ['Optional Model Evidence', modelSupportEnabled(state.settings) ? 'Owner-enabled model support and its Judge-qualified disposition.' : 'Disabled for this model-free mission.'],
      ['UI Evidence', 'Command Center controls and rendered behavior.'],
      ['Docs Verification', 'README, release notes and workflow claims.'],
      ['Battle Evidence', 'Comparison fixtures, regressions and disagreements.'],
      ['External Review', 'Imported reviewer evidence when explicitly enabled.'],
    ];
    $('#evidenceCards').innerHTML = defaults.map((item, index) => `<div class="evidence"><h3>${item[0]}</h3><p>${findings[index]?.message || findings[index]?.evidence || item[1]}</p><b class="${state.last ? 'pass' : 'work'}">${state.last ? 'RUNTIME' : 'AWAITING MISSION'}</b></div>`).join('');
  }

  function renderHistory() {
    const history = state.history || [];
    $('#recentMissions').innerHTML = history.slice(0, 3).map((item) => `<div class="row"><span>${item.id || '—'} · ${item.mission || item.title}</span><b class="${String(item.result || item.verdict).includes('PASS') ? 'pass' : 'work'}">${item.result || item.verdict}</b></div>`).join('') || '<p class="muted">No runtime missions yet.</p>';
    $('#historyBody').innerHTML = history.map((item) => `<tr><td>${item.id || '—'}</td><td>${item.date || item.finishedAt || '—'}</td><td class="${String(item.result || item.verdict).includes('PASS') ? 'pass' : 'work'}">${item.result || item.verdict}</td><td>${item.mission || item.title}</td><td>${item.duration || '—'}</td></tr>`).join('');
    $('#latestReport').innerHTML = state.last
      ? `<div class="row"><span>Mission</span><b>${state.last.title}</b></div><div class="row"><span>Verdict</span><b class="${String(state.last.summary?.verdict).includes('PASS') ? 'pass' : 'work'}">${state.last.summary?.verdict}</b></div><div class="row"><span>Finished</span><b>${state.last.finishedAt || '—'}</b></div>`
      : '<p class="muted">No runtime report yet.</p>';
  }

  function apply(snapshot) {
    state = { ...state, ...(snapshot || {}) };
    applySettings(state.settings || {});
    const running = Boolean(state.running) || String(state.status).toLowerCase() === 'running';
    $('#sideStatus').textContent = running ? 'Reviewing' : state.status;
    $('#sideMessage').textContent = running ? 'Permanent officers are working against live evidence.' : 'Model-free mission ready. Awaiting orders.';
    $('#commanderStatus').textContent = running ? 'Reviewing' : state.status;
    $('#currentMission').textContent = state.runningTitle || state.last?.title || 'Repository Review';
    $('#currentWorkspace').textContent = state.workspace;
    $('#workspaceMeta').textContent = `Branch: ${state.branch || '—'} · ${state.changedFilesCount || 0} changed file(s)`;
    $('#commanderVerdict').textContent = state.last?.summary?.verdict || state.last?.verdict || 'WAITING';
    $('#verdictMeta').textContent = state.last ? 'Latest runtime evidence loaded.' : 'No runtime evidence yet.';
    $('#activeFile').textContent = state.activeFile || '—';
    $('#changedFiles').textContent = state.changedFilesCount || 0;
    $('#platformName').textContent = state.platform || 'IDE';
    $('#runtimePlatform').textContent = `${state.platform || 'IDE'} Runtime`;
    const workspace = $('#workspaceSelect');
    if (state.workspace && !Array.from(workspace.options).some((option) => option.value === state.workspace)) {
      workspace.add(new Option(state.workspace, state.workspace));
    }
    workspace.value = state.workspace;
    phase(running ? state.progress || 36 : state.last ? 100 : 0);
    $('#operation').textContent = running
      ? state.runningTitle || 'Permanent officers are collecting and challenging evidence…'
      : state.last
        ? `${state.last.summary?.verdict || state.last.verdict} — report ready.`
        : 'Waiting for runtime…';
    $('#liveLog').textContent = running
      ? `[${new Date().toLocaleTimeString()}] Sergeant model-free mission running through ${state.platform} host. ${cplRouteLabel(state.settings)}.`
      : state.last
        ? `[${new Date().toLocaleTimeString()}] Mission completed. Evidence Locker updated.`
        : '';
    renderHistory();
    renderEvidence();
    missionSummary();
    settings($('#settingTabs button.active')?.dataset.tab || 'general');
    notice(state.notice || '', Boolean(state.error));
    if (running) page('progress');
    else if (state.last?.justFinished) page('reports');
  }

  function launch(action) {
    page('progress');
    phase(12);
    $('#operation').textContent = 'Sergeant accepted the mission. Waiting for deterministic evidence and permanent-officer reports…';
    send({
      type: 'run',
      action,
      briefing: $('#missionBriefing').value,
      priority: $('#priority').value,
      settings: selectedSettings(),
    });
  }

  document.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]');
    if (action) {
      event.preventDefault();
      launch(action.dataset.action);
      return;
    }
    const navigation = event.target.closest('[data-page]');
    if (navigation) {
      event.preventDefault();
      page(navigation.dataset.page);
    }
  });

  $$('input[name="level"]').forEach((radio) => {
    radio.onchange = () => {
      $$('.mission-types label').forEach((label) => label.classList.toggle('selected', label.querySelector('input').checked));
      missionSummary();
    };
  });
  ensureCouncilControls();
  $('#priority').onchange = missionSummary;
  $('#deployBtn').onclick = () => launch(missionMap[$('input[name="level"]:checked').value]);
  for (const selector of ['#llmPolicySelect', '#providerSelect', '#llmBaseUrlInput', '#llmModelInput', '#llmProtocolSelect', '#llmCouncilSelect', '#cplMaxRoundsInput', '#cplMaxMembersInput']) {
    $(selector).addEventListener('change', saveCplSettings);
  }
  $('#optionalModelReasoning').addEventListener('change', (event) => {
    if (event.target.checked) {
      $('#llmPolicySelect').value = 'preferred';
      if ($('#providerSelect').value === 'disabled') $('#providerSelect').value = 'auto';
    } else {
      $('#llmPolicySelect').value = 'disabled';
      $('#providerSelect').value = 'disabled';
    }
    saveCplSettings();
  });
  $('#workspaceSelect').onchange = () => send({ type: 'selectWorkspace', workspace: $('#workspaceSelect').value });
  $('#openLatestReport').onclick = () => send({ type: 'openLast' });
  $('#exportBattleReport').onclick = () => send({ type: 'exportLast' });
  $('#copyVerdict').onclick = $('#quickCopy').onclick = () => send({ type: 'copyLast' });
  $('#refreshMission').onclick = $('#refreshReports').onclick = () => send({ type: 'refresh' });
  $('#settingTabs').onclick = (event) => {
    const button = event.target.closest('button');
    if (button) settings(button.dataset.tab);
  };
  $('#globalSearch').oninput = () => {
    const query = $('#globalSearch').value.trim().toLowerCase();
    $$('.page.active .panel,.page.active .evidence,.page.active .guide,.page.active .officer,.page.active .weapon').forEach((element) => {
      element.classList.toggle('search-hidden', Boolean(query) && !element.textContent.toLowerCase().includes(query));
    });
  };
  window.addEventListener('message', (event) => {
    if (['sergeantState', 'state'].includes(event.data?.type)) apply(event.data.state);
  });

  function updateClock() {
    const clock = $('#clock');
    if (clock) clock.textContent = new Date().toLocaleTimeString();
  }

  updateClock();
  const clockTimer = setInterval(updateClock, 1000);
  let clockStopped = false;
  function stopClock() {
    if (clockStopped) return;
    clockStopped = true;
    clearInterval(clockTimer);
  }
  window.addEventListener('pagehide', stopClock, { once: true });
  window.addEventListener('beforeunload', stopClock, { once: true });
  window.sergeantClock = { stop: stopClock, isStopped: () => clockStopped };

  renderOfficers();
  renderConfidence();
  renderDoctrine();
  applySettings(state.settings);
  settings();
  renderEvidence();
  renderHistory();
  missionSummary();
  phase(0);
  if (!send({ type: 'ready' })) {
    notice('Standalone preview mode — model-free by default. Open through the Sergeant IDE extension for live missions.');
  }
})();
