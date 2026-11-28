'use strict';

(() => {
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>\x22']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\x22': '&quot;', "'": '&#39;' })[char]);
  const iconPaths = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    settings: '<path d="M4 7h16M4 17h16"/><circle cx="8" cy="7" r="3" fill="currentColor" stroke="none"/><circle cx="16" cy="17" r="3" fill="currentColor" stroke="none"/>',
    chip: '<rect x="5" y="5" width="14" height="14" rx="3"/><path d="M9 2v3m6-3v3M9 19v3m6-3v3M2 9h3m-3 6h3m14-6h3m-3 6h3M9 9h6v6H9z"/>',
    camera: '<path d="M4 7h4l2-3h4l2 3h4v13H4Z"/><circle cx="12" cy="13" r="4"/>',
    tree: '<path d="m12 3-5 6h3l-5 6h5v5h4v-5h5l-5-6h3Z"/>',
    robot: '<rect x="4" y="7" width="16" height="13" rx="3"/><path d="M12 3v4M1 12h3m16 0h3M8 16h8M8 11h.01M16 11h.01"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    external: '<path d="M14 3h7v7m0-7-11 11M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
    refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 6a8 8 0 0 1 13 3M5 15a8 8 0 0 0 13 3"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    code: '<path d="m8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16"/>',
    box: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 5v10l9 5 9-5V8M12 13v10"/>',
    link: '<path d="m10 13 4-4m-6 7-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 1 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0" transform="translate(1 -1)"/>'
  };
  const icon = (name) => `<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>${iconPaths[name] || iconPaths.file}</svg>`;
  const projectIcon = (id) => id.includes('button') ? 'grid' : id.includes('hachimo') ? 'chip' : id.includes('recorder') ? 'camera' : id.includes('christmas') ? 'tree' : id.includes('robot') ? 'robot' : 'box';
  const groupIcon = (group) => ({ '设计': 'chip', '固件': 'code', '制造': 'folder', '外壳': 'box', '需求': 'file' })[group] || 'file';
  const groups = ['全部', '设计', '固件', '制造', '外壳', '需求'];
  const noteKey = 'maker-lab.workbench.notes.v1';
  const state = { data: null, view: 'project', projectId: 'agent-button-deck', filter: '全部', live: null, connection: 'checking', statusError: '', statusGeneration: 0, actionBusy: '', notes: { server: {}, local: {} }, noteMode: null, remoteNotesLoaded: false, remoteNotesError: '', localStorageError: '', toastTimer: null };

  function safeUrl(value) {
    if (!value || typeof value !== 'string') return '';
    try {
      const url = new URL(value, window.location.href);
      return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
    } catch { return ''; }
  }

  function canVisit(value) {
    const url = safeUrl(value);
    if (!url) return false;
    const parsed = new URL(url);
    return !(parsed.origin === window.location.origin && parsed.pathname.startsWith('/documents/') && state.connection !== 'connected');
  }

  function link(value, label, className = '', includeIcon = false) {
    const url = safeUrl(value);
    if (!url || !canVisit(value)) return `<span class='${escapeHtml(className)} document-disabled' title='连接此 Mac 后可打开本地文件'>${escapeHtml(label)}</span>`;
    return `<a class='${escapeHtml(className)}' href='${escapeHtml(url)}' target='_blank' rel='noopener noreferrer'>${escapeHtml(label)}</a>`;
  }

  function formatTime(value, includeDate = false) {
    const date = new Date(value);
    if (!value || Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('zh-CN', includeDate ? { timeZone: 'Asia/Shanghai', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false } : { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false });
  }

  async function requestJson(path, options = {}, timeout = 9000) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(path, { cache: 'no-store', credentials: 'same-origin', ...options, signal: controller.signal });
      let body;
      try { body = await response.json(); } catch { throw new Error('服务器没有返回可读取的数据'); }
      if (!response.ok) throw new Error(body?.error?.message || `请求未完成（${response.status}）`);
      return body;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('连接超时，请稍后刷新');
      throw error;
    } finally { window.clearTimeout(timer); }
  }

  const postOptions = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Workbench-Request': '1' }, body: JSON.stringify(body) });
  const currentProject = () => state.data?.projects.find((project) => project.id === state.projectId) || state.data?.projects[0];
  const localAvailable = () => state.connection === 'connected' && state.live?.mode === 'local';
  const stageStatus = (status) => ({ complete: '已完成此阶段', current: '当前阶段', pending: '尚未开始', hold: '待核实' })[status] || '待核实';

  function connectionCopy() {
    if (state.connection === 'checking') return { label: '正在检查 Mac', short: '正在检查环境', kind: 'checking' };
    if (!localAvailable()) return { label: '资料预览 · 未连接此Mac', short: '资料预览 · 未连接 Mac', kind: '' };
    if (!state.live.app_installed || !state.live.cli_available) return { label: 'Mac 已连接 · 环境待检查', short: 'Mac 已连接 · 待检查', kind: 'attention' };
    if (state.live.bridge?.state && state.live.bridge.state !== 'connected') return { label: 'Mac 已连接 · 编辑器桥接未连接', short: '桥接未连接', kind: 'attention' };
    if (state.live.activation?.state === 'verified' && state.live.editor_round_trip === 'passed') return { label: 'Mac 已连接 · EDA 可用', short: 'EDA 可用', kind: 'connected' };
    if (state.live.activation?.state === 'pending') return { label: 'Mac 已连接 · EDA 待激活', short: 'Mac 已连接 · 待激活', kind: 'attention' };
    if (state.live.editor_round_trip === 'passed') return { label: 'Mac 已连接 · 工程读写已验证', short: 'Mac 已连接', kind: 'connected' };
    return { label: 'Mac 已连接 · 编辑器待核验', short: 'Mac 已连接', kind: 'connected' };
  }

  function renderShell() {
    const project = currentProject();
    const nav = [{ id: 'overview', icon: 'grid', label: '工作台总览' }, { id: 'files', icon: 'folder', label: '项目文件' }, { id: 'environment', icon: 'settings', label: '运行环境' }];
    $('#primary-nav').innerHTML = nav.map((item) => `<button class='nav-button' type='button' data-view='${item.id}' ${state.view === item.id ? "aria-current='page'" : ''}>${icon(item.icon)}<span>${item.label}</span></button>`).join('');
    $('#project-count').textContent = state.data.projects.length;
    $('#project-nav').innerHTML = state.data.projects.map((item) => `<button class='project-nav-button' type='button' data-project='${escapeHtml(item.id)}' ${['project', 'files'].includes(state.view) && item.id === project?.id ? "aria-current='page'" : ''}>${icon(projectIcon(item.id))}<span class='project-name'>${escapeHtml(item.name)}</span></button>`).join('');
    $('#breadcrumb').textContent = state.view === 'overview' ? '工作台总览' : state.view === 'environment' ? '运行环境' : project?.name || '项目';
    const status = connectionCopy();
    $('#connection-indicator').innerHTML = `<span class='status-dot ${status.kind}'></span><span>${escapeHtml(status.label)}</span>`;
    $('#sidebar-status-dot').className = `status-dot ${status.kind}`;
    $('#sidebar-status-text').textContent = status.short;
    const openButton = $('#open-eda-top');
    openButton.disabled = !localAvailable() || !state.live.app_installed || !!state.actionBusy;
    openButton.title = !localAvailable() ? '连接此 Mac 后可打开 EDA' : !state.live.app_installed ? '尚未检测到 EDA 客户端' : '在 Mac 上打开嘉立创 EDA';
    openButton.innerHTML = `${icon('chip')}<span>${state.actionBusy === 'open_eda' ? '正在打开…' : '打开 EDA'}</span>`;
    $('#workspace-updated').textContent = `资料更新于 ${state.data.updated_at || '待核实'}`;
    document.title = `${state.view === 'overview' ? '工作台总览' : state.view === 'environment' ? '运行环境' : project?.name || '项目'} · 硬件工作台`;
  }

  function previewNotice() {
    if (state.connection === 'checking' || localAvailable()) return '';
    return `<div class='notice-bar'>${icon('info')}<span>资料预览 · 未连接此Mac。可以浏览项目，Mac 操作暂不可用。</span><button class='button button-quiet notice-link' type='button' data-view='environment'>查看环境</button></div>`;
  }

  function projectHeading(project, isFiles = false) {
    return `<div class='page-heading'><div><div class='eyebrow'><span class='eyebrow-line'></span>${escapeHtml(isFiles ? '项目文件' : project.category || '当前项目')}</div><div class='project-title-line'><span class='project-symbol'>${icon(projectIcon(project.id))}</span><h1>${escapeHtml(project.name)}</h1></div><p class='project-subtitle'>${escapeHtml(isFiles ? '查看已有文件与尚未形成的交付物。文件存在与制造验证分别记录。' : project.tagline || project.summary)}</p>${!isFiles ? `<div class='project-status-line'><span class='badge current'><span class='status-dot attention'></span>${escapeHtml(project.stage_label || '待核实')}</span><span class='priority-label'>${escapeHtml(project.priority || '')}</span></div>` : ''}</div><div class='page-heading-actions'><button class='button' type='button' data-action='open_project' ${!localAvailable() || !project.workspace || state.actionBusy ? 'disabled' : ''} title='在 Mac 上打开项目目录'>${icon('folder')}${state.actionBusy === 'open_project' ? '正在打开…' : '打开项目目录'}</button></div></div>`;
  }

  function renderStages(project) {
    const stages = Array.isArray(project.stages) ? project.stages : [];
    if (!stages.length) return '';
    return `<section class='stage-section' aria-label='项目阶段'><div class='section-heading'><h2>从方案到成品</h2><span class='section-caption'>按实际证据推进</span></div><ol class='stage-track' style='--stage-count:${Math.min(stages.length, 6)}'>${stages.map((stage) => {
      const status = ['complete', 'current', 'pending', 'hold'].includes(stage.status) ? stage.status : 'pending';
      return `<li class='stage-item ${status}' title='${escapeHtml(stage.detail)}'><div class='stage-topline'><span class='stage-dot'>${status === 'complete' ? icon('check') : status === 'hold' ? '!' : ''}</span><span class='stage-line'></span></div><span class='stage-name'>${escapeHtml(stage.label)}</span><span class='stage-state'>${stageStatus(status)}</span><p class='stage-detail'>${escapeHtml(stage.detail)}</p></li>`;
    }).join('')}</ol></section>`;
  }

  function renderArtifacts(project, full = false) {
    const artifacts = Array.isArray(project.artifacts) ? project.artifacts : [];
    const filtered = artifacts.filter((item) => state.filter === '全部' || item.group === state.filter);
    return `<section class='panel ${full ? 'full-width-files' : ''}' aria-label='设计与交付文件'><div class='panel-heading'><h2>设计与交付文件</h2><span class='small-label'>${artifacts.filter((item) => item.url && item.status === 'ready').length} 项已有资料</span></div><div class='file-filters' role='group' aria-label='按文件类型筛选'>${groups.map((group) => `<button type='button' class='filter-button ${state.filter === group ? 'active' : ''}' data-filter='${group}' aria-pressed='${state.filter === group}'>${group}</button>`).join('')}</div><div class='artifact-list'>${filtered.length ? filtered.map((item) => {
      const status = ['ready', 'pending', 'hold'].includes(item.status) ? item.status : 'pending';
      const label = status === 'ready' ? '已有资料' : status === 'hold' ? '待核实' : '待形成';
      return `<div class='artifact-row'><span class='file-icon'>${icon(groupIcon(item.group))}</span><div class='artifact-content'><div class='artifact-title'>${item.url ? link(item.url, item.name, '', true) : escapeHtml(item.name)}</div><p class='artifact-detail'>${escapeHtml(item.detail)}</p>${item.url && !canVisit(item.url) ? `<p class='artifact-detail'>连接此 Mac 后可打开</p>` : ''}</div><span class='artifact-status ${status}'>${label}</span></div>`;
    }).join('') : `<div class='empty-files'>当前项目没有这一类资料记录。</div>`}</div><div class='artifact-footer'>“已有资料”表示文件可查阅，不代表电路、装配或实物已通过验收。</div></section>`;
  }

  function renderOpenItems(project) {
    const items = Array.isArray(project.open_items) ? project.open_items : [];
    return `<section class='panel'><div class='panel-heading'><h2>接下来要核实</h2><span class='open-count'>${items.length} 项</span></div><div class='panel-body'>${items.length ? `<ul class='open-items'>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : `<p class='body-muted'>当前记录中没有待核实事项。</p>`}</div></section>`;
  }

  function blankNote() { return { text: '', savedText: '', updatedAt: '', saving: false, status: '', error: '' }; }
  function getNote(mode = state.noteMode || 'local', projectId = state.projectId) {
    if (!state.notes[mode][projectId]) state.notes[mode][projectId] = blankNote();
    return state.notes[mode][projectId];
  }

  function renderNotes() {
    const mode = state.noteMode || 'local';
    const note = getNote(mode);
    const loading = state.noteMode === null;
    const serverSelected = mode === 'server';
    const location = loading ? '正在读取备注…' : serverSelected ? '保存在这台 Mac 的工作区。' : '仅保存在这个浏览器，不会自动同步到 Mac。';
    const switchButton = serverSelected ? `<button type='button' data-note-mode='local'>查看此浏览器的备注</button>` : localAvailable() && state.remoteNotesLoaded ? `<button type='button' data-note-mode='server'>查看 Mac 中的备注</button>` : '';
    return `<section class='panel notes-panel'><div class='panel-heading'><h2>项目备注</h2><span class='small-label'>${serverSelected ? 'Mac 工作区' : '此浏览器'}</span></div><div class='panel-body'><p class='note-storage'>${escapeHtml(location)}</p><label class='visually-hidden' for='project-note'>${escapeHtml(currentProject()?.name)}项目备注</label><textarea id='project-note' maxlength='8000' placeholder='记下想法、偏好，或下次继续时需要记住的事…' ${loading ? 'disabled' : ''}>${escapeHtml(note.text)}</textarea><div class='note-counter' id='note-counter'>${note.text.length} / 8000</div><div class='note-toolbar'><p class='note-save-status' id='note-save-status' aria-live='polite'></p><button type='button' class='button button-soft button-small' id='save-note' data-save-note ${loading || note.saving || (serverSelected && !localAvailable()) ? 'disabled' : ''}>${note.saving ? '保存中…' : serverSelected ? '保存备注' : '保存到浏览器'}</button></div><div class='note-switch'>${switchButton}</div></div></section>`;
  }

  function renderStatusBlock(project) {
    const sb = project.status_block;
    if (!sb) return '';
    const freeze = sb.freeze || {};
    const freezeRow = [
      `视觉方向：${freeze.visual || '待确认'}`,
      `工程尺寸：${freeze.dimensions || '待确认'}`,
      `制造：${freeze.manufacturing || '待确认'}`,
    ];
    const domains = Object.entries(sb.domain_status || {})
      .map(([k, v]) => `<div class='status-row'><span class='status-row-label'>${escapeHtml(k)}</span><div class='status-value ${v.startsWith('ready') ? 'good' : v.startsWith('draft') ? 'attention' : ''}'>${escapeHtml(v)}</div></div>`).join('');
    const decisions = (sb.decision_items || []).map(d => `<li>${escapeHtml(d)}</li>`).join('');
    return `<section class='panel' aria-label='当前状态'><div class='panel-heading'><h2>当前状态</h2><span class='badge ${sb.needs_user_decision ? 'hold' : 'ready'}'>${sb.needs_user_decision ? '需要本人决策' : 'Agent 推进中'}</span></div><div class='status-list'>
      <div class='status-row'><span class='status-row-label'>产品版本</span><div class='status-value good'>${escapeHtml(sb.version || '')}</div></div>
      <div class='status-row'><span class='status-row-label'>当前 G 阶段</span><div><div class='status-value'>${escapeHtml(sb.g_stage || '')}</div></div></div>
      <div class='status-row'><span class='status-row-label'>负责人</span><div class='status-value'>${escapeHtml(sb.owner || '')}</div></div>
      <div class='status-row'><span class='status-row-label'>最近完成</span><div><div class='status-value'>${escapeHtml(sb.last_completed || '')}</div></div></div>
      <div class='status-row'><span class='status-row-label'>下一项工作</span><div><div class='status-value'>${escapeHtml(sb.next_work || '')}</div></div></div>
      ${(sb.status_lines || []).length ? `<div class='status-row'><span class='status-row-label'>阶段状态</span><div class='status-value'>${(sb.status_lines || []).map(s => `<span class='${s.class === 'ok' ? 'good' : s.class === 'hold' ? 'hold' : 'attention'}' style='margin-right:10px'>${s.item}：${s.state}</span>`).join('')}</div></div>` : ''}
      ${(sb.blockers || []).length ? `<div class='status-row'><span class='status-row-label'>阻断</span><div><div class='status-value attention'>${sb.blockers.map(b => escapeHtml(b)).join('；')}</div></div></div>` : ''}
      ${sb.needs_user_decision && decisions ? `<div class='status-row'><span class='status-row-label'>待你决策</span><div><ul class='open-items' style='margin:0'>${decisions}</ul></div></div>` : ''}
      ${domains}
      <div class='status-row'><span class='status-row-label'>冻结三态</span><div class='status-value'>${freezeRow.map(escapeHtml).join(' · ')}</div></div>
      ${sb.product_ready === false ? `<div class='status-row'><span class='status-row-label'>产品就绪</span><div class='status-value attention'>未就绪——${escapeHtml(sb.product_ready_note || '')}</div></div>` : ''}
    </div></section>`;
  }

  function renderReferenceStudies(project) {
    const studies = Array.isArray(project.reference_studies) ? project.reference_studies : [];
    if (!studies.length) return '';
    const allowlist = state.data.documents || [];
    const cards = studies.map((study) => {
      const patterns = (study.patterns || []).map(p => `<li>${escapeHtml(p)}</li>`).join('');
      const tasks = (study.tasks || []).map(t => `<li>${escapeHtml(t)}</li>`).join('');
      const open = (study.open_questions || []).map(q => `<li>${escapeHtml(q)}</li>`).join('');
      const completeness = Object.entries(study.completeness || {})
        .map(([k, v]) => `<div class='status-row'><span class='status-row-label'>${escapeHtml(k)}</span><div class='status-value ${v === '完成' ? 'good' : 'attention'}'>${escapeHtml(v)}</div></div>`).join('');
      const docEntry = allowlist.find(d => d.path === study.study_doc);
      const docRow = study.study_doc ? `<div class='status-row'><span class='status-row-label'>研究文档</span><div class='status-value'>${docEntry ? link(`/documents/${encodeURIComponent(docEntry.id)}`, docEntry.name || docEntry.id, '') : `<code>${escapeHtml(study.study_doc)}</code>`}</div></div>` : '';
      return `<div class='reference-card'><div class='artifact-title'>${link(study.url, study.name, '', true)}</div>
        <div class='status-row'><span class='status-row-label'>许可边界</span><div class='status-value attention'>${escapeHtml(study.license || '')}</div></div>
        ${completeness}
        ${study.studied_at ? `<div class='status-row'><span class='status-row-label'>研究日期</span><div class='status-value'>${escapeHtml(study.studied_at)}</div></div>` : ''}
        ${docRow}
        ${patterns ? `<div class='status-row'><span class='status-row-label'>可借鉴模式</span><div><ul class='open-items' style='margin:0'>${patterns}</ul></div></div>` : ''}
        ${tasks ? `<div class='status-row'><span class='status-row-label'>对应任务</span><div><ul class='open-items' style='margin:0'>${tasks}</ul></div></div>` : ''}
        ${open ? `<div class='status-row'><span class='status-row-label'>待核实</span><div><ul class='open-items' style='margin:0'>${open}</ul></div></div>` : ''}
        ${study.boundary ? `<p class='body-muted' style='margin:9px 0 0;font-size:13px'>${escapeHtml(study.boundary)}</p>` : ''}</div>`;
    }).join('');
    return `<section class='panel' aria-label='参考工程研究'><div class='panel-heading'><h2>参考工程研究</h2><span class='small-label'>只借鉴模式，不复制文件</span></div><div class='panel-body'>${cards}</div></section>`;
  }

  function renderProject() {
    const project = currentProject();
    if (!project) return `<div class='initial-state'><h1>还没有项目记录</h1><p>工作台数据中尚未包含项目。</p></div>`;
    const source = project.source || {};
    return `${previewNotice()}${projectHeading(project)}${renderStatusBlock(project)}${renderReferenceStudies(project)}<section class='project-overview'><div><div class='info-label'>这次采用的路线</div><p class='route-text'>${escapeHtml(project.route)}</p></div><div class='next-action'><div class='next-label'>下一步</div><p>${escapeHtml(project.next_step)}</p></div></section>${renderStages(project)}<div class='project-grid'><div>${renderArtifacts(project)}${project.constraint ? `<p class='body-muted' style='margin-top:17px;font-size:14px'>${escapeHtml(project.constraint)}</p>` : ''}</div><div class='right-column'>${renderOpenItems(project)}${renderNotes()}</div></div><div class='source-row'><div>${source.url ? link(source.url, source.label || '查看项目来源', '', true) : ''}</div>${project.workspace ? `<details class='source-details'><summary>项目位置与现状</summary><code>${escapeHtml(project.workspace)}</code><p class='body-muted' style='margin-top:9px;font-size:14px'>${escapeHtml(project.summary)}</p></details>` : ''}</div>`;
  }

  function renderResources(items = state.data.resources || []) {
    return `<div class='resource-list'>${items.map((resource) => `<div class='resource-row'>${icon('file')}<div>${link(resource.url, resource.name, 'resource-name')}<p class='resource-detail'>${escapeHtml(resource.detail)}</p></div></div>`).join('')}</div>`;
  }

  function renderDocuments() {
    const documents = state.data.documents || [];
    return `<div class='document-list'>${documents.slice(0, 6).map((item) => `<div class='document-row'>${icon('file')}<div>${link(`/documents/${encodeURIComponent(item.id)}`, item.name, 'document-name')}</div></div>`).join('')}</div>${!localAvailable() ? `<p class='resource-detail'>本地文档在连接此 Mac 后可打开。</p>` : ''}`;
  }


  function renderHardwareStudio() {
    const hw = state.data.hardware;
    if (!hw) return '';
    const err = hw.error ? `<p class='body-muted'>校验器错误：${escapeHtml(hw.error)}</p>` : '';
    const line = (label, value, cls) => `<div class='status-row'><span class='status-row-label'>${escapeHtml(label)}</span><div class='status-value ${cls || ''}'>${escapeHtml(value)}</div></div>`;
    const lineRaw = (label, html, cls) => `<div class='status-row'><span class='status-row-label'>${escapeHtml(label)}</span><div class='status-value ${cls || ''}'>${html}</div></div>`;
    if (!hw.ok) {
      const fails = (hw.failures || []).map(f => `<li>${escapeHtml(f)}</li>`).join('');
      return `<section class='panel' aria-label='Hardware Studio'><div class='panel-heading'><h2>Hardware Studio · Space Buddy R1</h2><span class='badge hold'>校验失败/过期</span></div><div class='status-list'>${err}<ul class='open-items'>${fails}</ul></div></section>`;
    }
    const facts = hw.facts || {};
    const nine = (state.data.hardware_next || {});
    const quad = (facts.quad || {});
    const looks = nine.looks_like ? link(nine.looks_like, '五视图 + 可旋转模型', '', true) : '待输出';
    const cadLabel = facts.cad_evidence_state === 'valid'
      ? `有效（几何检查全绿）`
      : `${facts.cad_evidence_state === 'stale' ? '已过期' : '未知'}——${(facts.cad_evidence_diffs || []).join('；') || '缺回执'}`;
    const rows = [
      line('外观原型进展', nine.appearance_progress || '见项目记录'),
      lineRaw('产品长什么样', looks),
      line('当前几何检查', cadLabel, facts.cad_evidence_state === 'valid' ? 'good' : 'attention'),
      line('实物尺寸适配', facts.dims_confirmed ? '全部确认' : `待样品（未确认：${(facts.dims_unconfirmed || []).join('、')}）`, facts.dims_confirmed ? 'good' : 'attention'),
      line('板壳联合验证', facts.joint_status, checks_or('joint_verified', facts) ),
      line('制造准备与授权', facts.order_authorized ? '已授权' : '未授权（不付款不下单）', facts.order_authorized ? 'good' : 'attention'),
      line('制造包是否齐全', facts.package_complete ? '齐全' : `未齐全（缺：${(facts.package_missing || []).join('、')}）`, facts.package_complete ? 'good' : 'attention'),
      line('PCB 是否完成', facts.pcb_status, facts.pcb_frozen ? 'good' : 'attention'),
      line('当前阻断', (nine.blockers || []).join('；'), 'attention'),
      line('版本四元组', `R1.${quad.pcb || '未开始'}.${quad.cad}.${quad.fw}.${quad.bom}`),
      line('产品是否就绪', facts.product_ready ? '就绪' : '未就绪', facts.product_ready ? 'good' : 'attention'),
    ];
    const ownerRows = (nine.next_owner || []).map(o => `<li>${escapeHtml(o.who)}：${escapeHtml(o.what)}</li>`).join('');
    const needRows = (nine.needs_user || []).map(x => `<li>${escapeHtml(x)}</li>`).join('');
    const reasons = (facts.product_ready_reasons || []).map(x => `<li>${escapeHtml(x)}</li>`).join('');
    return `<section class='panel' aria-label='Hardware Studio'><div class='panel-heading'><h2>Hardware Studio · Space Buddy R1</h2><span class='badge ${facts.product_ready ? 'ready' : 'hold'}'>${facts.product_ready ? '产品就绪' : '产品未就绪'}</span></div><div class='status-list'>${rows.join('')}</div><div class='panel-body'><p class='note-storage'>未就绪原因（证据计算）</p><ul class='open-items'>${reasons}</ul><p class='note-storage'>下一步分工</p><ul class='open-items'>${ownerRows}</ul><p class='note-storage'>需要本人确认</p><ul class='open-items'>${needRows}</ul></div></section>`;
  }
  function checks_or(key, facts) {
    return facts[key] !== undefined ? String(facts[key]) : '未开始';
  }

  function renderOverview() {
    return `${previewNotice()}${renderHardwareStudio()}<div class='page-heading'><div><div class='eyebrow'><span class='eyebrow-line'></span>Maker Lab</div><h1>把想法做成可用的硬件</h1><p class='overview-intro'>${escapeHtml(state.data.objective)}</p></div></div><div class='section-heading'><h2>我的项目</h2><span class='section-caption'>${state.data.projects.length} 个项目 · 真实进度</span></div><div class='overview-list'>${state.data.projects.map((project) => `<button class='overview-row' type='button' data-project='${escapeHtml(project.id)}'><span class='project-symbol'>${icon(projectIcon(project.id))}</span><span><span class='overview-name'>${escapeHtml(project.name)}</span><span class='overview-tagline'>${escapeHtml(project.tagline)}</span></span><span class='overview-next'>${escapeHtml(project.next_step)}</span><span class='overview-status'><span class='badge ${project.stages?.some((stage) => stage.status === 'hold') ? 'hold' : 'neutral'}'>${escapeHtml(project.stage_label)}</span></span></button>`).join('')}</div><div class='overview-bottom'><section><div class='section-heading'><h2>工作区文档</h2></div>${renderDocuments()}</section><section><div class='section-heading'><h2>常用入口</h2></div>${renderResources((state.data.resources || []).filter((resource) => !resource.name.includes('自动化')).slice(0, 4))}</section></div>`;
  }

  function liveChecks() {
    if (!localAvailable()) return (state.data.environment?.checks || []).map((check) => ({ label: check.label, value: check.status === 'passed' ? '记录已验证' : '记录待完成', kind: check.status === 'passed' ? 'good' : 'attention', detail: check.detail }));
    const live = state.live;
    const bridge = live.bridge || {};
    const bridgeLabel = { connected: '已连接', disconnected: '未连接', unavailable: '暂不可用', error: '检查失败', timeout: '检查超时' }[bridge.state] || '待核验';
    return [
      { label: 'EDA 客户端', value: live.app_installed ? '已安装' : '未检测到', kind: live.app_installed ? 'good' : 'attention', detail: `工程工具版本 ${state.data.environment?.version || '待核实'}` },
      { label: '原生命令工具', value: live.cli_available ? '可用' : '未检测到', kind: live.cli_available ? 'good' : 'attention', detail: '用于打开、检查和导出实际工程。' },
      { label: '编辑器连接', value: bridgeLabel, kind: bridge.state === 'connected' ? 'good' : 'attention', detail: `${bridge.detail || ''}${bridge.detail ? ' ' : ''}连接状态不代表激活或设计已完成。` },
      { label: '官方激活', value: live.activation?.state === 'verified' ? `已激活（${(live.activation.accepted_at || '').slice(0, 10) || '已验收'}）` : live.activation?.state === 'pending' ? '待本人账号激活' : '待核验', kind: live.activation?.state === 'verified' ? 'good' : 'attention', detail: live.activation?.detail || '使用官网下载的免费激活文件。' },
      { label: '工程读写验证', value: live.editor_round_trip === 'passed' ? '已实测通过' : '待完成', kind: live.editor_round_trip === 'passed' ? 'good' : 'attention', detail: live.editor_round_trip === 'passed' ? `独立工程保存、关闭重开与标记读回已通过${live.editor_round_trip_evidence_at ? '（' + String(live.editor_round_trip_evidence_at).slice(0, 10) + '）' : ''}；当前以实时桥接状态为准。` : '尚不能将安装和连接成功视为工程已可使用。' }
    ];
  }

  function readinessSummary() {
    if (!localAvailable() || !state.live) return { ready: null, blockers: [], note: '连接本地工作台后显示实时就绪状态。' };
    const live = state.live;
    const conditions = [
      { ok: Boolean(live.app_installed), label: 'EDA 客户端已安装' },
      { ok: Boolean(live.cli_available), label: 'EDA 命令行可用' },
      { ok: live.bridge?.state === 'connected', label: '编辑器桥接已连接' },
      { ok: live.activation?.state === 'verified', label: '官方激活已验收' },
      { ok: live.editor_round_trip === 'passed', label: '工程读写往返已通过' },
    ];
    const blockers = conditions.filter((item) => !item.ok).map((item) => item.label);
    return { ready: blockers.length === 0, blockers,
             note: blockers.length ? `尚不能标记 EDA 可用：${blockers.join('、')}。` : '以上全部条件同时成立，可以开始实际设计。' };
  }

  function renderEnvironment() {
    const environment = state.data.environment || {};
    const live = localAvailable();
    const activationUrl = safeUrl(environment.activation_url);
    const activationVerified = live && state.live.activation?.state === 'verified';
    const isPending = !live || state.live.activation?.state === 'pending';
    const readiness = readinessSummary();
    const heading = live && !state.live.app_installed ? '当前未检测到 EDA 客户端' : readiness.ready ? 'EDA 工具链可用，可以开始设计' : isPending ? '工具已装好，编辑器还需官方激活' : 'Mac 已连接，继续核实编辑器状态';
    const readinessBadge = readiness.ready === null ? '' : readiness.ready
      ? `<span class='badge ready'><span class='status-dot connected'></span>EDA 可用</span>`
      : `<span class='badge hold'><span class='status-dot attention'></span>待处理 ${readiness.blockers.length} 项</span>`;
    return `<div class='page-heading'><div><div class='eyebrow'><span class='eyebrow-line'></span>本机工具</div><h1>运行环境</h1><p class='project-subtitle'>查看安装记录与实时状态，完成开始设计前的一步。</p></div><div class='page-heading-actions'><button type='button' class='button' data-refresh-status ${state.connection === 'checking' ? 'disabled' : ''}>${icon('refresh')}${state.connection === 'checking' ? '检查中…' : '刷新环境'}</button></div></div>${previewNotice()}<div class='environment-summary'><div><h2>${heading}</h2><p>${live ? `${escapeHtml(readiness.note)} 激活与工程读写是不同验收项，分别记录。` : '以下安装情况来自工作区记录，并非当前 Mac 的实时核验。连接本地工作台后可以刷新检查。'}</p></div>${readinessBadge}</div><div class='environment-grid'><div><section class='panel'><div class='panel-heading'><h2>${live ? 'Mac 实时检查' : '已保存的安装记录'}</h2><span class='badge ${live ? 'ready' : 'neutral'}'>${live ? '本地服务' : '资料预览'}</span></div><div class='status-list'>${liveChecks().map((check) => `<div class='status-row'><span class='status-row-label'>${escapeHtml(check.label)}</span><div><div class='status-value ${check.kind}'>${escapeHtml(check.value)}</div><p class='status-row-detail'>${escapeHtml(check.detail)}</p></div></div>`).join('')}</div><div class='environment-check-time'>${live ? `最近检查：${formatTime(state.live.checked_at, true) || '刚刚'}` : `资料日期：${escapeHtml(environment.checked_at || state.data.updated_at || '待核实')}`}${state.statusError && !live ? ` · ${escapeHtml(state.statusError)}` : ''}</div></section><section class='activation-box'><details ${activationVerified ? 'open' : ''}><summary>${activationVerified ? `官方激活已完成（${escapeHtml((state.live?.activation?.accepted_at || '').slice(0, 10))}）· 展开查看激活说明存档` : '人在外面，也可以先取得激活文件'}</summary><h3>取得并导入官方激活文件</h3><ol class='activation-steps'><li>打开官方页面，登录你本人的嘉立创账号。</li><li>下载免费的客户端激活文件，并妥善保存。</li><li>下载后把原始 .txt 文件发到当前对话，由已授权的本地 Agent 导入，不必等回到 Mac。</li></ol>${activationUrl ? `<a class='button button-dark' href='${escapeHtml(activationUrl)}' target='_blank' rel='noopener noreferrer'>打开官方激活页</a>` : ''}<p class='helper'>激活文件包含账户信息，请勿放入公开仓库或公开备注。下载文件不等于此 Mac 已完成激活；激活验收以客户端界面与编辑器读写往返记录为准。</p><div style='margin-top:10px'>${link('/documents/activation-guide', '查看详细操作说明', 'button button-quiet', true)}</div></details></section></div><div class='environment-side'><section class='panel'><div class='panel-heading'><h2>已接入的技能</h2></div><div class='panel-body'>${(environment.skills || []).map((skill) => {
      const observed = (state.live?.skills || []).find((item) => item.id === skill.id);
      const label = live && observed ? observed.installed ? '已检测到' : '未检测到' : '安装记录';
      return `<div class='skill-item'><div class='skill-name'><span>${escapeHtml(skill.name)}</span><span class='badge ${live && observed?.installed ? 'ready' : 'neutral'}'>${label}</span></div><p class='skill-detail'>${escapeHtml(skill.detail)}</p></div>`;
    }).join('')}</div></section><section class='environment-resources'><h2>官方文档与工具</h2>${renderResources((state.data.resources || []).filter((resource) => !resource.name.includes('免费激活')))}</section></div></div>`;
  }

  function render() {
    if (!state.data) return;
    renderShell();
    const project = currentProject();
    $('#main').innerHTML = state.view === 'overview' ? renderOverview() : state.view === 'environment' ? renderEnvironment() : state.view === 'files' && project ? `${previewNotice()}${projectHeading(project, true)}${renderArtifacts(project, true)}<div class='source-row'><button class='button button-quiet' data-project='${escapeHtml(project.id)}' type='button'>返回项目概况</button></div>` : renderProject();
    if (state.view === 'project') updateNoteStatus();
  }

  function closeMenu() {
    $('#sidebar').classList.remove('open');
    $('#sidebar-scrim').hidden = true;
    $('#menu-toggle').setAttribute('aria-expanded', 'false');
    $('#menu-toggle').setAttribute('aria-label', '打开导航');
  }

  function navigate(view, projectId) {
    if (projectId && state.data.projects.some((project) => project.id === projectId)) state.projectId = projectId;
    state.view = ['project', 'overview', 'files', 'environment'].includes(view) ? view : 'project';
    state.filter = '全部';
    const hash = state.view === 'project' || state.view === 'files' ? `#${state.view}/${encodeURIComponent(state.projectId)}` : `#${state.view}`;
    if (window.location.hash !== hash) window.history.pushState(null, '', hash);
    closeMenu();
    render();
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  function applyRoute() {
    if (!state.data) return;
    const parts = window.location.hash.slice(1).split('/');
    const view = ['project', 'overview', 'files', 'environment'].includes(parts[0]) ? parts[0] : 'project';
    let id;
    try { id = decodeURIComponent(parts[1] || ''); } catch { id = ''; }
    if (state.data.projects.some((project) => project.id === id)) state.projectId = id;
    if (!state.data.projects.some((project) => project.id === state.projectId)) state.projectId = state.data.projects[0]?.id || '';
    state.view = view;
    state.filter = '全部';
    closeMenu();
    render();
  }

  function loadBrowserNotes() {
    try {
      const stored = JSON.parse(window.localStorage.getItem(noteKey) || '{"notes":{}}');
      const notes = stored?.notes && typeof stored.notes === 'object' ? stored.notes : {};
      for (const [id, item] of Object.entries(notes)) {
        if (typeof item?.text !== 'string') continue;
        state.notes.local[id] = { ...blankNote(), text: item.text, savedText: item.text, updatedAt: item.updated_at || '' };
      }
    } catch { state.localStorageError = '这个浏览器未能读取本地备注。请保留草稿，确认浏览器允许本地存储后重试。'; }
  }

  async function loadRemoteNotes() {
    try {
      const data = await requestJson('/api/notes');
      if (!data.notes || typeof data.notes !== 'object' || Array.isArray(data.notes)) throw new Error('备注响应格式不正确');
      for (const project of state.data.projects) {
        const old = getNote('server', project.id);
        if (old.text !== old.savedText || old.saving) continue;
        const item = data.notes[project.id];
        const text = typeof item?.text === 'string' ? item.text : '';
        state.notes.server[project.id] = { ...blankNote(), text, savedText: text, updatedAt: item?.updated_at || '' };
      }
      state.remoteNotesLoaded = true;
      state.remoteNotesError = '';
      if (state.noteMode === null) state.noteMode = 'server';
    } catch (error) {
      state.remoteNotesError = error.message;
      if (state.noteMode === null) state.noteMode = 'local';
    }
  }

  async function refreshStatus() {
    const generation = ++state.statusGeneration;
    state.connection = 'checking';
    render();
    try {
      const data = await requestJson('/api/status', {}, 10000);
      if (generation !== state.statusGeneration) return;
      if (data.mode !== 'local' || typeof data.app_installed !== 'boolean') throw new Error('当前页面未连接本机工作台服务');
      state.live = data;
      state.connection = 'connected';
      state.statusError = '';
      await loadRemoteNotes();
      if (generation !== state.statusGeneration) return;
    } catch (error) {
      if (generation !== state.statusGeneration) return;
      state.live = null;
      state.connection = 'preview';
      state.statusError = error.message;
      if (state.noteMode === null) state.noteMode = 'local';
    }
    render();
  }

  function updateNoteStatus() {
    const status = $('#note-save-status');
    if (!status) return;
    const note = getNote();
    const server = state.noteMode === 'server';
    let message = '';
    let kind = '';
    if (state.noteMode === null) message = '正在读取备注…';
    else if (note.error) { message = note.error; kind = 'error'; }
    else if (note.saving) message = '保存并核对中…';
    else if (note.text !== note.savedText) message = '有未保存的修改';
    else if (note.updatedAt) { message = `${server ? 'Mac' : '此浏览器'}已保存 · ${formatTime(note.updatedAt)}`; kind = 'success'; }
    else if (server && !localAvailable()) message = '未连接 Mac，草稿仍保留在当前页面';
    else if (!server && state.localStorageError) { message = state.localStorageError; kind = 'error'; }
    else if (!server && state.remoteNotesError) message = 'Mac 备注暂不可读，当前使用浏览器备注';
    else message = server ? '输入后保存到 Mac' : '输入后保存到此浏览器';
    status.textContent = message;
    status.className = `note-save-status ${kind}`;
    const button = $('#save-note');
    if (button) {
      button.disabled = state.noteMode === null || note.saving || (server && !localAvailable()) || note.text.length > 8000;
      button.textContent = note.saving ? '保存中…' : server ? '保存备注' : '保存到浏览器';
    }
    if ($('#note-counter')) $('#note-counter').textContent = `${note.text.length} / 8000`;
  }

  async function saveNote() {
    const mode = state.noteMode || 'local';
    const id = state.projectId;
    const note = getNote(mode, id);
    if (note.saving || note.text.length > 8000 || (mode === 'server' && !localAvailable())) return;
    const text = note.text;
    note.saving = true;
    note.error = '';
    updateNoteStatus();
    try {
      let saved;
      if (mode === 'server') {
        await requestJson('/api/notes', postOptions({ project_id: id, text }));
        const verified = await requestJson('/api/notes');
        saved = verified.notes?.[id];
        if (!saved || saved.text !== text) throw new Error('保存后回读不一致，尚不能确认已保存；草稿仍在。');
      } else {
        const raw = JSON.parse(window.localStorage.getItem(noteKey) || '{"notes":{}}');
        const existing = raw?.notes && typeof raw.notes === 'object' && !Array.isArray(raw.notes) ? raw.notes : {};
        const value = { text, updated_at: new Date().toISOString() };
        window.localStorage.setItem(noteKey, JSON.stringify({ notes: { ...existing, [id]: value } }));
        const verified = JSON.parse(window.localStorage.getItem(noteKey) || '{}');
        saved = verified.notes?.[id];
        if (!saved || saved.text !== text) throw new Error('浏览器保存后回读不一致；草稿仍在。');
        state.localStorageError = '';
      }
      note.savedText = text;
      note.updatedAt = saved.updated_at || new Date().toISOString();
      note.status = 'saved';
    } catch (error) {
      note.error = mode === 'local' && !error.message.includes('回读') ? '浏览器未能保存。草稿仍在，请复制保留后重试。' : error.message;
    } finally {
      note.saving = false;
      updateNoteStatus();
    }
  }

  function toast(message, error = false) {
    window.clearTimeout(state.toastTimer);
    $('#toast-region').innerHTML = `<div class='toast ${error ? 'error' : ''}'>${escapeHtml(message)}</div>`;
    state.toastTimer = window.setTimeout(() => { $('#toast-region').innerHTML = ''; }, error ? 7000 : 4500);
  }

  async function runAction(action) {
    if (!['open_eda', 'open_project'].includes(action) || state.actionBusy || !localAvailable()) return;
    if (action === 'open_eda' && !state.live.app_installed) return;
    const id = state.projectId;
    if (action === 'open_project' && !currentProject()?.workspace) return;
    state.actionBusy = action;
    render();
    try {
      const body = action === 'open_project' ? { action, project_id: id } : { action };
      const result = await requestJson('/api/actions', postOptions(body));
      if (result.ok !== true) throw new Error(result.error?.message || '本机没有确认打开请求');
      toast(action === 'open_eda' ? '已请求在 Mac 打开嘉立创 EDA。编辑器激活状态请以实际界面为准。' : '已请求在 Mac 打开项目目录。');
    } catch (error) { toast(error.message, true); }
    finally { state.actionBusy = ''; render(); }
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button || button.disabled || !state.data && !button.hasAttribute('data-retry-load')) return;
    if (button.dataset.view) navigate(button.dataset.view);
    else if (button.dataset.project) navigate('project', button.dataset.project);
    else if (button.dataset.filter) { state.filter = button.dataset.filter; render(); }
    else if (button.dataset.action) runAction(button.dataset.action);
    else if (button.hasAttribute('data-refresh-status')) refreshStatus();
    else if (button.hasAttribute('data-save-note')) saveNote();
    else if (button.dataset.noteMode && ['server', 'local'].includes(button.dataset.noteMode)) {
      if (button.dataset.noteMode === 'server' && !state.remoteNotesLoaded) return;
      state.noteMode = button.dataset.noteMode;
      render();
    } else if (button.hasAttribute('data-retry-load')) start();
  });

  document.addEventListener('input', (event) => {
    if (event.target.id !== 'project-note') return;
    const note = getNote();
    note.text = event.target.value;
    note.error = '';
    updateNoteStatus();
  });
  $('#menu-toggle').addEventListener('click', () => {
    const open = !$('#sidebar').classList.contains('open');
    $('#sidebar').classList.toggle('open', open);
    $('#sidebar-scrim').hidden = !open;
    $('#menu-toggle').setAttribute('aria-expanded', String(open));
    $('#menu-toggle').setAttribute('aria-label', open ? '关闭导航' : '打开导航');
  });
  $('#sidebar-scrim').addEventListener('click', closeMenu);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeMenu(); });
  window.addEventListener('popstate', applyRoute);
  window.addEventListener('hashchange', applyRoute);
  window.addEventListener('beforeunload', (event) => {
    if (Object.values(state.notes).some((notes) => Object.values(notes).some((note) => note.text !== note.savedText || note.saving))) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  async function start() {
    try {
      const data = await requestJson('./workbench.json');
      if (!Array.isArray(data.projects)) throw new Error('工作台数据缺少项目列表');
      state.data = data;
      loadBrowserNotes();
      applyRoute();
      refreshStatus();
    } catch (error) {
      $('#main').innerHTML = `<div class='initial-state'>${icon('info')}<h1>暂时无法读取项目资料</h1><p>请从工作台服务地址打开此页面，并确认工作台数据文件已准备好。</p><p class='error-detail'>${escapeHtml(error.message)}</p><button type='button' class='button button-dark' data-retry-load>重新读取</button></div>`;
      $('#workspace-updated').textContent = '资料尚未载入';
      $('#connection-indicator').innerHTML = `<span class='status-dot'></span><span>项目资料不可用</span>`;
    }
  }

  start();
})();
