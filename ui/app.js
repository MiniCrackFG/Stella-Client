window.shootingStars = [];

function createStars() {
  const canvas = document.getElementById('stars');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  let width = window.innerWidth;
  let height = window.innerHeight;
  canvas.width = width;
  canvas.height = height;

  window.addEventListener('resize', () => {
    const oldW = width || 1;
    const oldH = height || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
    stars.forEach(s => {
      s.x = (s.x / oldW) * width;
      s.y = (s.y / oldH) * height;
    });
  });

  const stars = [];
  for (let i = 0; i < 200; i++) {
    stars.push({
      x: Math.random() * width,
      y: Math.random() * height,
      size: 1 + Math.random() * 2,
      baseAlpha: 0.3 + Math.random() * 0.5,
      blinkSpeed: 0.005 + Math.random() * 0.015,
      angle: Math.random() * Math.PI * 2,
      driftX: (Math.random() - 0.5) * 0.2,
      driftY: (Math.random() - 0.5) * 0.2,
    });
  }

  let animating = !document.body.classList.contains('no-smooth');
  let scheduled = false;
  let staticPainted = false;

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(draw);
  }

  function draw(ts) {
    scheduled = false;
    if (!animating) {
      // Sin animación pintamos un único fotograma y dejamos de gastar CPU
      if (staticPainted) return;
      staticPainted = true;
    }
    ctx.clearRect(0, 0, width, height);
    const isLight = document.body.classList.contains('theme-light');
    ctx.fillStyle = isLight ? '#7c5cbf' : '#ffffff';

    stars.forEach(s => {
      if (animating) {
        s.angle += s.blinkSpeed;
        s.x += s.driftX;
        s.y += s.driftY;

        if (s.x < 0) s.x = width;
        if (s.x > width) s.x = 0;
        if (s.y < 0) s.y = height;
        if (s.y > height) s.y = 0;
      }

      const alpha = animating ? s.baseAlpha + Math.sin(s.angle) * 0.3 : s.baseAlpha;
      ctx.globalAlpha = Math.max(0.1, Math.min(1, alpha));
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;

    // Draw shooting stars (solo mientras la animación está activa)
    for (let i = animating ? window.shootingStars.length - 1 : -1; i >= 0; i--) {
      const ss = window.shootingStars[i];
      if (!ss.startTime) ss.startTime = ts;
      const elapsed = (ts - ss.startTime) / 1000;
      const progress = Math.min(elapsed / ss.duration, 1);
      
      const x = ss.startX + ss.dx * progress;
      const y = ss.startY + ss.dy * progress;

      // Draw Trail Particles
      ctx.shadowBlur = 4;
      ctx.shadowColor = isLight ? 'rgba(150,100,255,0.3)' : 'rgba(168,85,247,0.5)';
      ss.trail.forEach(p => {
        const pElapsed = Math.max(0, progress - p.delay);
        if (pElapsed > 0) {
          const pProgress = pElapsed / 0.25;
          const fade = 1 - pProgress;
          if (fade > 0) {
            ctx.globalAlpha = fade * 0.9;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(x + p.ox * pProgress - 16, y + p.oy * pProgress - 16, p.size / 2, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      });
      ctx.globalAlpha = 1;

      // Draw Head (SVG Star)
      if (progress < 0.7) {
        ctx.save();
        ctx.translate(x, y);
        // rotate based on time
        ctx.rotate((elapsed * 360 / (ss.duration * 0.4)) * Math.PI / 180);
        ctx.translate(-16, -16); // offset by half SVG size (32/2)
        
        ctx.shadowBlur = 12;
        ctx.shadowColor = ss.glowColor;
        
        ctx.strokeStyle = ss.color;
        ctx.lineWidth = 1.5;
        
        const starPath = new Path2D('M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z');
        ctx.stroke(starPath);
        
        ctx.restore();
      }

      // Explosion
      if (progress >= 0.7) {
        if (!ss.exploded) {
          ss.exploded = true;
          ss.explosion = [];
          for (let p = 0; p < 35; p++) {
            const angle = Math.random() * 2 * Math.PI;
            const speed = 60 + Math.random() * 100;
            ss.explosion.push({
              x: x, y: y,
              vx: Math.cos(angle) * speed,
              vy: Math.sin(angle) * speed,
              color: ss.explColors[Math.floor(Math.random() * ss.explColors.length)],
              size: 3 + Math.random() * 5
            });
          }
        }
        
        const epElapsed = (progress - 0.7) / 0.3;
        const fade = 1 - epElapsed;
        if (fade > 0) {
          ctx.shadowBlur = 6;
          ctx.shadowColor = isLight ? 'rgba(150,100,255,0.4)' : 'rgba(168,85,247,0.6)';
          ss.explosion.forEach(ep => {
            ctx.globalAlpha = fade;
            ctx.fillStyle = ep.color;
            ctx.beginPath();
            ctx.arc(ep.x + ep.vx * epElapsed, ep.y + ep.vy * epElapsed, ep.size / 2, 0, Math.PI * 2);
            ctx.fill();
          });
        }
        ctx.globalAlpha = 1;
      }

      ctx.shadowBlur = 0; // reset
      if (progress >= 1) {
        window.shootingStars.splice(i, 1);
      }
    }

    if (animating) schedule();
  }

  window.__setBackgroundAnimating = (on) => {
    animating = !!on;
    staticPainted = false;
    if (!animating) window.shootingStars = [];
    schedule();
  };

  schedule();

  const moon = document.createElement('div');
  moon.className = 'moon';
  moon.id = 'draggable-moon';

  function updateMoonTheme() {
    const isLight = document.body.classList.contains('theme-light');
    const isOled = document.body.classList.contains('theme-oled');
    if (isOled) {
      moon.style.background = 'radial-gradient(circle at 35% 35%, #e8e8f0, #c0c0d0 40%, #8888a0 80%, #444460)';
      moon.style.boxShadow = '0 0 40px rgba(150, 150, 200, 0.3), 0 0 80px rgba(100, 100, 160, 0.15)';
      moon._glow = '0 0 40px rgba(150, 150, 200, 0.3), 0 0 80px rgba(100, 100, 160, 0.15)';
      moon._glowHover = '0 0 50px rgba(150, 150, 200, 0.4), 0 0 100px rgba(100, 100, 160, 0.2)';
    } else if (isLight) {
      moon.style.background = 'radial-gradient(circle at 35% 35%, #ffffff, #e8e0f8 40%, #c8b8e8 80%, #a890d0)';
      moon.style.boxShadow = '0 0 50px rgba(180, 150, 220, 0.5), 0 0 100px rgba(160, 130, 200, 0.25)';
      moon._glow = '0 0 50px rgba(180, 150, 220, 0.5), 0 0 100px rgba(160, 130, 200, 0.25)';
      moon._glowHover = '0 0 60px rgba(180, 150, 220, 0.7), 0 0 120px rgba(160, 130, 200, 0.35)';
    } else {
      moon.style.background = 'radial-gradient(circle at 35% 35%, #f5f3ff, #c4b5fd 40%, #7c3aed 80%, #4c1d95)';
      moon.style.boxShadow = '0 0 50px rgba(168,85,247,0.5), 0 0 100px rgba(124,58,237,0.25)';
      moon._glow = '0 0 50px rgba(168,85,247,0.5), 0 0 100px rgba(124,58,237,0.25)';
      moon._glowHover = '0 0 60px rgba(168,85,247,0.7), 0 0 120px rgba(124,58,237,0.35)';
    }
  }

  moon.style.cssText = 'position:fixed;left:80px;top:60px;z-index:9998;cursor:grab;user-select:none;pointer-events:auto;opacity:0.8;width:70px;height:70px;border-radius:50%;transition:box-shadow 0.3s, background 0.3s;border:2px solid rgba(0,0,0,0.3);';
  updateMoonTheme();

  moon.addEventListener('mouseenter', () => {
    if (!moon._isDragging) moon.style.boxShadow = moon._glowHover;
  });
  moon.addEventListener('mouseleave', () => {
    if (!moon._isDragging) moon.style.boxShadow = moon._glow;
  });

  const crater1 = document.createElement('div');
  crater1.style.cssText = 'position:absolute;width:55px;height:55px;border-radius:50%;top:7px;left:10px;background:radial-gradient(circle at 30% 30%, rgba(245,243,255,0.4), transparent 70%);';
  moon.appendChild(crater1);
  const crater2 = document.createElement('div');
  crater2.style.cssText = 'position:absolute;width:16px;height:16px;border-radius:50%;top:18px;left:32px;background:radial-gradient(circle at 30% 30%, rgba(196,181,253,0.3), transparent);';
  moon.appendChild(crater2);

  let animStartTime = null;
  let animPausedTime = 0;
  const animDuration = 30000;
  const travelDist = () => window.innerWidth * 0.8 + 160;

  let moonRunning = true;

  function updateMoon(timestamp) {
    // Sin renderizado suave la luna se queda quieta donde esté, sin bucle
    if (document.body.classList.contains('no-smooth')) { moonRunning = false; return; }
    moonRunning = true;
    if (!moon._isDragging) {
      if (!animStartTime) animStartTime = timestamp - animPausedTime;
      const elapsed = timestamp - animStartTime;
      const progress = (elapsed % animDuration) / animDuration;
      const tx = -80 + travelDist() * progress;
      const opacity = progress < 0.05 ? progress / 0.05 * 0.8
        : progress > 0.95 ? (1 - (progress - 0.95) / 0.05) * 0.8
        : progress > 0.45 && progress < 0.55 ? 0.2 + (0.6 - Math.abs(progress - 0.5) * 2) * 0.6 * 0.8
        : 0.8;
      moon.style.transform = `translateX(${tx}px)`;
      moon.style.opacity = opacity;
    }
    requestAnimationFrame(updateMoon);
  }

  moon._isDragging = false;
  moon.addEventListener('mousedown', (e) => {
    moon._isDragging = true;
    moon._startX = e.clientX;
    moon._startY = e.clientY;
    moon._startLeft = parseFloat(getComputedStyle(moon).left) || 80;
    moon._startTop = parseFloat(getComputedStyle(moon).top) || 60;
    moon.style.cursor = 'grabbing';
    document.body.style.cursor = 'grabbing';
    e.preventDefault();
  });
  document.addEventListener('mousemove', (e) => {
    if (!moon._isDragging) return;
    const dx = e.clientX - moon._startX;
    const dy = e.clientY - moon._startY;
    moon.style.left = (moon._startLeft + dx) + 'px';
    moon.style.top = (moon._startTop + dy) + 'px';
    moon.style.cursor = 'grabbing';
    document.body.style.cursor = 'grabbing';
  });
  document.addEventListener('mouseup', () => {
    if (!moon._isDragging) return;
    moon._isDragging = false;
    moon.style.cursor = 'grab';
    document.body.style.cursor = '';
  });

  new MutationObserver(() => {
    updateMoonTheme();
  }).observe(document.body, { attributes: true, attributeFilter: ['class'] });

  document.body.appendChild(moon);
  requestAnimationFrame(updateMoon);

  window.__restartMoon = () => {
    if (!moonRunning && !document.body.classList.contains('no-smooth')) requestAnimationFrame(updateMoon);
  };
}

function createShootingStar() {
  const isLight = document.body.classList.contains('theme-light');
  const starColor = isLight ? '#fff' : '#a78bfa';
  const glowColor = isLight ? 'rgba(200,200,255,0.6)' : 'rgba(168,85,247,0.8)';
  const trailColors = isLight ? ['#a855f7', '#c084fc', '#9333ea', '#7c3aed'] : ['#fff', '#a78bfa', '#c084fc', '#e9d5ff'];
  const explColors = isLight ? ['#7c3aed', '#a855f7', '#c084fc', '#9333ea', '#6d28d9'] : ['#fff', '#a78bfa', '#c084fc', '#e9d5ff', '#f5f3ff'];

  const startX = 2 + Math.random() * 8;
  const startY = 2 + Math.random() * 8;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const startPxX = vw * startX / 100;
  const startPxY = vh * startY / 100;
  const endX = vw * (0.92 + Math.random() * 0.07);
  const endY = vh * (0.9 + Math.random() * 0.08);
  const dx = endX - startPxX;
  const dy = endY - startPxY;
  const duration = 1.8 + Math.random() * 0.6;

  const trail = [];
  const particleCount = 50 + Math.floor(Math.random() * 20);
  for (let i = 0; i < particleCount; i++) {
    trail.push({
      ox: (Math.random() - 0.5) * 35,
      oy: (Math.random() - 0.5) * 20 - 5,
      size: 2 + Math.random() * 3,
      delay: Math.random() * 0.15,
      color: trailColors[Math.floor(Math.random() * trailColors.length)]
    });
  }

  window.shootingStars.push({
    startX: startPxX,
    startY: startPxY,
    dx: dx,
    dy: dy,
    duration: duration,
    size: 2 + Math.random() * 2,
    color: starColor,
    glowColor: glowColor,
    explColors: explColors,
    trail: trail,
    exploded: false
  });
}

function scheduleShootingStar() {
  function spawn() {
    if (document.body.classList.contains('no-smooth')) return;
    const roll = Math.random() * 100;
    let count = 1;
    if (roll < 25) count = 3;
    else if (roll < 55) count = 2;
    for (let i = 0; i < count; i++) {
      setTimeout(() => createShootingStar(), i * 200);
    }
  }
  function reschedule() {
    const delay = 5000 + Math.random() * 15000;
    setTimeout(() => { spawn(); reschedule(); }, delay);
  }
  setTimeout(() => { spawn(); reschedule(); }, 3000);
}

let currentPage = 'home';
let msLoginInterval = null;

/* Seguridad: nunca insertar datos remotos o del usuario en HTML sin escapar */
function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* Literal seguro para una cadena JS entre comillas simples dentro de un atributo HTML */
function jsArg(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/[\r\n]/g, ' ');
}

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
function maximizeWin() { pywebview.api.toggle_maximize(); }
function closeWin() { pywebview.api.close_window(); }

/* Frameless drag via begin_move_drag */
function initDrag() {
  const bar = document.getElementById('titlebar');
  if (!bar) return;
  bar.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    // Los botones viven dentro de la barra: si la pulsación nace en uno, es un
    // clic suyo y no un arrastre.
    if (e.target.closest && e.target.closest('.win-btns')) return;
    pywebview.api.begin_window_move(e.button, e.screenX, e.screenY, e.timeStamp);
    e.preventDefault();
  });
  // Doble clic en la barra: maximizar o restaurar, como en cualquier ventana.
  bar.addEventListener('dblclick', (e) => {
    if (e.target.closest && e.target.closest('.win-btns')) return;
    maximizeWin();
  });
}

function hideSplash() {
  const s = document.getElementById('splash');
  if (!s) return;
  if (!s.classList.contains('hide')) s.classList.add('hide');
  setTimeout(() => document.getElementById('splash')?.remove(), 700);
}

function showSplash() {
  const s = document.getElementById('splash');
  if (s) requestAnimationFrame(() => s.classList.add('show'));
}

function initApp() {
  const steps = [
    initPlatform, createStars, scheduleShootingStar, initInputEffects, showSplash,
    initDrag, initSidebar, initTabs, loadVersions, refreshHome,
    refreshAccount, initSettings, initModsPage, refreshVersions, refreshInstances,
  ];
  for (const step of steps) {
    // Un paso que falle no debe impedir que el resto de la UI arranque ni tapar la pantalla
    try { step(); } catch (e) { console.error('init:', step.name, e); }
  }
  setTimeout(hideSplash, 1500);
  setTimeout(hideSplash, 5000);
}

/* Sistema en el que corre el launcher: hay detalles de estilo que sólo valen en
   uno (la barra de scroll), y así los elegimos por CSS y no por el userAgent. */
async function initPlatform() {
  try {
    const platform = await pywebview.api.get_platform();
    if (platform === 'windows') document.body.classList.add('platform-win');
  } catch (e) {
    console.error('init: get_platform', e);
  }
}

/* Espera activa al puente de pywebview: no dependemos de un único evento */
function whenBridgeReady(callback) {
  let done = false;
  const run = () => { if (!done) { done = true; callback(); } };
  if (window.pywebview && window.pywebview.api) { run(); return; }
  window.addEventListener('pywebviewready', run);
  const started = Date.now();
  const timer = setInterval(() => {
    if (window.pywebview && window.pywebview.api) {
      clearInterval(timer);
      run();
    } else if (Date.now() - started > 15000) {
      clearInterval(timer);
      hideSplash();
      toast('No se pudo conectar con el backend del launcher', 'error');
    }
  }, 100);
}

/* Cualquier error visible en pantalla en vez de quedarse en un misterio */
window.addEventListener('error', (e) => {
  try { toast('Error: ' + (e.message || e), 'error'); } catch (_) { /* ignore */ }
});
window.addEventListener('unhandledrejection', (e) => {
  try {
    const reason = e.reason && (e.reason.message || e.reason);
    toast('Error: ' + (reason || 'desconocido'), 'error');
  } catch (_) { /* ignore */ }
});

whenBridgeReady(initApp);

/* Navigation */
function initSidebar() {
  const tooltip = document.createElement('div');
  tooltip.style.cssText = 'position:fixed;font-size:15px;padding:8px 18px;border-radius:8px;white-space:nowrap;font-weight:700;pointer-events:none;z-index:99999;opacity:0;transition:opacity 0.2s ease;border:1px solid rgba(168,85,247,0.25);box-shadow:0 4px 12px rgba(0,0,0,0.5);font-family:\'Comic Neue\',sans-serif;';
  tooltip.style.backdropFilter = 'blur(4px)';
  tooltip.style.webkitBackdropFilter = 'blur(4px)';

  function updateTooltipBg() {
    if (document.body.classList.contains('theme-light')) {
      tooltip.style.background = 'rgba(245, 245, 250, 0.92)';
    } else if (document.body.classList.contains('theme-oled')) {
      tooltip.style.background = 'rgba(0, 0, 0, 0.95)';
    } else {
      tooltip.style.background = 'rgba(10, 7, 32, 0.9)';
    }
  }
  updateTooltipBg();
  new MutationObserver(updateTooltipBg).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  tooltip.style.backdropFilter = 'blur(4px)';
  tooltip.style.webkitBackdropFilter = 'blur(4px)';
  document.body.appendChild(tooltip);

  function setTooltip(text) {
    tooltip.innerHTML = '';
    const inner = document.createElement('span');
    inner.style.background = 'linear-gradient(90deg, #a855f7, #3b82f6, #ec4899, #06b6d4, #a855f7, #3b82f6, #ec4899, #06b6d4)';
    inner.style.backgroundSize = '300% 100%';
    inner.style.webkitBackgroundClip = 'text';
    inner.style.webkitTextFillColor = 'transparent';
    inner.style.animation = 'slideRight 12s linear infinite';
    inner.style.fontFamily = "'Comic Neue', sans-serif";
    inner.style.fontSize = '15px';
    inner.textContent = text.charAt(0).toUpperCase() + text.slice(1);
    tooltip.appendChild(inner);
  }

  document.querySelectorAll('.nav-btn[data-page]').forEach(btn => {
    btn.addEventListener('mouseenter', (e) => {
      const rect = btn.getBoundingClientRect();
      setTooltip(btn.title || btn.dataset.page);
      tooltip.style.left = (rect.right + 10) + 'px';
      tooltip.style.top = (rect.top + rect.height / 2 - 12) + 'px';
      tooltip.style.opacity = '1';
    });
    btn.addEventListener('mouseleave', () => {
      tooltip.style.opacity = '0';
    });
    btn.removeAttribute('title');
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
  if (page === 'mods') {
    // Se refresca también la lista de Browse: si la primera carga falló (arranque
    // sin red, error de Modrinth...), al abrir la pestaña se reintenta sola.
    refreshInstalled();
    refreshBrowse(browseQuery || undefined, undefined, undefined, browseOffset);
  }
  if (page === 'versions') refreshVersions();
  if (page === 'instances') refreshInstances();
  if (page === 'settings') refreshSettingsForm();
  if (page === 'servers') loadServerHistory();
}

/* Generic Tabs */
function initTabs() {
  // Mods y Settings tienen su propio manejador (refrescan datos al cambiar de pestaña),
  // así que aquí se excluyen para no procesar cada clic dos veces.
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    if (btn.closest('.mods-tabs') || btn.closest('.settings-tabs')) return;
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
      const iconHtml = inst.icon && inst.icon !== '📦' ? inst.icon : '<svg class="ver-star-badge" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7a72b0" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>';
      badge.innerHTML = `<span class="badge-grad">${iconHtml} ${escapeHtml(inst.name)} · ${escapeHtml(inst.version)}</span>`;
    } else {
      badge.innerHTML = '<span class="badge-grad"><svg class="ver-star-badge" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7a72b0" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg> Default</span>';
    }
  } catch (e) { console.error(e); }
}

let launchPoll = null;

/* Barra de descarga inferior: solo aparece cuando el arranque tiene que bajar
   archivos (versión nueva, Fabric, librerías...). Con el juego ya instalado no
   se enseña nada, porque entonces no hay ninguna descarga que enseñar. */
function renderLaunchProgress(status) {
  const bar = document.getElementById('launch-progress');
  if (!bar) return;
  const show = !!(status && status.state === 'launching' && status.needs_download);
  bar.classList.toggle('show', show);
  // El toast se aparta mientras la barra está abierta (abajo del todo hay barra)
  document.body.classList.toggle('launch-bar-visible', show);
  if (!show) return;

  const label = document.getElementById('lp-label');
  const pct = document.getElementById('lp-pct');
  const fill = document.getElementById('lp-fill');
  const max = Number(status.max) || 0;
  const progress = Number(status.progress) || 0;
  const known = max > 0;
  const percent = known ? Math.min(100, Math.round((progress / max) * 100)) : null;

  if (label) label.textContent = status.phase || 'Preparando la descarga';
  if (pct) pct.textContent = percent === null ? '···' : `${percent}%`;
  if (fill) {
    fill.classList.toggle('indeterminate', percent === null);
    fill.style.width = percent === null ? '' : `${percent}%`;
  }
}

document.getElementById('play-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('play-btn');
  const resetBtn = () => { btn.textContent = '▶  PLAY'; btn.disabled = false; };
  const stopPolling = () => { if (launchPoll) { clearInterval(launchPoll); launchPoll = null; } };
  btn.textContent = '⏳ Launching...';
  btn.disabled = true;
  try {
    const ver = document.getElementById('version-current').textContent;
    await pywebview.api.save_settings(JSON.stringify({ version: ver }));
    const res = await pywebview.api.launch();
    if (res && res.ok === false) {
      toast(res.error || 'No se pudo iniciar Minecraft', 'error');
      resetBtn();
      return;
    }
    stopPolling();
    const pollOnce = async () => {
      try {
        const status = await pywebview.api.get_launch_status();
        renderLaunchProgress(status);
        if (status.state === 'playing') {
          btn.textContent = '▶ Playing';
          btn.disabled = true;
        } else if (status.state === 'error') {
          stopPolling();
          toast(status.message || 'El arranque falló', 'error');
          resetBtn();
        } else if (status.state === 'stopped') {
          stopPolling();
          resetBtn();
        }
      } catch (e) { /* ignore */ }
    };
    // Primera lectura inmediata (la barra sale al instante) y luego cada 400 ms:
    // con 2 s el porcentaje daba saltos y parecía congelado.
    await pollOnce();
    launchPoll = setInterval(pollOnce, 400);
  } catch (e) {
    toast(String(e), 'error');
    resetBtn();
  }
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
    <div class="instance-card ${inst.id === currentId ? 'active' : ''}" onclick="selectInstance('${jsArg(inst.id)}')">
      <div class="icon">${inst.icon && inst.icon !== '📦' ? escapeHtml(inst.icon) : '<svg class="ver-star" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#7a72b0" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>'}</div>
      <div class="iname">${escapeHtml(inst.name)}</div>
      <div class="imeta">${escapeHtml(inst.version)} · ${Number(inst.ram || 4)}GB</div>
      ${inst.id === currentId ? '<div style="font-size:11px;color:var(--accent);font-weight:600">✓ Active</div>' : ''}
      <button class="idel" onclick="event.stopPropagation();deleteInstance('${jsArg(inst.id)}')">Delete</button>
    </div>
  `).join('');
}

async function selectInstance(id) {
  await pywebview.api.set_current_instance(id);
  refreshInstances();
  refreshHome();
  loadVersions();
  refreshSettingsForm();
  // Always refresh mods data regardless of active page
  refreshInstalled();
  browseOffset = 0;
  refreshBrowse(browseQuery || undefined, undefined, undefined, 0);
}

function showCreateInstance() {
  const sel = document.getElementById('new-instance-version');
  if (!sel.children.length) {
    pywebview.api.get_versions().then(v => {
      sel.innerHTML = v.slice(0, 30).map(x => `<option value="${escapeHtml(x)}">${escapeHtml(x)}</option>`).join('');
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
  const inst = await pywebview.api.create_instance(name, version, icon);
  closeCreateInstance();
  document.getElementById('new-instance-name').value = '';
  if (inst && inst.id) {
    // La instancia recién creada se deja activa de una vez: así los mods y los
    // ajustes van a su carpeta y no a la de la instancia anterior.
    await selectInstance(inst.id);
  } else {
    refreshInstances();
  }
}

async function deleteInstance(id) {
  if (!confirm('Delete this instance and all its files?')) return;
  await pywebview.api.delete_instance(id);
  // El backend reasigna otra instancia si borramos la activa
  browseOffset = 0;
  refreshInstances();
  refreshHome();
  loadVersions();
  refreshSettingsForm();
  refreshInstalled();
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
    <div class="version-card ${g.versions.includes(current) ? 'active' : ''}" onclick="openVersionSubs('${jsArg(g.major)}')">
      <div class="version-card-header">
        <div class="icon-placeholder"><svg class="ver-star" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#7a72b0" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg></div>
        <div class="major">${escapeHtml(g.major)}.x</div>
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
    <div class="version-sub ${v === current ? 'active' : ''}" onclick="selectVersion('${jsArg(v)}')">${escapeHtml(v)}</div>
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
      modVer.innerHTML = versions.map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');
      modVer.value = settings.version;
    }
  } catch (e) { console.error(e); }
}

/* Account */
/* La cabeza de la skin la carga la propia página: es el mismo camino por el que
   ya se ven las miniaturas de los mods, y así no depende de la descarga que hace
   el backend. Si esa imagen no llega se pide el segundo intento al backend y,
   como última red, se pinta el glifo local: lo que nunca se pinta es un `src`
   vacío, que era el icono de imagen rota que salía en la ventana.

   El color va dentro del SVG a propósito: este dibujo se pinta dentro de un
   `<img>`, y ahí no hereda nada de la página (`currentColor` se quedaría en
   negro sobre el fondo oscuro y no se vería). */
const AVATAR_GLYPH = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2">' +
  '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
);

function avatarUrl(uuid) {
  return `https://mc-heads.net/avatar/${encodeURIComponent(uuid || 'steve')}/128`;
}

/* Segundo intento y última red: el backend, y si tampoco trae nada, el glifo. */
async function avatarRetry(img, uuid) {
  if (img.dataset.avatarRetried) { img.src = AVATAR_GLYPH; return; }
  img.dataset.avatarRetried = '1';
  let url = '';
  try { url = await pywebview.api.get_avatar(uuid || ''); } catch (e) { url = ''; }
  img.src = url || AVATAR_GLYPH;
}

function avatarImg(uuid, attributes = '') {
  return `<img src="${escapeHtml(avatarUrl(uuid))}" alt="" ${attributes} onerror="avatarRetry(this,'${jsArg(uuid)}')" />`;
}

function updateNavAvatar(uuid) {
  const navAvatar = document.getElementById('nav-avatar');
  if (!navAvatar) return;
  navAvatar.innerHTML = avatarImg(uuid);
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
      loginBadge = `
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;margin-top:-8px">
          ${avatarImg(skinUuid, 'style="width:64px;height:64px;border-radius:var(--radius);border:2px solid var(--border);background:var(--card);flex-shrink:0"')}
          <div>
            <div style="font-size:13px;color:var(--text2)">Logged in as</div>
            <div style="font-size:28px;font-weight:800;color:var(--text)">${escapeHtml(displayName)}</div>
          </div>
        </div>`;
      skinEl.innerHTML = '';
    } else {
      skinEl.innerHTML = avatarImg(skinUuid);
    }

    if (auth && auth.username) {
      container.innerHTML = loginBadge + `
        <div class="account-card">
          <h3>✓ Premium Account</h3>
          <p class="label">UUID: ${escapeHtml(auth.uuid || 'N/A')}</p>
          <button class="btn-danger" onclick="logoutAccount()">Logout</button>
        </div>`;
    } else {
      container.innerHTML = loginBadge + `
        <div class="account-card">
          <h3>${hasOffline ? '✓ Offline Mode' : 'Offline / Microsoft'}</h3>
          ${hasOffline ? `<p>Playing as: <strong>${escapeHtml(offlineUser)}</strong></p>` : '<p>No offline profile configured.</p>'}
          <label class="label">Username</label>
          <input type="text" id="offline-input" placeholder="Enter a nickname" value="${escapeHtml(offlineUser || '')}" />
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
    area.innerHTML = `<div class="msg info ms-login">
      <div>Open the browser and enter this code:</div>
      <div class="ms-code-row">
        <span class="ms-code" title="Click to copy" onclick="copyMsCode()">${escapeHtml(di.user_code)}</span>
        <button class="btn-copy" onclick="copyMsCode(this)">📋 Copy code</button>
      </div>
    </div>`;
    pollMsLogin();
  } catch (e) { toast(String(e), 'error'); }
}

/* Copiar al portapapeles con tres intentos: GTK (lo más fiable en WebKitGTK),
   la API del navegador y, si falla, el truco del textarea. */
async function copyText(text) {
  if (!text) return false;
  try {
    if (await pywebview.api.copy_to_clipboard(text)) return true;
  } catch (_) { /* seguimos con el siguiente método */ }
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_) { /* seguimos */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:-1000px;left:-1000px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, text.length);
    const ok = document.execCommand('copy');
    ta.remove();
    return ok;
  } catch (_) {
    return false;
  }
}

async function copyMsCode(btn) {
  const code = (msLoginData && msLoginData.user_code) || '';
  if (!code) return;
  const ok = await copyText(code);
  if (btn && btn.textContent) {
    const original = btn.textContent;
    btn.textContent = ok ? '✓ Copied' : '✗ Failed';
    setTimeout(() => { btn.textContent = original; }, 1600);
  }
  toast(ok ? `Code ${code} copied to clipboard` : 'Could not copy the code', ok ? 'success' : 'error');
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


function createTypingChar(input, char) {
  input.style.transition = 'box-shadow 0.3s ease';
  input.style.boxShadow = '0 0 20px rgba(168,85,247,0.6), 0 0 50px rgba(59,130,246,0.3), inset 0 0 15px rgba(168,85,247,0.1)';
  setTimeout(() => {
    input.style.boxShadow = 'none';
  }, 500);
}

function createFallingChar(input, char) {
  const colors = ['#a855f7', '#3b82f6', '#ec4899', '#06b6d4', '#c084fc'];
  input.style.transition = 'box-shadow 0.3s ease';
  input.style.boxShadow = '0 0 25px rgba(236,72,153,0.6), 0 0 60px rgba(6,182,212,0.3), inset 0 0 15px rgba(236,72,153,0.1)';
  setTimeout(() => {
    input.style.boxShadow = 'none';
  }, 600);
  for (let i = 0; i < 6; i++) {
    const el = document.createElement('span');
    el.textContent = char;
    const rect = input.getBoundingClientRect();
    el.style.cssText = `
      position:fixed;pointer-events:none;z-index:9999;
      font-size:${12 + Math.random() * 6}px;
      font-weight:700;font-family:'Comic Neue',sans-serif;
      color:${colors[Math.floor(Math.random() * colors.length)]};
      text-shadow:0 0 6px ${colors[Math.floor(Math.random() * colors.length)]};
      left:${rect.left + Math.random() * rect.width}px;
      top:${rect.top + rect.height / 2}px;
      opacity:1;
      transform:translateY(0);
      transition:all ${0.5 + Math.random() * 0.3}s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    `;
    document.body.appendChild(el);
    requestAnimationFrame(() => {
      el.style.transform = `translateY(${30 + Math.random() * 60}px) translateX(${(Math.random() - 0.5) * 20}px)`;
      el.style.opacity = '0';
    });
    setTimeout(() => el.remove(), 1000);
  }
}

function initInputEffects() {
  const inputs = document.querySelectorAll('input[type="text"], input[type="search"]');
  inputs.forEach(inp => {
    let prev = '';
    inp.addEventListener('focus', () => { prev = inp.value; });
    inp.addEventListener('input', () => {
      const val = inp.value;
      if (val.length > prev.length) {
        const typed = val.slice(prev.length);
        for (const ch of typed) createTypingChar(inp, ch);
      } else if (val.length < prev.length) {
        const deleted = prev.slice(val.length);
        for (const ch of deleted) createFallingChar(inp, ch);
      }
      prev = val;
    });
  });
}

function initModsPage() {
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.cat;
      browseOffset = 0;
      browseQuery = '';
      document.getElementById('mod-search').value = '';
      refreshBrowse(undefined, undefined, undefined, 0);
      refreshInstalled();
    });
  });
  document.getElementById('mod-sort')?.addEventListener('change', () => {
    browseOffset = 0;
    refreshBrowse(browseQuery || undefined, undefined, undefined, 0);
  });
  document.getElementById('mod-search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const activeTab = document.querySelector('#page-mods .tab-btn.active');
      const q = document.getElementById('mod-search').value.trim();
      if (activeTab?.dataset.tab === 'installed') {
        filterInstalled(q);
      } else {
        runBrowseSearch();
      }
    }
  });
  refreshBrowse(undefined, undefined, undefined, 0);
}

/* La búsqueda siempre empieza en la primera página y recuerda la consulta */
function runBrowseSearch() {
  browseQuery = document.getElementById('mod-search').value.trim();
  browseOffset = 0;
  refreshBrowse(browseQuery || undefined, undefined, undefined, 0);
}

function retryBrowseBtn() {
  return '<div class="pagination"><button class="btn-page" onclick="refreshBrowse(browseQuery || undefined, undefined, undefined, browseOffset)">↻ Reintentar</button></div>';
}

async function refreshBrowse(query, version, source, offset) {
  const container = document.getElementById('mods-browse');
  container.innerHTML = '<div class="loading">Loading...</div>';
  const selVersion = document.getElementById('mod-version');
  const selSource = document.getElementById('mod-source');
  const selSort = document.getElementById('mod-sort');
  let v = version || (selVersion ? selVersion.value : '');
  if (!v) {
    // El <select> de versiones se rellena de forma asíncrona: si aún está vacío
    // (primer arranque), se consulta la versión instalada para no pedir a
    // Modrinth una lista sin filtrar por versión.
    try { v = (await pywebview.api.get_settings()).version || ''; } catch (_) { /* ignore */ }
  }
  const s = source || (selSource ? selSource.value : 'modrinth');
  const sort = selSort ? selSort.value : 'downloads';
  const pt = currentCategory;
  const off = offset === undefined ? browseOffset : offset;
  try {
    let data;
    if (query) data = await pywebview.api.search_mods(query, v, s, pt, off, sort);
    else data = await pywebview.api.get_trending_mods(pt, off, sort);
    if (data.error) { container.innerHTML = `<div class="loading">Error: ${escapeHtml(data.error)}</div>${retryBrowseBtn()}`; return; }
    const mods = data.mods || [];
    const total = data.total_hits || 0;
    if (mods.length === 0) { container.innerHTML = `<div class="loading">No hay resultados para ${escapeHtml(v)}${query ? ' con "' + escapeHtml(query) + '"' : ''}.</div>${retryBrowseBtn()}`; return; }
    const installed = await pywebview.api.get_installed_mods(pt);
    const installedIds = new Set((installed.mods || []).filter(m => m.mod_id).map(m => m.mod_id));
    const hasPrev = off > 0;
    const hasNext = off + PAGE_SIZE < total;
    container.innerHTML = mods.map(m => `
      <div class="mod-card">
        <div class="mod-icon">
          ${m.thumbnail ? `<img src="${escapeHtml(m.thumbnail)}" alt="" />` : '📦'}
        </div>
        <div class="mod-info">
          <div class="name" style="cursor:pointer" onclick="showModDetail('${jsArg(m.mod_id)}')">${escapeHtml(m.name)}</div>
          <div class="desc">${escapeHtml((m.description || '').slice(0, 100))}${(m.description || '').length > 100 ? '...' : ''}</div>
          <div class="meta">v${escapeHtml(m.version || 'N/A')} · ${Number(m.downloads || 0).toLocaleString()} downloads</div>
        </div>
        ${installedIds.has(m.mod_id)
          ? `<button class="btn-sm installed" disabled>✓ Installed</button>`
          : `<button class="btn-sm install" onclick="installMod('${jsArg(m.mod_id)}','${jsArg(v)}','${jsArg(s)}','${jsArg(pt)}','${jsArg(m.thumbnail || '')}',this)">Download</button>`
        }
      </div>
    `).join('');
    container.innerHTML += `
      <div class="pagination">
        <button class="btn-page" onclick="goBrowsePage(-1)" ${hasPrev ? '' : 'disabled'}>← Previous</button>
        <span class="page-info">Page ${Math.floor(off / PAGE_SIZE) + 1} of ${Math.max(1, Math.ceil(total / PAGE_SIZE))}</span>
        <button class="btn-page" onclick="goBrowsePage(1)" ${hasNext ? '' : 'disabled'}>Next →</button>
      </div>`;
  } catch (e) {
    container.innerHTML = `<div class="loading">Error: ${escapeHtml(e)}</div>${retryBrowseBtn()}`;
  }
}

function goBrowsePage(dir) {
  browseOffset = Math.max(0, browseOffset + dir * PAGE_SIZE);
  refreshBrowse(browseQuery || undefined, undefined, undefined, browseOffset);
}

async function refreshInstalled() {
  const container = document.getElementById('mods-installed');
  try {
    const data = await pywebview.api.get_installed_mods(currentCategory);
    const mods = data.mods || [];
    container.dataset.all = JSON.stringify(mods);
    renderInstalled(mods);
  } catch (e) {
    container.innerHTML = `<div class="loading">Error: ${escapeHtml(e)}</div>`;
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
        ${m.thumbnail ? `<img src="${escapeHtml(m.thumbnail)}" alt="" />` : '📦'}
      </div>
      <div class="mod-info">
        <div class="name" ${m.mod_id ? `style="cursor:pointer" onclick="showModDetail('${jsArg(m.mod_id)}')"` : ''}>${escapeHtml(m.name)}</div>
        <div class="meta">${(Number(m.size || 0) / (1024*1024)).toFixed(2)} MB${m.project_type ? ' · '+escapeHtml(m.project_type) : ''}</div>
      </div>
      <button class="btn-sm delete" onclick="deleteMod('${jsArg(m.filename)}',this)">Delete</button>
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
    const res = await pywebview.api.download_mod(modId, version, source, projectType || currentCategory, thumbnail || '');
    if (res && res.ok === false) {
      btn.textContent = 'Error';
      btn.disabled = false;
      toast(res.error || 'No se pudo descargar', 'error');
      return;
    }
    toast('Descarga completada', 'success');
    refreshBrowse(browseQuery || undefined, undefined, undefined, browseOffset);
  } catch (e) {
    btn.textContent = 'Error';
    btn.disabled = false;
    toast(String(e), 'error');
  }
}

async function deleteMod(filename, btn) {
  btn.textContent = 'Deleting...';
  btn.disabled = true;
  try {
    const res = await pywebview.api.delete_mod(filename);
    if (res && res.ok === false) {
      btn.textContent = 'Error';
      btn.disabled = false;
      toast('No se pudo borrar el archivo', 'error');
      return;
    }
    refreshInstalled();
  } catch (e) {
    btn.textContent = 'Error';
    btn.disabled = false;
    toast(String(e), 'error');
  }
}

document.getElementById('mod-search-btn')?.addEventListener('click', () => {
  runBrowseSearch();
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
      javas.map(j => `<option value="${escapeHtml(j.path)}">${escapeHtml(j.version)} — ${escapeHtml(j.path)}</option>`).join('');
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
/* Desactiva las animaciones (estrellas, luna, transiciones) para equipos modestos.
   El fondo se sigue viendo: se pinta un fotograma estático y se para el bucle. */
function applySmoothRendering(enabled) {
  const off = !enabled;
  if (document.body.classList.contains('no-smooth') === off) return;
  document.body.classList.toggle('no-smooth', off);
  if (typeof window.__setBackgroundAnimating === 'function') window.__setBackgroundAnimating(!off);
  if (!off && typeof window.__restartMoon === 'function') window.__restartMoon();
}

/* Los campos de Ajustes reflejan la instancia activa (RAM, Java, carpeta del
   juego). Si no se refrescan al cambiar de instancia, guardar cualquier ajuste
   escribe los valores de la instancia anterior en la nueva: así acababa una
   instancia nueva apuntando a la carpeta de 'default'. */
async function refreshSettingsForm() {
  try {
    const settings = await pywebview.api.get_settings();
    const ram = Number(settings.ram) || 4;
    const slider = document.getElementById('ram-slider');
    if (slider) slider.value = ram;
    const ramValue = document.getElementById('ram-value');
    if (ramValue) ramValue.textContent = ram + ' GB';
    const javaPath = document.getElementById('java-path');
    if (javaPath) javaPath.value = settings.java_path || 'java';
    const mcDir = document.getElementById('mc-dir');
    if (mcDir) mcDir.value = settings.minecraft_dir || '~/.stellaclient';
  } catch (e) { console.error(e); }
}

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
    const smooth = settings.smooth_rendering !== false;
    document.getElementById('smooth-rendering').checked = smooth;
    applySmoothRendering(smooth);
    document.getElementById('smooth-rendering').addEventListener('change', (e) => {
      applySmoothRendering(e.target.checked);
      pywebview.api.save_settings(JSON.stringify({ smooth_rendering: e.target.checked }));
    });
    document.getElementById('ram-slider').addEventListener('input', (e) => {
      document.getElementById('ram-value').textContent = e.target.value + ' GB';
      pywebview.api.save_settings(JSON.stringify({ ram: parseInt(e.target.value) }));
    });
    document.getElementById('discord-rpc').checked = settings.discord_rpc !== false;
    document.getElementById('discord-rpc').addEventListener('change', (e) => {
      pywebview.api.save_settings(JSON.stringify({ discord_rpc: e.target.checked }));
    });
    document.getElementById('hw-accel').checked = settings.hw_accel !== false;
    document.getElementById('hw-accel').addEventListener('change', (e) => {
      pywebview.api.save_settings(JSON.stringify({ hw_accel: e.target.checked }));
      toast('Requires restart to take effect.', 'info');
    });
    await refreshSettingsForm();
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
    if (d.error) { body.innerHTML = `<div class="loading">Error: ${escapeHtml(d.error)}</div>`; return; }

    const installed = await pywebview.api.get_installed_mods();
    const isInstalled = installed.mods.some(m => m.mod_id === modId);
    const hasLinks = d.discord_url || d.issues_url || d.source_url || d.wiki_url || d.donation_urls?.length;
    const fmtDate = (s) => s ? new Date(s).toLocaleDateString() : 'N/A';

    body.innerHTML = `
      <div class="mod-detail-header">
        <div class="mod-detail-icon">
          ${d.thumbnail ? `<img src="${escapeHtml(d.thumbnail)}" alt="" />` : '📦'}
        </div>
        <div class="mod-detail-info">
          <h2>${escapeHtml(d.name)}</h2>
          <div class="stats">
            <span>Downloads: <strong>${(d.downloads || 0).toLocaleString()}</strong></span>
            <span>Followers: <strong>${(d.followers || 0).toLocaleString()}</strong></span>
          </div>
          ${d.license ? `<div class="stats"><span>License: <strong>${escapeHtml(d.license)}</strong></span></div>` : ''}
          ${d.loaders?.length ? `<div class="stats"><span>Loaders: <strong>${d.loaders.map(escapeHtml).join(', ')}</strong></span></div>` : ''}
          ${d.game_versions?.length ? `<div class="stats"><span>Game versions: <strong>${d.game_versions.map(escapeHtml).join(', ')}</strong></span></div>` : ''}
          ${d.categories?.length || d.additional_categories?.length ? `<div class="stats"><span>Categories: ${[...(d.categories||[]), ...(d.additional_categories||[])].map(c => '#'+escapeHtml(c)).join(' · ')}</span></div>` : ''}
          <div class="stats">
            <span>Published: <strong>${fmtDate(d.published)}</strong></span>
            <span>Updated: <strong>${fmtDate(d.updated)}</strong></span>
          </div>
          <div class="stats">
            <span>Client: <strong>${escapeHtml(d.client_side || 'N/A')}</strong></span>
            <span>Server: <strong>${escapeHtml(d.server_side || 'N/A')}</strong></span>
          </div>
          ${isInstalled
            ? '<button class="btn-sm installed" style="margin-top:10px" disabled>✓ Installed</button>'
            : '<button class="btn-primary" style="margin-top:10px" onclick="installMod(\'' + jsArg(modId) + '\',\'' + jsArg(document.getElementById('mod-version')?.value || '1.21.1') + '\',\'' + jsArg(document.getElementById('mod-source')?.value || 'modrinth') + '\',\'' + jsArg(currentCategory) + '\',\'' + jsArg(d.thumbnail || '') + '\',this); closeModDetail()">Download</button>'
          }
        </div>
      </div>

      ${d.gallery?.length ? `
        <div class="mod-detail-section">
          <h3>Screenshots</h3>
          <div class="mod-gallery">
            ${d.gallery.map(g => `
              <div class="mod-gallery-item">
                <img src="${escapeHtml(g.url)}" alt="${escapeHtml(g.title || '')}" loading="lazy" />
                ${g.description ? `<div class="mod-gallery-caption">${escapeHtml(g.description)}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${hasLinks ? `
        <div class="mod-detail-section">
          <h3>Links</h3>
          <div class="mod-links">
            ${d.discord_url ? `<a href="${escapeHtml(d.discord_url)}" target="_blank" class="mod-link">💬 Discord</a>` : ''}
            ${d.issues_url ? `<a href="${escapeHtml(d.issues_url)}" target="_blank" class="mod-link">🐛 Issues</a>` : ''}
            ${d.source_url ? `<a href="${escapeHtml(d.source_url)}" target="_blank" class="mod-link">📄 Source</a>` : ''}
            ${d.wiki_url ? `<a href="${escapeHtml(d.wiki_url)}" target="_blank" class="mod-link">📖 Wiki</a>` : ''}
            ${(d.donation_urls || []).map(du =>
              `<a href="${escapeHtml(du.url)}" target="_blank" class="mod-link">❤️ ${escapeHtml(du.platform)}</a>`
            ).join('')}
          </div>
        </div>
      ` : ''}

      <div class="mod-detail-section">
        <h3>Description</h3>
        <div class="mod-detail-desc">${escapeHtml(d.description || 'No description available.')}</div>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div class="loading">Error: ${escapeHtml(e)}</div>`;
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
  list.innerHTML = recent.map(ip => `<div class="server-recent-item" onclick="document.getElementById('server-ip').value='${jsArg(ip)}';checkServer()">🌐 ${escapeHtml(ip)}</div>`).join('');
}

async function checkServer() {
  const ip = document.getElementById('server-ip').value.trim();
  if (!ip) return;
  const result = document.getElementById('server-result');
  result.innerHTML = '<div class="loading">Checking...</div>';
  try {
    const d = await pywebview.api.get_server_info(ip);
    if (d.error) { result.innerHTML = `<div class="msg error">${escapeHtml(d.error)}</div>`; return; }
    const online = d.online;
    result.innerHTML = `
      <div class="server-card">
        <div class="icon">${online ? '🟢' : '🔴'}</div>
        <div class="info">
          <div class="name">${escapeHtml(d.hostname || ip)}</div>
          ${d.motd?.clean?.length ? `<div class="motd">${d.motd.clean.map(escapeHtml).join('<br>')}</div>` : ''}
          <div class="meta">${escapeHtml(d.version || 'Unknown')} · ${escapeHtml(d.protocol || '?')} protocol</div>
          ${online ? `<div class="players">👤 ${Number(d.players?.online || 0)}/${Number(d.players?.max || 0)} players</div>` : '<div class="players">🔴 Offline</div>'}
          ${d.players?.list?.length ? `<div class="players">Online: ${d.players.list.map(escapeHtml).join(', ')}</div>` : ''}
        </div>
      </div>`;
    const recent = JSON.parse(localStorage.getItem('recentServers') || '[]');
    const filtered = recent.filter(s => s !== ip);
    filtered.unshift(ip);
    localStorage.setItem('recentServers', JSON.stringify(filtered.slice(0, 10)));
    loadServerHistory();
  } catch (e) {
    result.innerHTML = `<div class="msg error">Error: ${escapeHtml(e)}</div>`;
  }
}


