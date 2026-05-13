let currentPage = 'home';
let msLoginInterval = null;

function initApp() {
  initSidebar();
  initTabs();
  loadVersions();
  refreshHome();
  refreshAccount();
  initSettings();
  initModsPage();
}

if (window.pywebview) {
  initApp();
} else {
  window.addEventListener('pywebviewready', initApp);
}

/* Navigation */
function initSidebar() {
  document.querySelectorAll('.nav-btn[data-page]').forEach(btn => {
    btn.addEventListener('click', () => navigate(btn.dataset.page));
  });
}

function navigate(page) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.nav-btn[data-page="${page}"]`)?.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${page}`)?.classList.add('active');
  currentPage = page;
  if (page === 'account') refreshAccount();
  if (page === 'mods') refreshInstalled();
}

/* Generic Tabs */
function initTabs() {
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.closest('.page').id, btn));
  });
}

function switchTab(pageId, btn) {
  const container = btn.closest('.page') || document.getElementById(pageId);
  container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const tabId = btn.dataset.tab;
  container.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  const target = container.querySelector(`#${pageId.replace('page-', '')}-${tabId}`)
    || document.getElementById(`${tabId}`);
  if (target) target.classList.add('active');
}

/* Home */
async function loadVersions() {
  try {
    const versions = await pywebview.api.get_versions();
    const selects = document.querySelectorAll('#version-select, #mod-version');
    selects.forEach(sel => {
      sel.innerHTML = versions.map(v => `<option value="${v}">${v}</option>`).join('');
    });
    const settings = await pywebview.api.get_settings();
    selects.forEach(sel => sel.value = settings.version);
  } catch (e) { console.error(e); }
}

async function refreshHome() {
  try {
    const user = await pywebview.api.get_current_user();
    document.getElementById('user-badge').textContent = user ? `👤 ${user.slice(0, 15)}` : '👤 Account';
  } catch (e) { console.error(e); }
}

document.getElementById('play-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('play-btn');
  btn.textContent = '⏳ Launching...';
  btn.disabled = true;
  try {
    const sel = document.getElementById('version-select');
    await pywebview.api.save_settings(JSON.stringify({ version: sel.value }));
    await pywebview.api.launch();
  } catch (e) { console.error(e); }
  btn.textContent = '▶  PLAY';
  btn.disabled = false;
});

document.getElementById('version-select')?.addEventListener('change', async (e) => {
  await pywebview.api.save_settings(JSON.stringify({ version: e.target.value }));
});

/* Account */
async function refreshAccount() {
  const container = document.getElementById('account-content');
  try {
    const auth = await pywebview.api.get_auth();
    const offlineUser = await pywebview.api.get_offline_username();
    const hasOffline = await pywebview.api.has_offline_account();

    if (auth && auth.username) {
      container.innerHTML = `
        <div class="account-card">
          <h3>✓ Premium Account</h3>
          <p>User: ${auth.username}</p>
          <p class="label">UUID: ${auth.uuid || 'N/A'}</p>
          <button class="btn-danger" onclick="logoutAccount()">Logout</button>
        </div>`;
    } else {
      container.innerHTML = `
        <div class="account-card">
          <h3>${hasOffline ? '✓ Offline Mode' : 'Offline / Microsoft'}</h3>
          ${hasOffline ? `<p>Playing as: <strong>${offlineUser}</strong></p>` : '<p>No offline profile configured.</p>'}
          <label class="label">Username</label>
          <input type="text" id="offline-input" placeholder="Enter a nickname" value="${offlineUser || ''}" />
          <div class="btn-row">
            <button class="btn-primary" onclick="saveOffline()">Save Offline</button>
            <button class="btn-danger" onclick="deleteOffline()">Delete</button>
          </div>
        </div>
        <div class="account-card">
          <h3>Microsoft Login</h3>
          <p>Sign in with your Microsoft account for premium features.</p>
          <div id="ms-login-area"></div>
          <button class="btn-primary" onclick="startMsLogin()">Sign in with Microsoft</button>
        </div>`;
    }
  } catch (e) { console.error(e); }
}

async function saveOffline() {
  const name = document.getElementById('offline-input').value.trim();
  if (!name) return;
  await pywebview.api.login_offline(name);
  showMsg('account-content', `Logged in as ${name}`, 'success');
  refreshHome();
}

async function deleteOffline() {
  await pywebview.api.logout();
  refreshAccount();
  refreshHome();
}

async function logoutAccount() {
  await pywebview.api.logout();
  refreshAccount();
  refreshHome();
}

let msLoginData = null;
async function startMsLogin() {
  try {
    const di = await pywebview.api.start_microsoft_login();
    if (di.error) { showMsg('account-content', di.error, 'error'); return; }
    msLoginData = di;
    const area = document.getElementById('ms-login-area');
    area.innerHTML = `<div class="msg info">
      Open the browser and enter code: <strong style="font-size:24px">${di.user_code}</strong>
    </div>`;
    pollMsLogin();
  } catch (e) { showMsg('account-content', String(e), 'error'); }
}

async function pollMsLogin() {
  if (msLoginInterval) clearInterval(msLoginInterval);
  msLoginInterval = setInterval(async () => {
    try {
      const result = await pywebview.api.poll_microsoft_login(msLoginData.device_code);
      if (result.status === 'success') {
        clearInterval(msLoginInterval);
        msLoginInterval = null;
        showMsg('account-content', `Logged in as ${result.username}`, 'success');
        refreshAccount();
        refreshHome();
      } else if (result.error) {
        clearInterval(msLoginInterval);
        msLoginInterval = null;
        showMsg('account-content', result.error, 'error');
      }
    } catch (e) { console.error(e); }
  }, (msLoginData.interval || 5) * 1000);
}

/* Mods */
let currentCategory = 'mod';

function initModsPage() {
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.cat;
      document.getElementById('mod-search').value = '';
      refreshBrowse();
      refreshInstalled();
    });
  });
  document.getElementById('mod-search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const tabs = document.querySelectorAll('#page-mods .tab-btn');
      const activeTab = document.querySelector('#page-mods .tab-btn.active');
      const q = document.getElementById('mod-search').value.trim();
      if (activeTab?.dataset.tab === 'installed') {
        filterInstalled(q);
      } else {
        refreshBrowse(q || undefined);
      }
    }
  });
  refreshBrowse();
}

async function refreshBrowse(query, version, source) {
  const container = document.getElementById('mods-browse');
  container.innerHTML = '<div class="loading">Loading...</div>';
  const selVersion = document.getElementById('mod-version');
  const selSource = document.getElementById('mod-source');
  const selSort = document.getElementById('mod-sort');
  const v = version || (selVersion ? selVersion.value : '1.21.1');
  const s = source || (selSource ? selSource.value : 'modrinth');
  const pt = currentCategory;
  try {
    let data;
    if (query) data = await pywebview.api.search_mods(query, v, s, pt);
    else data = await pywebview.api.get_trending_mods(pt);
    const mods = data.mods || [];
    if (mods.length === 0) { container.innerHTML = '<div class="loading">No results found.</div>'; return; }
    const installed = await pywebview.api.get_installed_mods(pt);
    const installedIds = new Set(installed.mods.filter(m => m.mod_id).map(m => m.mod_id));
    container.innerHTML = mods.map(m => `
      <div class="mod-card">
        <div class="mod-icon">
          ${m.thumbnail ? `<img src="${m.thumbnail}" alt="" />` : '📦'}
        </div>
        <div class="mod-info">
          <div class="name" style="cursor:pointer" onclick="showModDetail('${m.mod_id}')">${m.name}</div>
          <div class="desc">${(m.description || '').slice(0, 100)}${m.description?.length > 100 ? '...' : ''}</div>
          <div class="meta">v${m.version || 'N/A'} · ${(m.downloads || 0).toLocaleString()} downloads · ${(m.project_type||'mod')}</div>
        </div>
        ${installedIds.has(m.mod_id)
          ? `<button class="btn-sm installed" disabled>✓ Installed</button>`
          : `<button class="btn-sm install" onclick="installMod('${m.mod_id}','${v}','${s}','${pt}','${m.thumbnail || ''}',this)">Download</button>`
        }
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div class="loading">Error: ${e}</div>`;
  }
}

async function refreshInstalled() {
  const container = document.getElementById('mods-installed');
  try {
    const data = await pywebview.api.get_installed_mods(currentCategory);
    const mods = data.mods || [];
    container.dataset.all = JSON.stringify(mods);
    renderInstalled(mods);
  } catch (e) {
    container.innerHTML = `<div class="loading">Error: ${e}</div>`;
  }
}

function renderInstalled(mods) {
  const container = document.getElementById('mods-installed');
  const label = {mod:'Mods',modpack:'Modpacks',resourcepack:'Resource Packs',shader:'Shaders'}[currentCategory] || 'Items';
  if (mods.length === 0) {
    container.innerHTML = `<div class="loading">No ${label.toLowerCase()} installed.</div>`;
    return;
  }
  container.innerHTML = mods.map(m => `
    <div class="mod-card">
      <div class="mod-icon">
        ${m.thumbnail ? `<img src="${m.thumbnail}" alt="" />` : '📦'}
      </div>
      <div class="mod-info">
        <div class="name" style="cursor:pointer" onclick="showModDetail('${m.mod_id}')">${m.name}</div>
        <div class="meta">${(m.size / (1024*1024)).toFixed(2)} MB${m.project_type ? ' · '+m.project_type : ''}</div>
      </div>
      <button class="btn-sm delete" onclick="deleteMod('${m.filename}',this)">Delete</button>
    </div>
  `).join('');
}

function filterInstalled(query) {
  const container = document.getElementById('mods-installed');
  try {
    const all = JSON.parse(container.dataset.all || '[]');
    if (!query) { renderInstalled(all); return; }
    const q = query.toLowerCase();
    renderInstalled(all.filter(m => m.name.toLowerCase().includes(q)));
  } catch (e) { /* ignore */ }
}

async function installMod(modId, version, source, projectType, thumbnail, btn) {
  btn.textContent = 'Downloading...';
  btn.disabled = true;
  try {
    await pywebview.api.download_mod(modId, version, source, projectType || currentCategory, thumbnail || '');
    refreshBrowse();
  } catch (e) {
    btn.textContent = 'Error';
  }
}

async function deleteMod(filename, btn) {
  btn.textContent = 'Deleting...';
  btn.disabled = true;
  try {
    await pywebview.api.delete_mod(filename);
    refreshInstalled();
  } catch (e) { btn.textContent = 'Error'; }
}

document.getElementById('mod-search-btn')?.addEventListener('click', () => {
  const q = document.getElementById('mod-search').value.trim();
  refreshBrowse(q || undefined);
});

document.querySelectorAll('.mods-tabs .tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mods-tabs .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('#page-mods .tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(`mods-${btn.dataset.tab}`).classList.add('active');
    if (btn.dataset.tab === 'installed') refreshInstalled();
  });
});

/* Settings */
async function initSettings() {
  try {
    const settings = await pywebview.api.get_settings();
    const theme = settings.theme || 'dark';
    if (theme !== 'dark') document.body.classList.add(`theme-${theme}`);
    document.querySelectorAll('.theme-option').forEach(el => {
      el.classList.toggle('active', el.dataset.theme === theme);
      el.addEventListener('click', () => setTheme(el.dataset.theme));
    });
    const cr = settings.corner_radius || 12;
    document.documentElement.style.setProperty('--radius', cr + 'px');
    document.getElementById('corner-slider').value = cr;
    document.getElementById('corner-value').textContent = cr + 'px';
    document.getElementById('corner-slider').addEventListener('input', (e) => {
      const val = e.target.value + 'px';
      document.documentElement.style.setProperty('--radius', val);
      document.getElementById('corner-value').textContent = val;
      pywebview.api.save_settings(JSON.stringify({ corner_radius: parseInt(e.target.value) }));
    });
    document.getElementById('smooth-rendering').checked = !!settings.smooth_rendering;
    document.getElementById('smooth-rendering').addEventListener('change', (e) => {
      pywebview.api.save_settings(JSON.stringify({ smooth_rendering: e.target.checked }));
    });
    document.getElementById('ram-slider').value = settings.ram || 4;
    document.getElementById('ram-value').textContent = (settings.ram || 4) + ' GB';
    document.getElementById('ram-slider').addEventListener('input', (e) => {
      document.getElementById('ram-value').textContent = e.target.value + ' GB';
      pywebview.api.save_settings(JSON.stringify({ ram: parseInt(e.target.value) }));
    });
    document.getElementById('java-path').value = settings.java_path || 'java';
    document.getElementById('mc-dir').value = settings.minecraft_dir || '~/.stellaclient';
    document.getElementById('discord-rpc').checked = settings.discord_rpc !== false;
    document.getElementById('discord-rpc').addEventListener('change', (e) => {
      pywebview.api.save_settings(JSON.stringify({ discord_rpc: e.target.checked }));
    });
  } catch (e) { console.error(e); }
}

document.getElementById('save-java-btn')?.addEventListener('click', async () => {
  try {
    await pywebview.api.save_settings(JSON.stringify({
      java_path: document.getElementById('java-path').value,
      minecraft_dir: document.getElementById('mc-dir').value,
    }));
    showMsg('settings-runtime', 'Saved!', 'success');
  } catch (e) { showMsg('settings-runtime', String(e), 'error'); }
});

document.querySelectorAll('.settings-tabs .tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.settings-tabs .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('#page-settings .tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(`settings-${btn.dataset.tab}`).classList.add('active');
  });
});

async function setTheme(name) {
  document.body.classList.remove('theme-light', 'theme-oled');
  if (name !== 'dark') document.body.classList.add(`theme-${name}`);
  document.querySelectorAll('.theme-option').forEach(el => el.classList.remove('active'));
  document.querySelector(`.theme-option[data-theme="${name}"]`).classList.add('active');
  await pywebview.api.save_settings(JSON.stringify({ theme: name.toLowerCase() }));
}

/* Mod Detail */
async function showModDetail(modId) {
  const overlay = document.getElementById('mod-detail-overlay');
  const body = document.getElementById('mod-detail-body');
  body.innerHTML = '<div class="loading">Loading...</div>';
  overlay.classList.add('open');

  try {
    const d = await pywebview.api.get_mod_detail(modId);
    if (d.error) { body.innerHTML = `<div class="loading">Error: ${d.error}</div>`; return; }

    const installed = await pywebview.api.get_installed_mods();
    const isInstalled = installed.mods.some(m => m.mod_id === modId);
    const hasLinks = d.discord_url || d.issues_url || d.source_url || d.wiki_url || d.donation_urls?.length;
    const fmtDate = (s) => s ? new Date(s).toLocaleDateString() : 'N/A';

    body.innerHTML = `
      <div class="mod-detail-header">
        <div class="mod-detail-icon">
          ${d.thumbnail ? `<img src="${d.thumbnail}" alt="" />` : '📦'}
        </div>
        <div class="mod-detail-info">
          <h2>${d.name}</h2>
          <div class="stats">
            <span>Downloads: <strong>${(d.downloads || 0).toLocaleString()}</strong></span>
            <span>Followers: <strong>${(d.followers || 0).toLocaleString()}</strong></span>
          </div>
          ${d.license ? `<div class="stats"><span>License: <strong>${d.license}</strong></span></div>` : ''}
          ${d.loaders?.length ? `<div class="stats"><span>Loaders: <strong>${d.loaders.join(', ')}</strong></span></div>` : ''}
          ${d.game_versions?.length ? `<div class="stats"><span>Game versions: <strong>${d.game_versions.join(', ')}</strong></span></div>` : ''}
          ${d.categories?.length || d.additional_categories?.length ? `<div class="stats"><span>Categories: ${[...(d.categories||[]), ...(d.additional_categories||[])].map(c => '#'+c).join(' · ')}</span></div>` : ''}
          <div class="stats">
            <span>Published: <strong>${fmtDate(d.published)}</strong></span>
            <span>Updated: <strong>${fmtDate(d.updated)}</strong></span>
          </div>
          <div class="stats">
            <span>Client: <strong>${d.client_side || 'N/A'}</strong></span>
            <span>Server: <strong>${d.server_side || 'N/A'}</strong></span>
          </div>
          ${isInstalled
            ? '<button class="btn-sm installed" style="margin-top:10px" disabled>✓ Installed</button>'
            : '<button class="btn-primary" style="margin-top:10px" onclick="installMod(\'' + modId + '\',\'' + (document.getElementById('mod-version')?.value || '1.21.1') + '\',\'' + (document.getElementById('mod-source')?.value || 'modrinth') + '\',\'' + currentCategory + '\',\'' + (d.thumbnail || '') + '\',this); closeModDetail()">Download</button>'
          }
        </div>
      </div>

      ${d.gallery?.length ? `
        <div class="mod-detail-section">
          <h3>Screenshots</h3>
          <div class="mod-gallery">
            ${d.gallery.map(g => `
              <div class="mod-gallery-item">
                <img src="${g.url}" alt="${g.title || ''}" loading="lazy" />
                ${g.description ? `<div class="mod-gallery-caption">${g.description}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${hasLinks ? `
        <div class="mod-detail-section">
          <h3>Links</h3>
          <div class="mod-links">
            ${d.discord_url ? `<a href="${d.discord_url}" target="_blank" class="mod-link">💬 Discord</a>` : ''}
            ${d.issues_url ? `<a href="${d.issues_url}" target="_blank" class="mod-link">🐛 Issues</a>` : ''}
            ${d.source_url ? `<a href="${d.source_url}" target="_blank" class="mod-link">📄 Source</a>` : ''}
            ${d.wiki_url ? `<a href="${d.wiki_url}" target="_blank" class="mod-link">📖 Wiki</a>` : ''}
            ${(d.donation_urls || []).map(du =>
              `<a href="${du.url}" target="_blank" class="mod-link">❤️ ${du.platform}</a>`
            ).join('')}
          </div>
        </div>
      ` : ''}

      <div class="mod-detail-section">
        <h3>Description</h3>
        <div class="mod-detail-desc">${d.description || 'No description available.'}</div>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div class="loading">Error: ${e}</div>`;
  }
}

function closeModDetail(e) {
  if (e && e.target !== e.currentTarget) return;
  document.getElementById('mod-detail-overlay').classList.remove('open');
}

/* Helpers */
function showMsg(containerId, text, type = 'info') {
  const container = document.getElementById(containerId);
  const msg = document.createElement('div');
  msg.className = `msg ${type}`;
  msg.textContent = text;
  container.prepend(msg);
  setTimeout(() => msg.remove(), 4000);
}
