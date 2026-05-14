let currentPage = 'home';
let msLoginInterval = null;

/* Global toast */
function toast(text, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = text;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add('show'), 10);
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 3500);
}

/* Window controls */
function minimizeWin() { pywebview.api.minimize(); }
function maximizeWin() { pywebview.api.maximize(); }
function closeWin() { pywebview.api.close_window(); }

/* Frameless drag via begin_move_drag */
function initDrag() {
  const region = document.getElementById('drag-region');
  if (!region) return;
  region.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    pywebview.api.begin_window_move(e.button, e.screenX, e.screenY, e.timeStamp);
    e.preventDefault();
  });
}

function hideSplash() {
  const s = document.getElementById('splash');
  if (!s || s.classList.contains('hide')) return;
  s.classList.add('hide');
  setTimeout(() => s.remove(), 600);
}

function showSplash() {
  const s = document.getElementById('splash');
  if (s) requestAnimationFrame(() => s.classList.add('show'));
}

function initApp() {
  showSplash();
  try { initDrag(); } catch(e) { console.error('initDrag:', e); }
  initSidebar();
  initTabs();
  loadVersions();
  refreshHome();
  refreshAccount();
  initSettings();
  initModsPage();
  refreshVersions();
  refreshInstances();
  setTimeout(hideSplash, 1500);
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
  if (page === 'versions') refreshVersions();
  if (page === 'instances') refreshInstances();
  if (page === 'servers') loadServerHistory();
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
async function refreshHome() {
  try {
    const user = await pywebview.api.get_current_user();
    document.getElementById('user-badge').textContent = user ? `👤 ${user.slice(0, 15)}` : '👤 Account';
    const inst = await pywebview.api.get_current_instance();
    const badge = document.getElementById('instance-badge');
    if (inst) {
      badge.textContent = `${inst.icon || '📦'} ${inst.name} · ${inst.version}`;
    } else {
      badge.textContent = '📦 Default';
    }
  } catch (e) { console.error(e); }
}

let launchPoll = null;

document.getElementById('play-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('play-btn');
  btn.textContent = '⏳ Launching...';
  btn.disabled = true;
  try {
    const ver = document.getElementById('version-current').textContent;
    await pywebview.api.save_settings(JSON.stringify({ version: ver }));
    await pywebview.api.launch();
    if (launchPoll) clearInterval(launchPoll);
    launchPoll = setInterval(async () => {
      try {
        const status = await pywebview.api.get_launch_status();
        if (status.state === 'playing') {
          btn.textContent = '▶ Playing';
          btn.disabled = true;
        } else if (status.state === 'stopped') {
          clearInterval(launchPoll);
          launchPoll = null;
          btn.textContent = '▶  PLAY';
          btn.disabled = false;
        }
      } catch (e) { /* ignore */ }
    }, 2000);
  } catch (e) { console.error(e); }
});

/* Instances */
async function refreshInstances() {
  const list = document.getElementById('instances-list');
  if (!list) return;
  const instances = await pywebview.api.list_instances();
  const current = await pywebview.api.get_current_instance();
  const currentId = current?.id;
  if (!instances.length) {
    list.innerHTML = '<div class="loading" style="grid-column:1/-1">No instances yet. Create one to get started!</div>';
    return;
  }
  list.innerHTML = instances.map(inst => `
    <div class="instance-card ${inst.id === currentId ? 'active' : ''}" onclick="selectInstance('${inst.id}')">
      <div class="icon">${inst.icon || '📦'}</div>
      <div class="iname">${inst.name}</div>
      <div class="imeta">${inst.version} · ${inst.ram || 4}GB</div>
      ${inst.id === currentId ? '<div style="font-size:11px;color:var(--accent);font-weight:600">✓ Active</div>' : ''}
      <button class="idel" onclick="event.stopPropagation();deleteInstance('${inst.id}')">Delete</button>
    </div>
  `).join('');
}

async function selectInstance(id) {
  await pywebview.api.set_current_instance(id);
  refreshInstances();
  refreshHome();
  loadVersions();
  // Always refresh mods data regardless of active page
  refreshInstalled();
  browseOffset = 0;
  refreshBrowse(browseQuery || undefined);
}

function showCreateInstance() {
  const sel = document.getElementById('new-instance-version');
  if (!sel.children.length) {
    pywebview.api.get_versions().then(v => {
      sel.innerHTML = v.slice(0, 30).map(x => `<option value="${x}">${x}</option>`).join('');
    });
  }
  document.getElementById('create-instance-overlay').classList.add('open');
}

function closeCreateInstance() {
  document.getElementById('create-instance-overlay').classList.remove('open');
}

async function createInstance() {
  const name = document.getElementById('new-instance-name').value.trim();
  if (!name) return;
  const version = document.getElementById('new-instance-version').value;
  const icon = document.getElementById('new-instance-icon').value;
  await pywebview.api.create_instance(name, version, icon);
  closeCreateInstance();
  document.getElementById('new-instance-name').value = '';
  refreshInstances();
}

async function deleteInstance(id) {
  if (!confirm('Delete this instance and all its files?')) return;
  await pywebview.api.delete_instance(id);
  refreshInstances();
}

/* Version Picker */
let _versionGroups = [];

async function refreshVersions() {
  const list = document.getElementById('version-list-home');
  if (!list) return;
  list.innerHTML = '<div class="loading">Loading versions...</div>';
  _versionGroups = await pywebview.api.get_versions_grouped();
  const settings = await pywebview.api.get_settings();
  const current = settings.version;
  list.innerHTML = _versionGroups.map(g => `
    <div class="version-card ${g.versions.includes(current) ? 'active' : ''}" onclick="openVersionSubs('${g.major}')">
      <div class="version-card-header">
        <div class="icon-placeholder">📦</div>
        <div class="major">${g.major}.x</div>
      </div>
    </div>
  `).join('');
}

function openVersionSubs(major) {
  const group = _versionGroups.find(g => g.major === major);
  if (!group) return;
  document.getElementById('version-subs-title').textContent = `Minecraft ${major}.x`;
  const current = document.getElementById('version-current').textContent;
  document.getElementById('version-subs-list').innerHTML = group.versions.map(v => `
    <div class="version-sub ${v === current ? 'active' : ''}" onclick="selectVersion('${v}')">${v}</div>
  `).join('');
  document.getElementById('version-subs-overlay').classList.add('open');
}

function closeVersionSubs(e) {
  if (e && e.target !== e.currentTarget) return;
  document.getElementById('version-subs-overlay').classList.remove('open');
}

async function selectVersion(v) {
  await pywebview.api.save_settings(JSON.stringify({ version: v }));
  document.getElementById('version-current').textContent = v;
  closeVersionSubs();
  refreshVersions();
}

async function loadVersions() {
  try {
    const settings = await pywebview.api.get_settings();
    document.getElementById('version-current').textContent = settings.version;
    const versions = await pywebview.api.get_versions();
    const modVer = document.getElementById('mod-version');
    if (modVer) {
      modVer.innerHTML = versions.map(v => `<option value="${v}">${v}</option>`).join('');
      modVer.value = settings.version;
    }
  } catch (e) { console.error(e); }
}

/* Account */
function updateNavAvatar(uuid) {
  const navAvatar = document.getElementById('nav-avatar');
  if (!navAvatar) return;
  pywebview.api.get_avatar(uuid).then(url => {
    if (url) {
      navAvatar.innerHTML = `<img src="${url}" alt="" />`;
    } else {
      const fallback = 'data:image/svg+xml,' + encodeURIComponent('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>');
      navAvatar.innerHTML = `<img src="${fallback}" alt="" />`;
    }
  });
}

async function refreshAccount() {
  const container = document.getElementById('account-content');
  const skinEl = document.getElementById('account-skin');
  try {
    const auth = await pywebview.api.get_auth();
    const offlineUser = await pywebview.api.get_offline_username();
    const hasOffline = await pywebview.api.has_offline_account();

    // Skin
    let skinUuid = '';
    let displayName = '';
    if (auth && auth.uuid) skinUuid = auth.uuid;
    if (auth && auth.username) displayName = auth.username;
    else if (offlineUser) displayName = offlineUser;
    updateNavAvatar(skinUuid);

    let loginBadge = '';
    if (displayName) {
      const url = await pywebview.api.get_avatar(skinUuid);
      loginBadge = `
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;margin-top:-8px">
          <img src="${url}" alt="" style="width:64px;height:64px;border-radius:var(--radius);border:2px solid var(--border);background:var(--card);flex-shrink:0" />
          <div>
            <div style="font-size:13px;color:var(--text2)">Logged in as</div>
            <div style="font-size:28px;font-weight:800;color:var(--text)">${displayName}</div>
          </div>
        </div>`;
      skinEl.innerHTML = '';
    } else {
      const url = await pywebview.api.get_avatar('');
      skinEl.innerHTML = `<img src="${url}" alt="skin" />`;
    }

    if (auth && auth.username) {
      container.innerHTML = loginBadge + `
        <div class="account-card">
          <h3>✓ Premium Account</h3>
          <p class="label">UUID: ${auth.uuid || 'N/A'}</p>
          <button class="btn-danger" onclick="logoutAccount()">Logout</button>
        </div>`;
    } else {
      container.innerHTML = loginBadge + `
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
  toast(`Logged in as ${name}`, 'success');
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
    if (di.error) { toast(di.error, 'error'); return; }
    msLoginData = di;
    const area = document.getElementById('ms-login-area');
    area.innerHTML = `<div class="msg info">
      Open the browser and enter code: <strong style="font-size:24px">${di.user_code}</strong>
    </div>`;
    pollMsLogin();
  } catch (e) { toast(String(e), 'error'); }
}

async function pollMsLogin() {
  if (msLoginInterval) clearInterval(msLoginInterval);
  msLoginInterval = setInterval(async () => {
    try {
      const result = await pywebview.api.poll_microsoft_login(msLoginData.device_code);
      if (result.status === 'success') {
        clearInterval(msLoginInterval);
        msLoginInterval = null;
        toast(`Logged in as ${result.username}`, 'success');
        refreshAccount();
        refreshHome();
      } else if (result.error) {
        clearInterval(msLoginInterval);
        msLoginInterval = null;
        toast(result.error, 'error');
      }
    } catch (e) { console.error(e); }
  }, (msLoginData.interval || 5) * 1000);
}

/* Mods */
let currentCategory = 'mod';
let browseOffset = 0;
let browseQuery = '';
const PAGE_SIZE = 15;

function initModsPage() {
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.cat;
      browseOffset = 0;
      browseQuery = '';
      document.getElementById('mod-search').value = '';
      refreshBrowse();
      refreshInstalled();
    });
  });
  document.getElementById('mod-search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const activeTab = document.querySelector('#page-mods .tab-btn.active');
      const q = document.getElementById('mod-search').value.trim();
      if (activeTab?.dataset.tab === 'installed') {
        filterInstalled(q);
      } else {
        browseOffset = 0;
        browseQuery = q;
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
  const v = version || (selVersion ? selVersion.value : '1.21.1');
  const s = source || (selSource ? selSource.value : 'modrinth');
  const pt = currentCategory;
  const off = query !== undefined ? 0 : browseOffset;
  try {
    let data;
    if (query) data = await pywebview.api.search_mods(query, v, s, pt, off);
    else data = await pywebview.api.get_trending_mods(pt, off);
    const mods = data.mods || [];
    const total = data.total_hits || 0;
    if (mods.length === 0) { container.innerHTML = '<div class="loading">No results found.</div>'; return; }
    const installed = await pywebview.api.get_installed_mods(pt);
    const installedIds = new Set(installed.mods.filter(m => m.mod_id).map(m => m.mod_id));
    const hasPrev = off > 0;
    const hasNext = off + PAGE_SIZE < total;
    container.innerHTML = mods.map(m => `
      <div class="mod-card">
        <div class="mod-icon">
          ${m.thumbnail ? `<img src="${m.thumbnail}" alt="" />` : '📦'}
        </div>
        <div class="mod-info">
          <div class="name" style="cursor:pointer" onclick="showModDetail('${m.mod_id}')">${m.name}</div>
          <div class="desc">${(m.description || '').slice(0, 100)}${m.description?.length > 100 ? '...' : ''}</div>
          <div class="meta">v${m.version || 'N/A'} · ${(m.downloads || 0).toLocaleString()} downloads</div>
        </div>
        ${installedIds.has(m.mod_id)
          ? `<button class="btn-sm installed" disabled>✓ Installed</button>`
          : `<button class="btn-sm install" onclick="installMod('${m.mod_id}','${v}','${s}','${pt}','${m.thumbnail || ''}',this)">Download</button>`
        }
      </div>
    `).join('');
    container.innerHTML += `
      <div class="pagination">
        <button class="btn-page" onclick="goBrowsePage(-1)" ${hasPrev ? '' : 'disabled'}>← Previous</button>
        <span class="page-info">Page ${Math.floor(off / PAGE_SIZE) + 1} of ${Math.ceil(total / PAGE_SIZE)}</span>
        <button class="btn-page" onclick="goBrowsePage(1)" ${hasNext ? '' : 'disabled'}>Next →</button>
      </div>`;
  } catch (e) {
    container.innerHTML = `<div class="loading">Error: ${e}</div>`;
  }
}

function goBrowsePage(dir) {
  browseOffset = Math.max(0, browseOffset + dir * PAGE_SIZE);
  refreshBrowse(browseQuery || undefined);
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

async function installMod(modId, version, source, projectType, thumbnail, btn, loader) {
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

/* Detect Java */
async function detectJava() {
  const btn = document.getElementById('detect-java-btn');
  const list = document.getElementById('java-detected-list');
  btn.textContent = '🔍 Scanning...';
  btn.disabled = true;
  try {
    const javas = await pywebview.api.detect_java();
    btn.textContent = '🔍 Detect Java';
    btn.disabled = false;
    if (!javas.length) { alert('No Java installations found.'); return; }
    list.style.display = 'block';
    list.innerHTML = '<option value="">Select a Java version...</option>' +
      javas.map(j => `<option value="${j.path}">${j.version} — ${j.path}</option>`).join('');
  } catch (e) {
    btn.textContent = '🔍 Detect Java';
    btn.disabled = false;
    alert('Error detecting Java: ' + e);
  }
}

function applyDetectedJava(path) {
  if (!path) return;
  document.getElementById('java-path').value = path;
}

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
    toast('Saved!', 'success');
  } catch (e) { toast(String(e), 'error'); }
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

/* Servers */
const FEATURED = [
  { ip: 'mc.hypixel.net', name: 'Hypixel', desc: 'The largest Minecraft server', icon: '⚔️' },
  { ip: 'play.minetime.cc', name: 'MineTime', desc: 'Survival, Skyblock, Minigames', icon: '⛏️' },
  { ip: 'us.mineplex.com', name: 'Mineplex', desc: 'Classic minigames server', icon: '🛡️' },
  { ip: 'mc.cubecraft.net', name: 'CubeCraft', desc: 'Minigames & Bedrock crossplay', icon: '🎮' },
  { ip: 'play.vanillamongus.com', name: 'VanillaMongus', desc: 'Among Us in Minecraft', icon: '👾' },
  { ip: 'pvp.pvpcraft.ca', name: 'PvPCraft', desc: 'Competitive PvP server', icon: '🔥' },
];

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('server-ip')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') checkServer(); });
  // Server tabs
  document.querySelectorAll('.server-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.server-tabs .tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.stab-content').forEach(t => t.classList.remove('active'));
      document.getElementById(`server-${btn.dataset.stab}`)?.classList.add('active');
      if (btn.dataset.stab === 'featured') loadFeatured();
    });
  });
});

function loadFeatured() {
  const el = document.getElementById('server-featured');
  el.innerHTML = `<div class="featured-list">${FEATURED.map(s => `
    <div class="featured-item" onclick="document.getElementById('server-ip').value='${s.ip}';checkServer()">
      <div class="fi-icon">${s.icon}</div>
      <div class="fi-info">
        <div class="fi-name">${s.name}</div>
        <div class="fi-desc">${s.desc}</div>
        <div class="fi-desc" style="color:var(--accent);font-size:11px">${s.ip}</div>
      </div>
    </div>
  `).join('')}</div>`;
}

function loadServerHistory() {
  const list = document.getElementById('server-recent');
  const recent = JSON.parse(localStorage.getItem('recentServers') || '[]');
  if (!recent.length) { list.innerHTML = '<div class="loading" style="padding:10px 0">No recent servers.</div>'; return; }
  list.innerHTML = recent.map(ip => `<div class="server-recent-item" onclick="document.getElementById('server-ip').value='${ip}';checkServer()">🌐 ${ip}</div>`).join('');
}

async function checkServer() {
  const ip = document.getElementById('server-ip').value.trim();
  if (!ip) return;
  const result = document.getElementById('server-result');
  result.innerHTML = '<div class="loading">Checking...</div>';
  try {
    const d = await pywebview.api.get_server_info(ip);
    if (d.error) { result.innerHTML = `<div class="msg error">${d.error}</div>`; return; }
    const online = d.online;
    result.innerHTML = `
      <div class="server-card">
        <div class="icon">${online ? '🟢' : '🔴'}</div>
        <div class="info">
          <div class="name">${d.hostname || ip}</div>
          ${d.motd?.clean?.length ? `<div class="motd">${d.motd.clean.join('<br>')}</div>` : ''}
          <div class="meta">${d.version || 'Unknown'} · ${d.protocol || '?'} protocol</div>
          ${online ? `<div class="players">👤 ${d.players?.online || 0}/${d.players?.max || 0} players</div>` : '<div class="players">🔴 Offline</div>'}
          ${d.players?.list?.length ? `<div class="players">Online: ${d.players.list.join(', ')}</div>` : ''}
        </div>
      </div>`;
    const recent = JSON.parse(localStorage.getItem('recentServers') || '[]');
    const filtered = recent.filter(s => s !== ip);
    filtered.unshift(ip);
    localStorage.setItem('recentServers', JSON.stringify(filtered.slice(0, 10)));
    loadServerHistory();
  } catch (e) {
    result.innerHTML = `<div class="msg error">Error: ${e}</div>`;
  }
}


