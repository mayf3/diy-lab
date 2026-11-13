/* Maker Lab interactions. No analytics, account, network request, or backend. */
(() => {
  'use strict';
  const prefix = 'makerlab:v1:';
  const body = document.body;
  const project = body.dataset.project || '';
  function read(key) { try { return window.localStorage.getItem(prefix + key); } catch { return null; } }
  function write(key, value) { try { window.localStorage.setItem(prefix + key, String(value)); } catch { /* storage may be blocked */ } }
  function keyOfChapter(chapter) { return 'chapter:' + chapter; }

  // 个人进度：只接管带 data-personal-key 的清单（步骤页的"我的验收"）。
  // 作者事实（✅/◻ 徽章）是内容源渲染的只读记录，这里一律不碰。
  const personal = Array.from(document.querySelectorAll('.doc-content input[data-personal-key]'));

  // 旧版按"页内顺序"编号的记录无法可靠对应到当前内容：停用、清除并告知，绝不静默套用到新条目。
  (function retireLegacy() {
    if (!personal.length) return;
    let stale = 0;
    try {
      const doomed = [];
      for (let i = 0; i < window.localStorage.length; i++) {
        const k = window.localStorage.key(i);
        if (k && k.startsWith(prefix + 'check:')) doomed.push(k);
      }
      stale = doomed.length;
      doomed.forEach(k => window.localStorage.removeItem(k));
    } catch { return; }
    if (stale) {
      const doc = document.querySelector('.doc-content');
      if (doc) {
        const note = document.createElement('div');
        note.className = 'legacy-progress-note';
        note.textContent = '检测到旧版个人勾选记录（旧格式按页内顺序编号，无法可靠对应到当前内容），已停用并清除；请重新确认你的勾选。页面里的作者记录不受影响。';
        doc.prepend(note);
      }
    }
  })();

  personal.forEach(input => {
    const storageKey = 'personal:' + input.dataset.personalKey;
    input.disabled = false;
    input.checked = read(storageKey) === 'true';
    const label = input.closest('li');
    if (label) label.classList.toggle('is-checked', input.checked);
    input.addEventListener('change', () => {
      write(storageKey, input.checked);   // 显式记录取消与恢复
      if (label) label.classList.toggle('is-checked', input.checked);
      updateCompleteButton();
    });
  });

  function updateProgress() {
    document.querySelectorAll('[data-progress-project]').forEach(box => {
      const id = box.dataset.progressProject;
      const total = Number(box.dataset.progressTotal || 0);
      if (!total) return;
      let done = 0;
      document.querySelectorAll('[data-nav-step]').forEach(nav => {
        const key = nav.dataset.navStep;
        const isDone = read(keyOfChapter(key)) === 'true';
        nav.classList.toggle('is-complete', isDone);
      });
      const steps = window.MAKER_PROJECT_STEPS?.[id] || [];
      steps.forEach(stepid => { if (read(keyOfChapter(id + ':' + stepid)) === 'true') done += 1; });
      const count = box.querySelector('.progress-count');
      const fill = box.querySelector('.progress-fill');
      if (count) count.textContent = `${done}/${total}`;
      if (fill) fill.style.width = `${Math.round(100 * done / total)}%`;
    });
  }

  const complete = document.querySelector('[data-chapter]');
  const doneButton = complete?.querySelector('button');
  function updateCompleteButton() {
    if (!complete || !doneButton) return;
    const id = complete.dataset.chapter;
    const isDone = read(keyOfChapter(id)) === 'true';
    const allChecked = personal.every(item => item.checked);
    doneButton.textContent = isDone ? '重新打开本章' : '标记本章已完成';
    doneButton.classList.toggle('is-done', isDone);
    doneButton.disabled = !isDone && !allChecked;
    complete.classList.toggle('is-done', isDone);
  }
  if (doneButton) {
    doneButton.addEventListener('click', () => {
      const id = complete.dataset.chapter;
      write(keyOfChapter(id), read(keyOfChapter(id)) === 'true' ? 'false' : 'true');
      updateCompleteButton();
      updateProgress();
    });
  }
  updateCompleteButton();
  updateProgress();

  // The mobile navigation is a toggle, not an external page/modal.
  const menu = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('mobileOverlay');
  function setMenu(open) {
    if (!sidebar || !overlay || !menu) return;
    sidebar.classList.toggle('open', open);
    overlay.hidden = !open;
    menu.setAttribute('aria-expanded', String(open));
    body.classList.toggle('menu-is-open', open);
  }
  menu?.addEventListener('click', () => setMenu(!sidebar.classList.contains('open')));
  overlay?.addEventListener('click', () => setMenu(false));
  sidebar?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));

  const dialog = document.getElementById('searchModal');
  const searchInput = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');
  const openButton = document.getElementById('searchOpen');
  const closeButton = document.getElementById('searchClose');
  const root = body.dataset.root || './';
  function setSearch(open) {
    if (!dialog) return;
    dialog.hidden = !open;
    body.classList.toggle('search-is-open', open);
    if (open) { setMenu(false); searchInput?.focus(); } else openButton?.focus();
  }
  function renderResults(query) {
    if (!searchResults) return;
    const term = query.trim().toLocaleLowerCase();
    searchResults.replaceChildren();
    if (!term) { const p = document.createElement('p'); p.textContent = '输入关键词，搜索全站教程。'; searchResults.append(p); return; }
    const entries = window.MAKER_SEARCH_INDEX || [];
    const found = entries.filter(item => (`${item.title} ${item.summary}`).toLocaleLowerCase().includes(term)).slice(0, 16);
    if (!found.length) { const p = document.createElement('p'); p.textContent = '没有匹配内容。可以试试「排线」「打印」「烧录」「万圣节」。'; searchResults.append(p); return; }
    for (const item of found) {
      const a = document.createElement('a');
      a.href = root + item.path;
      const strong = document.createElement('strong'); strong.textContent = item.title;
      const sub = document.createElement('small'); sub.textContent = item.summary;
      a.append(strong, sub); searchResults.append(a);
    }
  }
  openButton?.addEventListener('click', () => setSearch(true));
  closeButton?.addEventListener('click', () => setSearch(false));
  dialog?.addEventListener('click', (e) => { if (e.target === dialog) setSearch(false); });
  searchInput?.addEventListener('input', e => renderResults(e.target.value));
  document.addEventListener('keydown', event => {
    if ((event.key === '/' || (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey))) && !dialog?.hidden) return;
    if ((event.key === '/' || (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey))) && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
      event.preventDefault(); setSearch(true);
    }
    if (event.key === 'Escape') { if (dialog && !dialog.hidden) setSearch(false); else setMenu(false); }
  });
})();
// Embed video only on user interaction; don't load third-party player by default.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.video-embed[data-bvid]').forEach(holder => {
    holder.querySelector('.load-video')?.addEventListener('click', () => {
      const bvid = holder.dataset.bvid;
      if (!/^BV[a-zA-Z0-9]+$/.test(bvid)) return;
      const frame = document.createElement('iframe');
      frame.src = 'https://player.bilibili.com/player.html?bvid=' + encodeURIComponent(bvid);
      frame.loading = 'lazy'; frame.allow = 'fullscreen'; frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.title = 'B 站 DIY 教程视频'; holder.replaceChildren(frame);
    });
  });
});
