/* ==========================================================
   OLIVIA Nightclubs — cœur client
   Store, API, routeur, temps réel (SSE), compteur, feedback.
   La vérité est côté serveur : le client ne fait qu'afficher.
   ========================================================== */

import * as pages from "./pages.js";
import { audio } from "./audio.js";

export { audio };

export const S = {
  state: null,
  route: { name: "city", params: {} },
  timeOffset: 0,
  sse: null,
  unread: 0,
  pendingTrades: 0,
  cache: {},
  lastTimerRefresh: 0,
  serviceQueue: [],
  serviceTimer: null,
  hiddenReports: [],
};

// ---------------- Format ----------------
export function money(v, opts = {}) {
  const n = Number(v || 0);
  const abs = Math.abs(n);
  const isInt = Number.isInteger(abs);
  let s = isInt
    ? abs.toLocaleString("fr-FR")
    : abs.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  s = s.replace(/ | /g, " ");
  const sign = n < 0 ? "-" : opts.sign && n > 0 ? "+" : "";
  return `${sign}${s} €`;
}
export function num(v) { return Number(v || 0).toLocaleString("fr-FR").replace(/ | /g, " "); }
export function pct(v, digits = 0) { const n = Number(v || 0) * 100; return `${n > 0 ? "+" : ""}${n.toFixed(digits)} %`; }
export function esc(s) { return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
export function now() { return Date.now() / 1000 + S.timeOffset; }
export function clock(ts) { const d = new Date(ts * 1000); return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }); }
export function dateTime(ts) { const d = new Date(ts * 1000); return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }) + " " + clock(ts); }
export function ago(ts) {
  const s = Math.max(0, now() - ts);
  if (s < 60) return "à l'instant";
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`;
  return `il y a ${Math.floor(s / 86400)} j`;
}
export function duration(s) {
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  if (h > 0) return `${h} h ${String(m).padStart(2, "0")} min`;
  if (m > 0) return `${m} min ${String(sec).padStart(2, "0")} s`;
  return `${sec} s`;
}
export function countdown(s) {
  s = Math.max(0, Math.floor(s));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

// ---------------- API ----------------
export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  if (res.status === 401) {
    S.state = null;
    disconnectSSE();
    render();
    throw { code: "AUTH", message: "Session expirée. Reconnectez-vous, patron." };
  }
  if (!res.ok) {
    throw { code: data?.error || "HTTP", message: data?.message || data?.detail || "Erreur serveur.", payload: data?.payload };
  }
  return data;
}

export function setState(state) {
  if (!state) return;
  S.state = state;
  if (state.server_time) S.timeOffset = state.server_time - Date.now() / 1000;
  if (typeof state.unread === "number") S.unread = state.unread;
  if (typeof state.pending_trades === "number") S.pendingTrades = state.pending_trades;
  renderTopbar();
}

export async function refresh(withRecap = false) {
  const state = await api(`/api/state${withRecap ? "?recap=1" : ""}`);
  setState(state);
  if (state.recap && state.recap.services > 0) showRecap(state.recap);
  return state;
}

/** Action de jeu : appelle l'API, met à jour l'état, anime la trésorerie. */
export async function act(path, body, { method = "POST", silent = false } = {}) {
  const before = S.state?.club?.cash ?? null;
  try {
    const data = await api(path, { method, body });
    const cashAfter = data?.club?.cash;
    setState(data);
    if (before !== null && typeof cashAfter === "number" && cashAfter !== before && !silent) flyMoney(cashAfter - before);
    return data.result ?? data;
  } catch (e) {
    if (!silent) toast({ icon: "♣", title: "Impossible", text: e.message, tone: "red" });
    throw e;
  }
}

// ---------------- Routeur ----------------
export function navigate(hash) { location.hash = hash; }

function parseRoute() {
  const h = location.hash.replace(/^#\/?/, "");
  const [name, ...rest] = h.split("/");
  return { name: name || "city", params: { id: rest[0], sub: rest[1] } };
}

export async function render() {
  const app = document.getElementById("app");
  if (!S.state) {
    app.innerHTML = "";
    pages.login(app);
    return;
  }
  if (!S.state.club) {
    app.innerHTML = "";
    pages.createClub(app);
    return;
  }
  S.route = parseRoute();
  const page = pages[S.route.name] || pages.city;
  // État local trop ancien (autre onglet, longue inactivité) → on le rafraîchit avant d'afficher.
  if (S.state.server_time && now() - S.state.server_time > 20) {
    try { await refresh(); } catch { return; }
  }
  if (!document.getElementById("view")) {
    app.innerHTML = `<div class="topbar" id="topbar"></div><nav class="mainnav" id="mainnav"></nav><main id="view"></main>`;
  }
  renderTopbar();
  renderNav();
  const view = document.getElementById("view");
  view.innerHTML = `<div class="muted small" style="padding:30px;text-align:center">Chargement…</div>`;
  // Contexte audio : seules les pages "Ma boîte" et "Visite" définissent une vue de club.
  if (!["club", "visit"].includes(S.route.name)) audio.setView(null);
  try {
    await page(view, S.route.params);
  } catch (e) {
    console.error(e);
    view.innerHTML = `<div class="panel accent-red"><h3>Erreur</h3><p>${esc(e.message || e)}</p></div>`;
  }
  window.scrollTo({ top: 0 });
}

// ---------------- Audio : préférences, manifeste, alerte braquage ----------------
export async function initAudio(state) {
  audio.onSave = (prefs) => api("/api/me/audio", { method: "PUT", body: { prefs } }).catch(() => {});
  audio.onStateChange = () => renderAudioControls();
  if (state?.user?.audio_prefs) audio.setPrefs(state.user.audio_prefs, { persist: false });
  try { audio.setManifest(await api("/api/audio/manifest")); } catch (e) { console.warn("audio manifest", e); }
  renderAudioControls();
}

export function renderAudioControls() {
  const el = document.getElementById("audio-controls");
  if (!el) return;
  const st = audio.status();
  el.innerHTML = `${st.blocked ? `<button class="btn sm gold" id="audio-unlock">🔊 Activer le son</button>` : ""}
    <button class="iconbtn" id="audio-mute" title="${st.muted ? "Réactiver le son" : "Couper le son"}">${st.muted ? "🔇" : "🔊"}</button>`;
  const unlock = el.querySelector("#audio-unlock");
  if (unlock) unlock.onclick = () => audio.unlock();
  el.querySelector("#audio-mute").onclick = () => { audio.toggleMute(); renderAudioControls(); };
}

export function showRobberyAlert(p) {
  const me = S.state?.user?.id;
  const ok = p.result === "SUCCESS";
  const who = p.attacker_id === me ? "Vous venez de braquer" : `${p.attacker_club} (${p.attacker_name}) vient de braquer`;
  const target = p.victim_id === me ? "votre boîte" : `${p.victim_club} (${p.victim_name})`;
  const el = document.createElement("div");
  el.className = "robbery-alert";
  el.innerHTML = `<div class="flash"></div><div class="rob-card">
    <div class="siren">🚨</div><div class="t">BRAQUAGE !</div>
    <div class="d">${esc(who)} ${esc(target)}.</div>
    <div class="r ${ok ? "gold" : "red"}">${ok ? `Coup réussi — ${money(p.amount)} envolés` : `Coup raté — ${money(p.amount)} perdus par le braqueur`}</div></div>`;
  document.body.appendChild(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 500); }, 3600);
}

export function renderTopbar() {
  const el = document.getElementById("topbar");
  if (!el || !S.state?.club) return;
  const c = S.state.club, d = S.state.derived;
  const statusTone = { "COMPLET": "gold", "TRÈS ACTIF": "green", "SHOWCASE EN COURS": "violet", "ÉVÉNEMENT EN COURS": "red", "CALME": "", "OUVERT": "cyan" }[d.status] || "";
  el.innerHTML = `
    <div class="brand" onclick="location.hash='#/city'"><span class="logo">OLIVIA</span><span class="sub">Nightclubs</span></div>
    <div class="stats-strip">
      <div class="stat-chip cash" id="chip-cash"><span class="k">Trésorerie</span><span class="v">${money(c.cash)}</span></div>
      <div class="stat-chip"><span class="k">Clients</span><span class="v">${num(c.last_clients)}</span></div>
      <div class="stat-chip"><span class="k">VIP</span><span class="v">${num(c.last_vips)}</span></div>
      <div class="stat-chip"><span class="k">Niveau</span><span class="v">${c.level} · ${esc(d.level_name)}</span></div>
      <div class="stat-chip status"><span class="k">Statut</span><span class="v ${statusTone}">${esc(d.status)}</span></div>
      <div class="stat-chip timer"><span class="k">Prochain service</span><span class="v" id="timer">--:--</span></div>
    </div>
    <div class="icons">
      <span id="audio-controls" class="row" style="gap:6px"></span>
      <button class="iconbtn" title="Banque & trades" onclick="location.hash='#/bank'">🏦${S.pendingTrades ? `<span class="badge">${S.pendingTrades}</span>` : ""}</button>
      <button class="iconbtn" title="Notifications" onclick="location.hash='#/notifications'">🔔${S.unread ? `<span class="badge">${S.unread > 99 ? "99+" : S.unread}</span>` : ""}</button>
      <button class="iconbtn" title="Profil" onclick="location.hash='#/profile/${S.state.user.id}'">${esc(S.state.user.avatar)}</button>
      <button class="iconbtn" title="Paramètres" onclick="location.hash='#/settings'">⚙</button>
    </div>`;
  renderAudioControls();
  tickTimer();
}

const NAV = [
  ["city", "🏙️ Ville"], ["club", "♣ Ma boîte"], ["dashboard", "Direction"], ["finances", "Finances"],
  ["showcases", "Showcases"], ["equipment", "Équipements"], ["manager", "Manager"], ["activities", "Activités"],
  ["shop", "Boutique"], ["bank", "Banque"], ["leaderboard", "Classement"], ["settings", "Paramètres"],
];
function renderNav() {
  const el = document.getElementById("mainnav");
  if (!el) return;
  const cur = S.route.name;
  el.innerHTML = NAV.map(([k, l]) => `<a href="#/${k}" class="${cur === k ? "active" : ""}">${l}</a>`).join("")
    + (S.state.user.is_admin ? `<a href="#/admin" class="${cur === "admin" ? "active" : ""}">⚙ Admin</a>` : "")
    + `<a href="#" id="logout" style="margin-left:auto">Déconnexion</a>`;
  el.querySelector("#logout").onclick = async (e) => {
    e.preventDefault();
    await api("/api/auth/logout", { method: "POST" });
    audio.setView(null);
    S.state = null; disconnectSSE(); location.hash = ""; render();
  };
}

// ---------------- Compteur ----------------
function tickTimer() {
  const el = document.getElementById("timer");
  if (!el || !S.state?.derived) return;
  const remaining = S.state.derived.next_service - now();
  el.textContent = countdown(remaining);
  if (remaining <= -2 && Date.now() - S.lastTimerRefresh > 6000) {
    S.lastTimerRefresh = Date.now();
    refresh().then(() => { if (pageWantsLiveRefresh()) render(); }).catch(() => {});
  }
  const bigTimer = document.getElementById("big-timer");
  if (bigTimer) bigTimer.textContent = countdown(remaining);
  const bigBar = document.getElementById("big-timer-bar");
  if (bigBar) {
    const tick = S.state.config.tick_seconds;
    bigBar.style.width = `${Math.max(0, Math.min(100, (1 - remaining / tick) * 100))}%`;
  }
}
setInterval(tickTimer, 1000);
function pageWantsLiveRefresh() { return ["dashboard", "club", "city"].includes(S.route.name); }

// ---------------- Feedback ----------------
export function toast({ icon = "♣", title = "", text = "", tone = "", ttl = 5000 }) {
  const box = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${tone}`;
  el.innerHTML = `<div class="i">${icon}</div><div><div class="t">${esc(title)}</div>${text ? `<div class="d">${esc(text)}</div>` : ""}</div>`;
  box.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .4s"; setTimeout(() => el.remove(), 400); }, ttl);
}

export function flyMoney(delta) {
  const chip = document.getElementById("chip-cash");
  const rect = chip ? chip.getBoundingClientRect() : { left: window.innerWidth - 120, top: 60 };
  const el = document.createElement("div");
  el.className = `flyer ${delta < 0 ? "neg" : "pos"}`;
  el.textContent = money(delta, { sign: true });
  el.style.left = `${rect.left}px`; el.style.top = `${rect.top + 30}px`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1500);
}

export function overlay(html, { cls = "", closable = true } = {}) {
  const el = document.createElement("div");
  el.className = `overlay ${cls}`;
  el.innerHTML = `<div class="box">${html}</div>`;
  const close = () => el.remove();
  if (closable) el.addEventListener("click", (e) => { if (e.target === el) close(); });
  el.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  document.getElementById("overlays").appendChild(el);
  return close;
}

export function confirmBox({ title, html, okLabel = "Confirmer", tone = "gold" }) {
  return new Promise((resolve) => {
    const close = overlay(`<h2>${esc(title)}</h2><div style="margin:14px 0">${html}</div>
      <div class="row" style="justify-content:flex-end"><button class="btn ghost" data-close>Annuler</button><button class="btn ${tone}" id="ok">${esc(okLabel)}</button></div>`);
    const box = document.getElementById("overlays").lastElementChild;
    box.querySelector("#ok").onclick = () => { close(); resolve(true); };
    box.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => resolve(false)));
    box.addEventListener("click", (e) => { if (e.target === box) resolve(false); });
  });
}

export function showServiceOverlay(reports) {
  const sum = (k) => reports.reduce((a, r) => a + (r[k] || 0), 0);
  const last = reports[reports.length - 1];
  const multi = reports.length > 1;
  const showcase = reports.map((r) => r.showcase).filter(Boolean).pop();
  const combos = reports.flatMap((r) => r.combos || []);
  const fun = last.fun_event;
  const html = `
    <div class="kicker center">${multi ? `${reports.length} services terminés` : `Service #${last.service_no} terminé`}</div>
    <h2>SERVICE TERMINÉ</h2>
    <div class="big">+${num(sum("clients"))} CLIENTS</div>
    <div class="lines">
      <div class="line"><span>🍸 Bar</span><b class="gold">${money(sum("bar"), { sign: true })}</b></div>
      <div class="line"><span>🎟️ Entrées</span><b class="gold">${money(sum("entry"), { sign: true })}</b></div>
      <div class="line"><span>👑 VIP (${num(sum("vips"))})</span><b class="gold">${money(sum("vip"), { sign: true })}</b></div>
      ${sum("salary") ? `<div class="line"><span>♣ Salaire manager</span><b class="red">${money(-sum("salary"))}</b></div>` : ""}
      <div class="line" style="border:1px solid var(--gold);background:var(--gold-dim)"><span><b>TOTAL</b></span><b class="gold" style="font-size:20px">${money(sum("total"), { sign: true })}</b></div>
    </div>
    ${showcase ? `<div class="notice gold"><b>🎤 Showcase — ${esc(showcase.artist)}</b><br>${esc(showcase.text)}<br><b>${showcase.clients >= 0 ? "+" : ""}${num(showcase.clients)} clients</b></div>` : ""}
    ${fun ? `<div class="notice" style="margin-top:8px"><b>${esc(fun.title)}</b><br>${esc(fun.text)}</div>` : ""}
    <div class="row" style="justify-content:center;margin-top:16px"><button class="btn gold" data-close>Continuer</button></div>`;
  overlay(html, { cls: "service" });
  if (combos.length) setTimeout(() => { showCombo(combos[0]); audio.playUi("combo"); }, 400);
}

export function showCombo(comboId) {
  const cfg = S.state?.config;
  const name = comboId === "coca_lagui" ? "Coca Cherry × Lagui" : comboId === "boro_saisai" ? "Boro 700 × Saisai" : comboId;
  overlay(`<h2>🔥 COMBO DÉCLENCHÉ</h2><div class="big" style="color:var(--red2);font-size:30px">${esc(name)}</div>
    <div class="lines">
      <div class="line"><span>👥 Bonus clients</span><b class="green">x2</b></div>
      <div class="line"><span>🎟️ Bonus entrées</span><b class="green">${comboId === "coca_lagui" ? "+25 %" : "+20 %"}</b></div>
      <div class="line"><span>🍸 Bonus bar</span><b class="green">${comboId === "coca_lagui" ? "+20 %" : "+15 %"}</b></div>
      <div class="line"><span>👑 Bonus VIP</span><b class="green">${comboId === "coca_lagui" ? "+2 VIP" : "+1 VIP"}</b></div>
    </div>
    <p class="center muted small">Combo secret découvert — il figure désormais dans votre bureau des showcases.</p>
    <div class="row" style="justify-content:center"><button class="btn red" data-close>La salle explose</button></div>`, { cls: "combo" });
  void cfg;
}

export function showRecap(r) {
  overlay(`
    <div class="kicker center">Pendant votre absence (${duration(r.away_seconds)})</div>
    <h2>BON RETOUR, PATRON.</h2>
    <div class="big">${r.services} SERVICE${r.services > 1 ? "S" : ""}</div>
    <div class="lines">
      <div class="line"><span>👥 Clients</span><b>+${num(r.clients)}</b></div>
      <div class="line"><span>👑 VIP</span><b>+${num(r.vips)}</b></div>
      <div class="line"><span>💶 Revenus</span><b class="gold">${money(r.income, { sign: true })}</b></div>
      <div class="line"><span>💸 Dépenses</span><b class="red">${money(-r.expenses)}</b></div>
      <div class="line"><span>🚨 Événements</span><b>${r.events}</b></div>
      <div class="line"><span>🎤 Showcases</span><b>${r.showcases}</b></div>
      <div class="line" style="border:1px solid var(--gold);background:var(--gold-dim)"><span><b>Bénéfice net</b></span><b class="${r.net >= 0 ? "gold" : "red"}" style="font-size:20px">${money(r.net, { sign: true })}</b></div>
    </div>
    <div class="row" style="justify-content:center"><button class="btn gold" data-close>Reprendre la direction</button></div>`);
}

export function showEventBanner(ev) {
  const good = /influenceur|vip/i.test(ev.title || "");
  const el = document.createElement("div");
  el.className = `event-banner ${good ? "good" : ""}`;
  el.innerHTML = `<div class="i">${good ? "✨" : "🚨"}</div><div><div class="t">${esc(ev.title)}</div><div class="d">${esc(ev.text)}</div>${ev.cash_delta ? `<div class="red num" style="font-size:18px">${money(ev.cash_delta)}</div>` : ""}</div>
    <button class="btn sm ghost" style="margin-left:auto" onclick="location.hash='#/notifications';this.parentElement.remove()">Voir</button>`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 9000);
}

// ---------------- Temps réel ----------------
export function connectSSE() {
  disconnectSSE();
  const es = new EventSource("/api/events");
  S.sse = es;
  es.addEventListener("service", (e) => {
    const r = JSON.parse(e.data);
    if (document.hidden) { S.hiddenReports.push(r); return; } // récap unique au retour
    S.serviceQueue.push(r);
    clearTimeout(S.serviceTimer);
    S.serviceTimer = setTimeout(async () => {
      const reports = S.serviceQueue.splice(0);
      try { await refresh(); } catch {}
      showServiceOverlay(reports);
      audio.playUi("cash");
      if (pageWantsLiveRefresh() || S.route.name === "finances") render();
    }, 700);
  });
  es.addEventListener("event", (e) => {
    const ev = JSON.parse(e.data);
    showEventBanner(ev);
    audio.playEvent(/influenceur|vip/i.test(ev.title || "") ? "good" : "alert");
    refresh().catch(() => {});
  });
  es.addEventListener("notification", (e) => {
    const n = JSON.parse(e.data);
    S.unread += 1; renderTopbar();
    if (["transfer", "bottle", "trade", "robbery", "admin"].includes(n.kind)) {
      toast({ icon: n.icon, title: n.title, text: n.text, tone: n.kind === "robbery" ? "red" : "gold", ttl: 8000 });
      audio.playUi(n.kind === "bottle" ? "bottle" : "notify");
      refresh().then(() => { if (["bank", "dashboard", "club"].includes(S.route.name)) render(); }).catch(() => {});
    }
  });
  // ---- Événements audio validés par le serveur ----
  // ROBBERY_CREATED : GLOBAL — tous les joueurs connectés (braqueur compris) : FX + notification synchronisés.
  es.addEventListener("robbery_created", (e) => {
    const p = JSON.parse(e.data);
    showRobberyAlert(p);
    audio.playRobbery();
  });
  // SHOWCASE_STARTED / ENDED : LOCAL — le client ne joue que si activeClubView === club_id.
  const onShowcaseEvent = (p, started) => {
    if (started) audio.onShowcaseStarted(p); else audio.onShowcaseEnded(p);
    const mine = p.club_id === S.state?.user?.id;
    const viewing = S.route.name === "visit" && Number(S.route.params.id) === p.club_id;
    if (mine) refresh().then(() => { if (["club", "dashboard", "showcases"].includes(S.route.name)) render(); }).catch(() => {});
    else if (viewing) render();
  };
  es.addEventListener("showcase_started", (e) => onShowcaseEvent(JSON.parse(e.data), true));
  es.addEventListener("showcase_ended", (e) => onShowcaseEvent(JSON.parse(e.data), false));
  es.addEventListener("showcase_changed", (e) => { audio.onShowcaseStarted(JSON.parse(e.data)); });
  es.addEventListener("audio_manifest", () => { api("/api/audio/manifest").then((m) => audio.setManifest(m)).catch(() => {}); });
  es.addEventListener("trade", () => { S.pendingTrades += 1; renderTopbar(); if (S.route.name === "bank") render(); });
  es.addEventListener("refresh", () => { refresh().then(() => render()).catch(() => {}); });
  es.addEventListener("city", (e) => {
    if (document.hidden) return;
    const changed = (JSON.parse(e.data).changed || []);
    if (["city", "leaderboard"].includes(S.route.name)) render();
    else if (S.route.name === "dashboard" && !changed.includes(S.state?.user?.id)) render();
  });
  es.addEventListener("feed", (e) => {
    const f = JSON.parse(e.data);
    const box = document.getElementById("city-feed");
    if (box) box.insertAdjacentHTML("afterbegin", pages.feedItem(f));
  });
  es.onerror = () => { /* EventSource se reconnecte seul */ };
}
export function disconnectSSE() { if (S.sse) { S.sse.close(); S.sse = null; } }

// ---------------- Boot ----------------
window.addEventListener("hashchange", () => render());
document.addEventListener("visibilitychange", () => {
  if (document.hidden || !S.state) return;
  const reports = S.hiddenReports.splice(0);
  refresh(reports.length === 0).then(() => {
    if (reports.length) showServiceOverlay(reports);
    if (pageWantsLiveRefresh() || S.route.name === "finances") render();
  }).catch(() => {});
});

(async function boot() {
  audio.init();
  window.olivia = { S, audio, refresh, render };   // accès console pour le débogage
  try {
    const state = await api("/api/state?recap=1");
    setState(state);
    connectSSE();
    initAudio(state);
    if (state.recap && state.recap.services > 0) showRecap(state.recap);
  } catch { S.state = null; }
  render();
})();

export function afterLogin(state) {
  setState(state);
  connectSSE();
  initAudio(state);
  location.hash = "#/city";
  render();
  if (state.recap && state.recap.services > 0) showRecap(state.recap);
}
