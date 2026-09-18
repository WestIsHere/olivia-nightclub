/* ==========================================================
   Pages du jeu. Chaque page : async (root, params) => void
   ========================================================== */

import { S, api, act, refresh, render, money, num, pct, esc, now, clock, dateTime, ago, countdown, toast, overlay, confirmBox, afterLogin, navigate, renderTopbar, audio } from "./app.js";
import { renderScene, LEVEL_THEMES } from "./scene.js";

import { icon, pageNotes } from "./design.js";

// ---------------- helpers ----------------
const cfg = () => S.state.config;
const myClub = () => S.state.club;
const derived = () => S.state.derived;

function head(title, sub, right = "") {
  return `<header class="page-head"><div><div class="kicker">OLIVIA <span>/</span> ${esc(sub || "")}</div><h1>${title}</h1><p>${pageNotes[S.route.name] || "La nuit vous appartient."}</p></div><div class="row page-actions">${right}</div><div class="page-emblem">${icon(S.route.name)}</div></header>`;
}
function levelPill(level, name) {
  const t = LEVEL_THEMES[Math.min(6, level)];
  return `<span class="pill" style="color:${t.neon};border-color:${t.glow}66;background:${t.glow}1a">${t.symbol || "•"} ${esc(name)}</span>`;
}
function statusPill(status) {
  const tone = { "COMPLET": "gold", "TRÈS ACTIF": "green", "SHOWCASE EN COURS": "violet", "ÉVÉNEMENT EN COURS": "red", "CALME": "", "OUVERT": "cyan" }[status] || "";
  return `<span class="pill ${tone}"><span class="dot"></span>${esc(status)}</span>`;
}
function bestCarName(c) {
  const cars = cfg().shop.cars;
  let best = null;
  for (const id of c.cars || []) { const it = cars[id]; if (it && (!best || it.price > best.price)) best = it; }
  return best ? best.name : null;
}
function sceneBlock(c, { chips = true, tag = true } = {}) {
  const d = derived();
  const view = { ...c, user_id: S.state.user.id, occupancy: d.occupancy, status: d.status, last_event: c.last_event };
  return `<div class="scene-wrap club-cinematic"><div class="cinematic-title"><div class="eyebrow">VOTRE ADRESSE · NIVEAU ${c.level}</div><h2>${esc(c.name)}</h2><span class="night-signature">More than a night</span></div>
    ${tag ? `<div class="scene-tag">${statusPill(d.status)}${levelPill(c.level, d.level_name)}${c.showcase_pending ? `<span class="pill violet">🎤 ${esc(c.showcase_artist)}</span>` : ""}</div>` : ""}
    ${chips ? `<div class="scene-overlay">
      <div class="chip">Clients<b>${num(c.last_clients)}</b></div>
      <div class="chip">Occupation<b>${Math.round(d.occupancy * 100)} %</b></div>
      <div class="chip gold">Revenu / service<b>${money(c.last_income)}</b></div>
      <div class="chip">Prochain service<b id="big-timer">${countdown(d.next_service - now())}</b></div>
    </div>` : ""}
  </div><details class="facade-details"><summary>Voir la façade et ses améliorations <span>+</span></summary>${renderScene(view, { config: cfg(), levelName: d.level_name, serverTime: now(), carName: bestCarName(c) })}</details>`;
}
function designCarIcon() { return icon("car"); }
function designWatchIcon() { return icon("watch"); }
function stars(bonus) { const n = Math.max(1, Math.min(5, Math.round(bonus * 5))); return "★".repeat(n) + "☆".repeat(5 - n); }
function txLabel(kind) {
  return { service: "Service", salary: "Salaire", event: "Événement", upgrade: "Amélioration", equipment: "Équipement", showcase: "Showcase",
    activity: "Activité", blackjack: "Blackjack", shop_buy: "Achat", shop_sell: "Revente", btc_buy: "Bitcoin", btc_sell: "Bitcoin",
    transfer_out: "Transfert envoyé", transfer_in: "Transfert reçu", bottle_out: "Pack envoyé", bottle_in: "Pack reçu",
    trade_out: "Trade", trade_in: "Trade", robbery: "Braquage", admin: "Administration" }[kind] || kind;
}
export function feedItem(f) {
  return `<div class="feed-item ${esc(f.kind)}"><span class="t">${clock(f.ts)}</span><span class="i">${esc(f.icon)}</span><span>${esc(f.text)}</span></div>`;
}
function playerSelect(players, id = "target", selected = null) {
  return `<select id="${id}">${players.map((p) => `<option value="${p.user_id}" ${String(p.user_id) === String(selected) ? "selected" : ""}>${esc(p.club)} — ${esc(p.display_name)} (niv. ${p.level})</option>`).join("")}</select>`;
}

// ==========================================================
// LOGIN
// ==========================================================
export function login(root) {
  root.innerHTML = `<div class="login-hero"><header class="landing-nav"><a class="brand" href="#"><span class="logo">OLIVIA</span><span class="sub">NIGHTCLUB</span></a><span class="landing-manifesto">MUSIC <i>·</i> PEOPLE <i>·</i> MEMORIES</span><a class="btn ghost" href="#f-login">Se connecter ${icon("arrow")}</a></header><div class="login-box">
    <section class="login-visual"><div class="caption"><div class="eyebrow">VOTRE VILLE. VOTRE CLUB. VOTRE HISTOIRE.</div><h1>OLIVIA</h1><div class="wordmark-sub">NIGHTCLUB</div><div class="night-signature">More than a night</div><p>Des soirées inoubliables.<br>Un empire de la nuit à construire.</p><div class="login-tags"><span>${icon("music")} Showcases live</span><span>${icon("levels")} Adresses d’exception</span><span>${icon("profile")} Joueurs réels</span></div></div></section>
    <section class="panel login-form"><div class="eyebrow">VOTRE INVITATION POUR CE SOIR</div><h2>La nuit vous attend.</h2><p class="muted small">Entrez dans votre club et écrivez la suite.</p>
      <div class="tabs"><button class="on" data-tab="login">Connexion</button><button data-tab="register">Créer ma boîte</button></div>
      <form id="f-login">
        <div class="field"><label>Utilisateur</label><input name="username" autocomplete="username" required></div>
        <div class="field"><label>Mot de passe</label><input name="password" type="password" autocomplete="current-password" required></div>
        <button class="btn gold block lg">Entrer dans le club ${icon("arrow")}</button><div class="error" id="err-login"></div>
      </form>
      <form id="f-register" class="hidden">
        <div class="field"><label>Utilisateur</label><input name="username" autocomplete="username" required placeholder="3 à 24 caractères"></div>
        <div class="field"><label>Nom affiché</label><input name="display_name" placeholder="Votre nom de patron"></div>
        <div class="field"><label>Mot de passe</label><input name="password" type="password" autocomplete="new-password" required placeholder="6 caractères minimum"></div>
        <div class="field"><label>Nom de la boîte de nuit</label><input name="club_name" required placeholder="Ex : Le Noir, Olivia Club, 700…" maxlength="40"></div>
        <label id="local-admin-option" class="local-admin-option hidden"><input name="local_admin" type="checkbox"> Activer mon accès administrateur sur cet ordinateur</label>
        <button class="btn gold block lg">Créer mon établissement ${icon("arrow")}</button><div class="error" id="err-register"></div>
      </form>
    </section></div><footer class="landing-footer"><span>OLIVIA NIGHTCLUB</span><span>Votre club continue de vivre, même hors-ligne.</span><span>Music · People · Memories</span></footer></div>`;
  api("/api/auth/local-admin").then(({ available }) => {
    root.querySelector("#local-admin-option")?.classList.toggle("hidden", !available);
  }).catch(() => {});
  root.querySelector('.landing-nav a[href="#f-login"]').onclick = (e) => {
    e.preventDefault();
    root.querySelector('[data-tab="login"]').click();
    root.querySelector('#f-login input[name="username"]').focus();
  };
  root.querySelectorAll(".tabs button").forEach((b) => b.onclick = () => {
    root.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("on", x === b));
    root.querySelector("#f-login").classList.toggle("hidden", b.dataset.tab !== "login");
    root.querySelector("#f-register").classList.toggle("hidden", b.dataset.tab !== "register");
  });
  for (const kind of ["login", "register"]) {
    root.querySelector(`#f-${kind}`).onsubmit = async (e) => {
      e.preventDefault();
      const body = Object.fromEntries(new FormData(e.target).entries());
      const err = root.querySelector(`#err-${kind}`); err.textContent = "";
      try { afterLogin(await api(`/api/auth/${kind}`, { method: "POST", body })); }
      catch (ex) { err.textContent = ex.message; }
    };
  }
}

export function createClub(root) {
  root.innerHTML = `<div class="login-hero create-club-screen"><div class="brand"><span class="logo">OLIVIA</span><span class="sub">NIGHTCLUB</span></div><div class="panel accent-gold" style="width:min(480px,100%)">
    <div class="kicker">Un nouveau chapitre</div><h2>Votre prochaine légende.</h2>
    <p class="muted small">Vous n’avez pas encore d’établissement. Choisissez son nom et faites votre entrée dans la nuit.</p>
    <form id="f"><div class="field"><label>Nom de la boîte</label><input name="club_name" required maxlength="40"></div>
    <button class="btn gold block">♣ Créer ma boîte</button><div class="error" id="err"></div></form>
    <div class="divider"></div><a href="#" id="logout" class="small">Déconnexion</a></div></div>`;
  root.querySelector("#f").onsubmit = async (e) => {
    e.preventDefault();
    try { const st = await api("/api/club/create", { method: "POST", body: { club_name: e.target.club_name.value } }); afterLogin(st); }
    catch (ex) { root.querySelector("#err").textContent = ex.message; }
  };
  root.querySelector("#logout").onclick = async (e) => { e.preventDefault(); await api("/api/auth/logout", { method: "POST" }); S.state = null; location.hash = ""; location.reload(); };
}

// ==========================================================
// VILLE
// ==========================================================
export async function city(root) {
  const data = await api("/api/city");
  const me = S.state.user.id;
  const clubs = data.clubs.slice().sort((a, b) => a.slot - b.slot);
  const perRow = 4;
  const rows = [];
  for (let i = 0; i < Math.max(clubs.length, 1); i += perRow) rows.push(clubs.slice(i, i + perRow));
  const top = clubs.slice().sort((a, b) => b.cash - a.cash || b.level - a.level).slice(0, 5);
  root.innerHTML = `
    <section class="city-head"><div class="city-hero-copy"><div class="eyebrow"><span class="live-dot"></span> LA VILLE S’ÉVEILLE</div><h1>La nuit<br>vous appartient.</h1><div class="night-signature">More than a night</div><p>Des adresses, des rencontres, des nuits à inventer.<br>Faites de votre club une légende.</p><div class="row"><a class="btn gold lg" href="#/club">Entrer dans mon club ${icon("arrow")}</a><a class="btn ghost lg" href="#/showcases">Les artistes à l’affiche</a></div></div><div class="city-hero-mark">OLIVIA<span>N I G H T C L U B</span></div><div class="hero-bottom"><span>${clubs.length} établissement${clubs.length > 1 ? "s" : ""} en ville</span><span>MUSIC · PEOPLE · MEMORIES</span><span>LA NUIT, ENSEMBLE</span></div></section>
    <div class="section-heading"><div><div class="eyebrow">LE CARNET D’ADRESSES</div><h2>Ce soir en ville</h2></div><a class="text-link" href="#/leaderboard">Découvrir le classement ${icon("arrow")}</a></div>
    <div class="grid" style="grid-template-columns: minmax(0, 1fr) 320px">
      <div id="streets">
        ${rows.map((row, ri) => `<div class="street">${row.map((c) => clubCard(c, me, data.server_time)).join("")}</div>`).join("")}
      </div>
      <div>
        <div class="panel tight"><div class="kicker">Ce soir en ville</div>
          <div class="list" style="margin-top:8px">${top.map((c, i) => `<div class="competitor" onclick="location.hash='#/${c.user_id === me ? "club" : "visit/" + c.user_id}'"><span class="rank-medal">${["🥇", "🥈", "🥉"][i] || `<span class="rank-n">#${i + 1}</span>`}</span><div><div class="n">${esc(c.name)}</div><div class="m">${esc(c.level_name)} · ${money(c.cash)}</div></div><span class="spacer"></span>${c.online ? `<span class="pill green"><span class="dot"></span>en ligne</span>` : ""}</div>`).join("")}</div>
          <a href="#/leaderboard" class="btn sm ghost block" style="margin-top:8px">Classement complet</a></div>
        <div class="panel tight" style="margin-top:14px"><div class="kicker">Actualités de la nuit</div>
          <div class="feed" id="city-feed" style="margin-top:8px">${data.feed.length ? data.feed.map(feedItem).join("") : `<div class="muted small">La nuit commence à peine…</div>`}</div></div>
      </div>
    </div>`;
  if (window.innerWidth < 900) root.querySelector(".grid").style.gridTemplateColumns = "1fr";
}

function clubCard(c, me, serverTime) {
  const mine = c.user_id === me;
  return `<a class="club-card ${mine ? "mine" : ""}" href="#/${mine ? "club" : "visit/" + c.user_id}"><div class="club-cover" style="background-position:${20 + (c.slot * 23) % 70}% center"><span class="cover-label">${mine ? "VOTRE ÉTABLISSEMENT" : "OLIVIA COLLECTION"}</span><span class="club-monogram">${esc(c.name.slice(0, 1))}</span></div>
    <div class="plaque"><div><div class="n">${LEVEL_THEMES[c.level].symbol || "•"} ${esc(c.name)}</div><div class="o">${esc(c.owner)}${mine ? " · vous" : ""}</div></div>
      <div><div class="c">${money(c.cash)}</div><div class="p">👤 ${num(c.last_clients)} clients · ${money(c.entry_price)}</div></div></div>
    <div class="foot">${statusPill(c.status)}${levelPill(c.level, c.level_name)}</div>
  </a>`;
}

// ==========================================================
// MA BOÎTE (menu radial)
// ==========================================================
export async function club(root) {
  const c = myClub(), d = derived();
  const items = [
    ["dashboard", "♣", "Direction", "Vue générale"], ["finances", "💶", "Finances", "Registre"], ["showcases", "🎤", "Showcases", d.artist_costs ? "Artistes" : ""],
    ["equipment", "🔊", "Équipements", `${c.equipment.length}/${Object.keys(cfg().equipment).length}`], ["manager", "♠", "Manager", d.manager ? d.manager.name : "Aucun"],
    ["activities", "🃏", "Activités", "Blackjack…"], ["shop", "🚘", "Boutique", "Voitures · Montres · BTC"], ["bank", "🏦", "Banque", "Transferts · Trades"], ["levels", "📈", "Statistiques", "Progression"],
  ];
  const R = 480, cy = 520;
  root.innerHTML = `
    ${head(esc(c.name), "Ma boîte", `<button class="btn sm ghost" id="rename">✏️ Renommer</button><a class="btn sm ghost" href="#/dashboard">Direction</a>`)}
    ${sceneBlock(c)}
    <div class="radial-wrap"><div class="radial">${items.map(([k, i, l, s], idx) => {
      const a = (210 + (120 / (items.length - 1)) * idx) * Math.PI / 180;
      return `<a href="#/${k}" style="--rx:${(R * Math.cos(a)).toFixed(0)}px;--ry:${(cy + R * Math.sin(a)).toFixed(0)}px"><span class="i">${icon(k)}</span><span class="l">${l}</span><span class="s">${esc(s)}</span></a>`;
    }).join("")}</div></div>
    <div class="grid three" style="margin-top:14px">
      <div class="panel tight"><div class="kicker">Showcase</div>${c.showcase_pending ? `<div><b>🎤 ${esc(c.showcase_artist)}</b> — actif sur le prochain service</div>` : `<div class="muted">🥀 Aucun showcase en attente.</div>`}${c.last_showcase_event ? `<div class="small muted" style="margin-top:6px">Dernier : ${esc(c.last_showcase_event.artist)} (${c.last_showcase_event.clients >= 0 ? "+" : ""}${c.last_showcase_event.clients} clients)</div>` : ""}</div>
      <div class="panel tight"><div class="kicker">Manager</div>${d.manager ? `<div><b>${esc(d.manager.name)}</b> — niveau ${d.manager.level}</div><div class="small muted">${money(d.manager.salary)} / service</div>` : `<div class="muted">Aucun manager embauché.</div>`}</div>
      <div class="panel tight"><div class="kicker">Dernier événement</div>${c.last_event ? `<div><b>${esc(c.last_event.title)}</b></div><div class="small muted">${esc(c.last_event.text)}</div>` : `<div class="muted">Nuit calme pour l'instant.</div>`}</div>
    </div>`;
  // Contexte audio : je suis dans la vue de MON club → ambiance + showcase de ce club uniquement.
  audio.setView({ clubId: S.state.user.id, level: c.level, showcase: S.state.showcase_screen });
  root.querySelector("#rename").onclick = async () => {
    const close = overlay(`<h2>Renommer votre boîte</h2><div class="field" style="margin-top:14px"><label>Nouveau nom</label><input id="nn" value="${esc(c.name)}" maxlength="40"></div><div class="row" style="justify-content:flex-end"><button class="btn ghost" data-close>Annuler</button><button class="btn gold" id="ok">Renommer</button></div>`);
    document.getElementById("ok").onclick = async () => { try { await act("/api/club/rename", { name: document.getElementById("nn").value }); close(); toast({ icon: "✏️", title: "Boîte renommée", tone: "gold" }); club(root); } catch {} };
  };
}

// ==========================================================
// DIRECTION (dashboard)
// ==========================================================
export async function dashboard(root) {
  const [fin, cityData] = await Promise.all([api("/api/finances"), api("/api/city")]);
  const c = myClub(), d = derived(), me = S.state.user.id;
  const competitors = cityData.clubs.filter((x) => x.user_id !== me).sort((a, b) => b.cash - a.cash).slice(0, 5);
  const recent = fin.services.slice(-8).reverse();
  const nextCost = d.next_level ? d.next_level.upgrade_cost : null;
  root.innerHTML = `
    ${head("Direction", esc(c.name), `<a class="btn sm gold" href="#/showcases">🎤 Programmer un showcase</a><a class="btn sm ghost" href="#/equipment">🔊 Équipements</a>`)}
    <div class="grid four" style="margin-bottom:14px">
      <div class="metric gold"><span class="k">Trésorerie</span><span class="v">${money(c.cash)}</span><span class="s">Richesse totale <span data-own-wealth>${money(d.net_worth)}</span></span></div>
      <div class="metric"><span class="k">Dernier service</span><span class="v">${money(c.last_income)}</span><span class="s">${num(c.last_clients)} clients · ${c.last_vips} VIP</span></div>
      <div class="metric green"><span class="k">Revenus du jour</span><span class="v">${money(fin.today.total)}</span><span class="s">${fin.today.n} services</span></div>
      <div class="metric ${fin.today.net >= 0 ? "green" : "red"}"><span class="k">Bénéfice du jour</span><span class="v">${money(fin.today.net)}</span><span class="s">Dépenses ${money(fin.today.expenses)}</span></div>
    </div>
    <div class="grid" style="grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr)">
      <div>
        ${sceneBlock(c)}
        <div class="panel tight" style="margin-top:10px"><div class="row between"><div><div class="kicker">Prochain service</div><div class="num cyan" style="font-size:34px" id="big-timer">${countdown(d.next_service - now())}</div></div>
          <div style="flex:1;min-width:180px"><div class="bar cyan"><i id="big-timer-bar" style="width:0%"></i></div><div class="small muted" style="margin-top:4px">Service automatique toutes les ${cfg().tick_seconds / 60} minutes. Estimation : ${money(d.estimate.total)} (${num(d.estimate.clients)} clients).</div></div></div></div>
        <div class="grid two" style="margin-top:14px">
          <div class="panel"><h3>Activité en direct</h3>
            ${c.last_fun_event ? `<div class="notice" style="margin-bottom:10px"><b>${esc(c.last_fun_event.title)}</b><br>${esc(c.last_fun_event.text)}</div>` : ""}
            <div class="list">${recent.length ? recent.map((s) => `<div class="feed-item"><span class="t">${clock(s.ts)}</span><span class="i">${s.showcase_artist ? "🎤" : "💰"}</span><span>#${s.service_no} · <b>${money(s.total, { sign: true })}</b> · ${num(s.clients)} clients · ${s.vips} VIP${s.showcase_artist ? ` · showcase ${esc(s.showcase_artist)}` : ""}${s.combos ? " · 🔥 combo" : ""}</span></div>`).join("") : `<div class="muted small">Le premier service arrive bientôt.</div>`}</div></div>
          <div>
            <div class="panel accent-red" style="margin-bottom:14px"><h3>Dernier événement</h3>${c.last_event ? `<div><b>${esc(c.last_event.title)}</b></div><div class="small muted">${esc(c.last_event.text)}</div><div class="small muted" style="margin-top:4px">${ago(c.last_event.time)}</div>` : `<div class="muted small">Aucun événement récent. Contrôle toutes les ${cfg().event_interval / 60} min (${Math.round(cfg().event_chance * 100)} % de chance).</div>`}</div>
            <div class="panel accent-violet"><h3>Showcase</h3>${c.showcase_pending ? `<div><b>🎤 ${esc(c.showcase_artist)}</b> — actif sur le prochain service (+${Math.round(c.showcase_bonus * 100)} % entrées, x2 revenus)</div>` : `<div class="muted small">🥀 Aucun showcase en attente.</div><a class="btn sm violet" style="margin-top:8px" href="#/showcases">Programmer</a>`}${c.last_showcase_event ? `<div class="divider"></div><div class="small"><b>Dernier — ${esc(c.last_showcase_event.artist)}</b><br><span class="muted">${esc(c.last_showcase_event.text)}</span></div>` : ""}</div>
          </div>
        </div>
      </div>
      <div>
        <div class="panel" style="margin-bottom:14px"><h3>Prix d'entrée</h3>
          <div class="row between"><div class="num gold" style="font-size:30px">${money(c.entry_price)}</div><div class="small muted">max ${money(d.max_entry_price)}</div></div>
          <div class="small muted">Effet fréquentation : <b class="${d.price_client_mult >= 1 ? "green" : "red"}">${pct(d.price_client_mult - 1)}</b></div>
          <button class="btn sm gold block" style="margin-top:10px" id="price">Modifier le prix</button></div>
        <div class="panel" style="margin-bottom:14px"><h3>Progression</h3>
          <div>${levelPill(c.level, d.level_name)}</div>
          ${nextCost ? `<div class="small muted" style="margin:8px 0 4px">Prochain : <b>${esc(d.next_level.name)}</b> — ${money(nextCost)}</div><div class="bar"><i style="width:${Math.min(100, (c.cash / nextCost) * 100).toFixed(1)}%"></i></div><button class="btn sm ${c.cash >= nextCost ? "gold" : "ghost"} block" style="margin-top:10px" id="upgrade" ${c.cash >= nextCost ? "" : "disabled"}>Améliorer (${money(nextCost)})</button>` : `<div class="small gold" style="margin-top:8px">♛ Standing maximum atteint.</div>`}
          <a class="small" href="#/levels" style="display:block;margin-top:8px">Voir toute la progression →</a></div>
        <div class="panel"><h3>Concurrents</h3><div class="list">${competitors.length ? competitors.map((x) => `<div class="competitor" onclick="location.hash='#/visit/${x.user_id}'"><div class="avatar">${esc(x.avatar)}</div><div><div class="n">${esc(x.name)}</div><div class="m">${esc(x.level_name)} · ${num(x.last_clients)} clients</div></div><span class="spacer"></span><span class="num gold">${money(x.cash)}</span></div>`).join("") : `<div class="muted small">Vous êtes seul en ville pour l'instant.</div>`}</div></div>
      </div>
    </div>`;
  if (window.innerWidth < 900) root.querySelector(".grid[style]").style.gridTemplateColumns = "1fr";
  root.querySelector("#price").onclick = () => priceDialog();
  const up = root.querySelector("#upgrade");
  if (up) up.onclick = () => upgradeDialog();
}

export function priceDialog() {
  const c = myClub(), d = derived(), C = cfg();
  const max = d.max_entry_price;
  const est = (price) => {
    const lvl = C.levels[c.level];
    const priceMult = (1 + C.entry_price_effect.max_bonus) - C.entry_price_effect.span * (Math.max(0, Math.min(price, max)) / max);
    const mgr = d.manager ? (d.manager.client_bonus[0] + d.manager.client_bonus[1]) / 2 : 0;
    const clients = ((lvl.clients_min + lvl.clients_max) / 2 + mgr) * priceMult;
    const entry = clients * price * lvl.income_mult * (1 + d.bonuses.entry);
    return { priceMult, clients: Math.round(clients), entry: Math.round(entry), total: Math.round(entry + d.estimate.bar + d.estimate.vip) };
  };
  const cur = est(c.entry_price);
  const close = overlay(`<div class="kicker center">Prix de l'entrée</div><h2>Fixer le tarif</h2>
    <div class="row between" style="margin-top:14px"><div><div class="kicker">Prix actuel</div><div class="num gold" style="font-size:28px">${money(c.entry_price)}</div></div><div style="text-align:right"><div class="kicker">Nouveau prix</div><div class="num cyan" style="font-size:28px" id="np">${money(c.entry_price)}</div></div></div>
    <input type="range" id="slider" min="0" max="${max}" step="0.25" value="${c.entry_price}" style="margin:12px 0">
    <div class="row"><input id="pin" value="${c.entry_price}" style="max-width:120px"><span class="small muted">Maximum autorisé : ${money(max)} (niveau ${c.level})</span></div>
    <div class="kicker" style="margin-top:14px">Impact estimé</div>
    <div class="impact" id="impact"></div>
    <div class="row" style="justify-content:flex-end;margin-top:16px"><button class="btn ghost" data-close>Annuler</button><button class="btn gold" id="ok">Confirmer</button></div>`);
  const box = document.getElementById("overlays").lastElementChild;
  const slider = box.querySelector("#slider"), pin = box.querySelector("#pin");
  const update = (v) => {
    v = Math.max(0, Math.min(max, Number(String(v).replace(",", ".")) || 0));
    const e = est(v);
    box.querySelector("#np").textContent = money(v);
    const dClients = e.priceMult / cur.priceMult - 1, dRev = c.entry_price > 0 ? v / c.entry_price - 1 : 0, dTotal = e.total - cur.total;
    box.querySelector("#impact").innerHTML = `
      <div class="box"><div class="k">Fréquentation</div><div class="v ${dClients >= 0 ? "green" : "red"}">${pct(dClients, 1)}</div></div>
      <div class="box"><div class="k">Revenu / client</div><div class="v ${dRev >= 0 ? "green" : "red"}">${c.entry_price > 0 ? pct(dRev) : "—"}</div></div>
      <div class="box"><div class="k">Clients / service</div><div class="v">≈ ${num(e.clients)}</div></div>
      <div class="box"><div class="k">Revenu estimé / service</div><div class="v ${dTotal >= 0 ? "green" : "red"}">${money(dTotal, { sign: true })}</div></div>`;
  };
  slider.oninput = () => { pin.value = slider.value; update(slider.value); };
  pin.oninput = () => { slider.value = pin.value; update(pin.value); };
  update(c.entry_price);
  box.querySelector("#ok").onclick = async () => {
    try { const r = await act("/api/club/entry-price", { price: pin.value }); close(); toast({ icon: "🎟️", title: "Prix d'entrée mis à jour", text: `${money(r.old)} → ${money(r.new)}`, tone: "gold" }); dashboard(document.getElementById("view")); } catch {}
  };
}

export async function upgradeDialog() {
  const c = myClub(), d = derived();
  if (!d.next_level) return;
  const n = d.next_level, cur = d.level_info;
  const ok = await confirmBox({ title: `Devenir ${n.name}`, html: `
    <div class="lines">
      <div class="line"><span>Coût</span><b class="red">${money(-n.upgrade_cost)}</b></div>
      <div class="line"><span>Bonus général</span><b>${pct(cur.income_mult - 1)} → <span class="green">${pct(n.income_mult - 1)}</span></b></div>
      <div class="line"><span>Clients / service</span><b>${cur.clients_min}–${cur.clients_max} → <span class="green">${n.clients_min}–${n.clients_max}</span></b></div>
      <div class="line"><span>Entrée max</span><b>${money(cur.max_entry)} → <span class="green">${money(n.max_entry)}</span></b></div>
      <div class="line"><span>Bonus showcase</span><b>${pct(cur.showcase_mult - 1)} → <span class="green">${pct(n.showcase_mult - 1)}</span></b></div>
    </div>`, okLabel: "Acheter l'amélioration" });
  if (!ok) return;
  try {
    const r = await act("/api/club/upgrade");
    audio.playUi("levelup");
    overlay(`<h2>📈 NIVEAU SUPÉRIEUR</h2><div class="big">${esc(r.name).toUpperCase()}</div><p class="center muted">Votre établissement change de standing. La façade évolue.</p><div class="row" style="justify-content:center"><button class="btn gold" data-close>Voir ma boîte</button></div>`);
    document.getElementById("overlays").lastElementChild.querySelector("[data-close]").addEventListener("click", () => navigate("#/club"));
  } catch {}
}

// ==========================================================
// FINANCES
// ==========================================================
export async function finances(root) {
  const fin = await api("/api/finances");
  const c = myClub();
  const t = fin.totals, today = fin.today;
  const services = fin.services.slice().reverse();
  const spark = sparkline(fin.services.map((s) => s.total));
  root.innerHTML = `
    ${head("Registre financier", esc(c.name))}
    <div class="grid four" style="margin-bottom:14px">
      <div class="metric gold"><span class="k">Trésorerie</span><span class="v">${money(c.cash)}</span></div>
      <div class="metric"><span class="k">Dernier service</span><span class="v">${money(fin.last.income)}</span><span class="s">${num(fin.last.clients)} clients · ${fin.last.vips} VIP</span></div>
      <div class="metric green"><span class="k">Revenus du jour</span><span class="v">${money(today.total + today.other_income)}</span><span class="s">${today.n} services</span></div>
      <div class="metric red"><span class="k">Dépenses du jour</span><span class="v">${money(today.expenses)}</span></div>
      <div class="metric ${today.net >= 0 ? "green" : "red"}"><span class="k">Bénéfice du jour</span><span class="v">${money(today.net)}</span></div>
      <div class="metric"><span class="k">Bar (total)</span><span class="v">${money(t.bar)}</span></div>
      <div class="metric"><span class="k">Entrées (total)</span><span class="v">${money(t.entry)}</span></div>
      <div class="metric violet"><span class="k">VIP (total)</span><span class="v">${money(t.vip)}</span></div>
      <div class="metric"><span class="k">Clients reçus</span><span class="v">${num(t.clients)}</span></div>
      <div class="metric"><span class="k">VIP reçus</span><span class="v">${num(t.vips)}</span></div>
      <div class="metric"><span class="k">Showcases</span><span class="v">${num(t.showcases)}</span></div>
      <div class="metric red"><span class="k">Dépenses (total)</span><span class="v">${money(t.expenses)}</span></div>
    </div>
    <div class="panel" style="margin-bottom:14px"><div class="kicker">Revenus par service (60 derniers)</div>${spark}</div>
    <div class="grid two">
      <div class="panel"><h3>Historique des services</h3><div class="table-wrap"><table class="table"><thead><tr><th>#</th><th>Heure</th><th class="r">Clients</th><th class="r">VIP</th><th class="r">Bar</th><th class="r">Entrées</th><th class="r">VIP €</th><th class="r">Total</th><th>Notes</th></tr></thead>
        <tbody>${services.map((s) => `<tr><td class="muted">${s.service_no}</td><td class="muted">${clock(s.ts)}</td><td class="r">${num(s.clients)}</td><td class="r">${s.vips}</td><td class="r">${money(s.bar)}</td><td class="r">${money(s.entry)}</td><td class="r">${money(s.vip)}</td><td class="r gold num">${money(s.total)}</td><td class="small">${s.showcase_artist ? `🎤 ${esc(s.showcase_artist)} ` : ""}${s.combos ? "🔥 " : ""}${s.salary ? `<span class="muted">-${money(s.salary)} salaire</span>` : ""}</td></tr>`).join("") || `<tr><td colspan="9" class="muted">Aucun service pour l'instant.</td></tr>`}</tbody></table></div></div>
      <div class="panel"><h3>Grand livre</h3><div class="table-wrap"><table class="table"><thead><tr><th>Date</th><th>Type</th><th>Libellé</th><th class="r">Montant</th><th class="r">Solde</th></tr></thead>
        <tbody>${fin.transactions.map((x) => `<tr><td class="muted small">${dateTime(x.ts)}</td><td><span class="pill ${x.amount >= 0 ? "green" : "red"}">${esc(txLabel(x.kind))}</span></td><td class="small">${esc(x.label)}</td><td class="r num ${x.amount >= 0 ? "green" : "red"}">${money(x.amount, { sign: true })}</td><td class="r muted num">${money(x.balance_after)}</td></tr>`).join("") || `<tr><td colspan="5" class="muted">Aucune opération.</td></tr>`}</tbody></table></div></div>
    </div>`;
}

function sparkline(values) {
  if (!values.length) return `<div class="muted small">Pas encore de données.</div>`;
  const w = 1000, h = 120, max = Math.max(...values, 1);
  const step = w / Math.max(1, values.length - 1);
  const pts = values.map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * (h - 10) - 4).toFixed(1)}`);
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:120px;display:block"><defs><linearGradient id="spk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a855f7" stop-opacity=".5"/><stop offset="1" stop-color="#a855f7" stop-opacity="0"/></linearGradient></defs>
    <path d="M0,${h} L${pts.join(" L")} L${w},${h} Z" fill="url(#spk)"/><polyline points="${pts.join(" ")}" fill="none" stroke="#d9a7ff" stroke-width="2"/>
    ${values.map((v, i) => `<circle cx="${(i * step).toFixed(1)}" cy="${(h - (v / max) * (h - 10) - 4).toFixed(1)}" r="2.5" fill="#d9a7ff"><title>${money(v)}</title></circle>`).join("")}</svg>`;
}

// ==========================================================
// SHOWCASES
// ==========================================================
const showcaseFilters = { query: "", sort: "rating", affordable: false };
const normalizeArtist = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("fr");

export async function showcases(root) {
  const c = myClub(), d = derived(), C = cfg();
  const artists = C.artist_order;
  const discovered = new Set(d.combos_discovered);
  root.innerHTML = `
    ${head("Bureau des showcases", "Programmer un artiste")}
    <div class="panel" style="margin-bottom:14px">
      <div class="row between"><h3>Rap 2016–2026 · ${Object.values(C.artists).filter((a) => a.collection === "rap_2016_2026").length} artistes sélectionnés</h3><span class="pill gold">${artists.length} affiches au total</span></div>
      <p class="muted small">Les grands noms du rap en France et de la scène francophone, groupes inclus. Notes et cachets fictifs pour le jeu, selon leur rayonnement sur la période et leur potentiel en club.</p>
      <div class="row" style="flex-wrap:wrap;gap:12px">
        <label>Rechercher <input id="artist-search" type="search" placeholder="Ninho, Jul, SCH…" value="${esc(showcaseFilters.query)}"></label>
        <label>Trier <select id="artist-sort"><option value="rating">Note décroissante</option><option value="price">Prix croissant</option><option value="name">Nom A–Z</option></select></label>
        <label><input id="artist-affordable" type="checkbox" ${showcaseFilters.affordable ? "checked" : ""}> Dans mon budget</label>
        <span id="artist-count" class="muted small" aria-live="polite"></span>
      </div>
    </div>
    ${c.showcase_pending ? `<div class="panel accent-violet" style="margin-bottom:14px"><div class="row between"><div><div class="kicker">Showcase programmé</div><h2>🎤 ${esc(c.showcase_artist)}</h2><div class="muted small">Le bonus est appliqué automatiquement au prochain service (<span id="big-timer">${countdown(d.next_service - now())}</span>). Tous les showcases donnent x${C.showcase_clients_mult} clients de showcase et x${C.showcase_income_mult} revenus sur le service.</div></div><div class="num violet" style="font-size:30px">+${Math.round(c.showcase_bonus * 100)} %</div></div></div>` : `<div class="notice gold" style="margin-bottom:14px">Effet : bonus artiste sur les entrées + bonus de standing (<b>${pct(d.showcase_mult - 1)}</b> au niveau ${c.level}) — et <b>x${C.showcase_income_mult} revenus</b> sur le service. Un même artiste ne peut revenir qu'après ${C.artist_cooldown_services} services complets.</div>`}
    <div class="grid" style="grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr)">
      <div class="list" id="artist-list"></div>
      <div>
        <div class="panel accent-red"><h3>🔥 Combos secrets</h3><p class="muted small">Certaines combinaisons déclenchent des effets spéciaux. Ils se découvrent en jouant.</p>
          <div class="list">${C.combo_hints.map((h) => discovered.has(h.id) ? `<div class="combo-card found"><div class="kicker" style="color:var(--red2)">Découvert</div><b>${h.id === "coca_lagui" ? "Coca Cherry + Showcase Lagui" : "Boro 700 + Saisai"}</b><div class="small muted">${h.id === "coca_lagui" ? "Le même service : clients x2, entrées +25 %, bar +20 %, +2 VIP." : "Double showcase surprise : clients x2, entrées +20 %, bar +15 %, +1 VIP."}</div></div>` : `<div class="combo-card"><div class="kicker">Indice</div><div class="small">${esc(h.hint)}</div></div>`).join("")}</div></div>
        ${c.last_showcase_event ? `<div class="panel" style="margin-top:14px"><h3>Dernier showcase</h3><b>${esc(c.last_showcase_event.artist)}</b><div class="small muted">${esc(c.last_showcase_event.text)}</div><div class="num ${c.last_showcase_event.clients >= 0 ? "green" : "red"}" style="font-size:20px">${c.last_showcase_event.clients >= 0 ? "+" : ""}${num(c.last_showcase_event.clients)} clients</div></div>` : ""}
      </div>
    </div>`;
  if (window.innerWidth < 900) root.querySelector(".grid[style]").style.gridTemplateColumns = "1fr";
  const renderArtists = () => {
    const query = normalizeArtist(showcaseFilters.query.trim());
    const filtered = artists.filter((a) => normalizeArtist(a).includes(query) && (!showcaseFilters.affordable || d.artist_costs[a] <= c.cash));
    filtered.sort((a, b) => showcaseFilters.sort === "price" ? d.artist_costs[a] - d.artist_costs[b] || a.localeCompare(b, "fr") : showcaseFilters.sort === "name" ? a.localeCompare(b, "fr") : (C.artists[b]?.rating ?? 0) - (C.artists[a]?.rating ?? 0) || a.localeCompare(b, "fr"));
    root.querySelector("#artist-list").innerHTML = filtered.map((a) => artistCard(a, c, d, C)).join("") || `<div class="notice">Aucun artiste ne correspond à ces critères.</div>`;
    root.querySelector("#artist-count").textContent = `${filtered.length} / ${artists.length} affiches`;
    root.querySelectorAll("[data-book]").forEach((b) => b.onclick = () => bookShowcase(b.dataset.book, root));
  };
  root.querySelector("#artist-sort").value = showcaseFilters.sort;
  root.querySelector("#artist-search").oninput = (e) => { showcaseFilters.query = e.target.value; renderArtists(); };
  root.querySelector("#artist-sort").onchange = (e) => { showcaseFilters.sort = e.target.value; renderArtists(); };
  root.querySelector("#artist-affordable").onchange = (e) => { showcaseFilters.affordable = e.target.checked; renderArtists(); };
  renderArtists();
}

function artistCard(a, c, d, C) {
  const bonus = C.artists[a]?.bonus ?? C.artist_default_bonus;
  const cost = d.artist_costs[a];
  const cd = d.artist_cooldowns[a] || 0;
  const phrases = C.showcase_phrases[a] || [C.showcase_default_phrase];
  const lo = Math.min(...phrases.map((p) => p[1])) * C.showcase_clients_mult, hi = Math.max(...phrases.map((p) => p[2])) * C.showcase_clients_mult;
  const entryMult = (1 + bonus) * d.showcase_mult * C.showcase_income_mult;
  const pop = Math.round(bonus * 100);
  const canAfford = c.cash >= cost;
  const disabled = c.showcase_pending || cd > 0 || !canAfford;
  return `<div class="item artist-card ${cd > 0 ? "locked" : ""}"><div class="artist-art"><span class="artist-edition">OLIVIA LIVE SESSIONS</span><span class="artist-initial">${esc(a.slice(0, 2).toUpperCase())}</span>${icon("showcases")}<span class="artist-stamp">${esc(C.artists[a]?.tier || "EXCLUSIF")}</span></div><div class="body">
    <div class="title">${esc(a)} ${C.artists[a]?.rating != null ? `<span class="pill gold">${C.artists[a].rating}/100</span> <span class="pill">${esc(C.artists[a].tier)}</span>` : `<span class="pill violet">Artiste original</span>`}<span class="muted small" style="font-family:var(--font-body);font-weight:400">${a === "Lagui" ? "— car Lagui c'est le meilleur" : ""}</span></div>
    <div class="desc">Popularité <span class="gold">${stars(bonus)}</span> · bonus entrées <b class="green">+${pop} %</b> · clients potentiels <b>${lo}–${hi}</b>${a === "Boro 700" ? " · <span class='violet'>peut venir accompagné</span>" : ""}${a === "Bello&Dallas" ? " · <span class='red'>imprévisible</span>" : ""}</div>
    <div class="desc">Impact estimé sur les entrées : <b class="gold">x${entryMult.toFixed(2)}</b> (artiste × standing × ${C.showcase_income_mult}) · cooldown ${C.artist_cooldown_services} services${cd > 0 ? ` · <span class="red">encore ${cd} service${cd > 1 ? "s" : ""}</span>` : ""}</div></div>
    <div class="price">${money(cost)}</div><div class="actions"><button class="btn sm ${disabled ? "ghost" : "gold"}" data-book="${esc(a)}" ${disabled ? "disabled" : ""}>${c.showcase_pending ? "Déjà programmé" : cd > 0 ? "Repos" : canAfford ? "Programmer" : "Trésorerie"}</button></div></div>`;
}

async function bookShowcase(artist, root) {
  const d = derived(), C = cfg();
  const bonus = C.artists[artist]?.bonus ?? C.artist_default_bonus;
  const ok = await confirmBox({ title: `Programmer ${artist}`, html: `<div class="lines"><div class="line"><span>Frais</span><b class="red">${money(-d.artist_costs[artist])}</b></div><div class="line"><span>Bonus artiste</span><b class="green">+${Math.round(bonus * 100)} %</b></div><div class="line"><span>Bonus standing</span><b class="green">${pct(d.showcase_mult - 1)}</b></div><div class="line"><span>Revenus du service</span><b class="green">x${C.showcase_income_mult}</b></div></div><p class="muted small">Le bonus sera appliqué automatiquement au prochain service.</p>`, okLabel: "Confirmer le showcase" });
  if (!ok) return;
  try {
    await act("/api/club/showcase", { artist });
    overlay(`<h2>🎤 SHOWCASE PROGRAMMÉ</h2><div class="big" style="font-size:32px">${esc(artist).toUpperCase()}</div><p class="center muted">Le clip et sa musique sont diffusés dans ta boîte. Le bonus sera appliqué au prochain service.</p><div class="row" style="justify-content:center"><a class="btn violet" href="#/club" data-close>Voir le showcase dans ma boîte</a></div>`);
    showcases(root);
  } catch {}
}

// ==========================================================
// ÉQUIPEMENTS
// ==========================================================
export async function equipment(root) {
  const c = myClub(), d = derived(), C = cfg();
  const owned = new Set(c.equipment);
  const entries = Object.entries(C.equipment);
  root.innerHTML = `
    ${head("Personnel & équipements", "Améliorations secondaires", `<span class="pill gold">${owned.size}/${entries.length} installés</span>`)}
    <div class="grid four" style="margin-bottom:14px">
      <div class="metric"><span class="k">Bonus bar</span><span class="v green">${pct(d.bonuses.bar)}</span></div>
      <div class="metric"><span class="k">Bonus entrées</span><span class="v green">${pct(d.bonuses.entry)}</span></div>
      <div class="metric"><span class="k">Bonus VIP</span><span class="v green">${pct(d.bonuses.vip)}</span></div>
      <div class="metric"><span class="k">Puissance (braquage)</span><span class="v gold">${d.robbery_power}</span><span class="s">+${C.robbery.level_power}/niveau, +${C.robbery.equipment_power}/équipement</span></div>
    </div>
    <div class="list">${entries.map(([id, it]) => {
      const has = owned.has(id), can = c.cash >= it.cost;
      const impact = ["bar_bonus", "entry_bonus", "vip_bonus"].filter((k) => it[k]).map((k) => `${{ bar_bonus: "Bar", entry_bonus: "Entrées", vip_bonus: "VIP" }[k]} ${pct(it[k])}`).join(" · ");
      return `<div class="item ${has ? "owned" : ""}"><div class="ico">${it.emoji}</div><div class="body"><div class="title">${esc(it.name)}</div><div class="desc">${esc(it.description)} · <span class="green">${impact}</span></div></div>
        ${has ? `<span class="pill green">Installé</span>` : `<div class="price">${money(it.cost)}</div><div class="actions"><button class="btn sm ${can ? "gold" : "ghost"}" data-buy="${id}" ${can ? "" : "disabled"}>Acheter</button></div>`}</div>`;
    }).join("")}</div>
    <p class="muted small" style="margin-top:12px">♣ Ces bonus se cumulent avec le standing de votre boîte et apparaissent sur la façade.</p>`;
  root.querySelectorAll("[data-buy]").forEach((b) => b.onclick = async () => {
    const it = C.equipment[b.dataset.buy];
    const ok = await confirmBox({ title: it.name, html: `<div class="lines"><div class="line"><span>Prix</span><b class="red">${money(-it.cost)}</b></div><div class="line"><span>Effet</span><b class="green">${esc(it.description)}</b></div></div>`, okLabel: "Acheter" });
    if (!ok) return;
    try {
      const r = await act("/api/club/equipment", { item_id: b.dataset.buy });
      overlay(`<div class="big red" style="font-size:30px">${money(-r.cost)}</div><h2>${it.emoji} ${esc(it.name).toUpperCase()} INSTALLÉ</h2><div class="lines">${["bar_bonus", "entry_bonus", "vip_bonus"].filter((k) => it[k]).map((k) => `<div class="line"><span>${{ bar_bonus: "🍸 Bar", entry_bonus: "🎟️ Entrées", vip_bonus: "👑 VIP" }[k]}</span><b class="green">${pct(it[k])}</b></div>`).join("")}</div><div class="row" style="justify-content:center"><button class="btn gold" data-close>Continuer</button></div>`);
      equipment(root);
    } catch {}
  });
}

// ==========================================================
// MANAGER
// ==========================================================
export async function manager(root) {
  const c = myClub(), d = derived(), C = cfg();
  const cur = d.manager;
  const card = (id, m, isCurrent) => `<div class="item ${isCurrent ? "active" : ""}"><div class="ico">♣</div><div class="body"><div class="title">${esc(m.name)} <span class="pill">Niveau ${m.level}</span>${isCurrent ? ` <span class="pill gold">Manager actuel</span>` : ""}</div><div class="desc">${esc(m.description)}</div>
      <div class="impact"><div class="box"><div class="k">Salaire</div><div class="v red">${money(m.salary)}</div><div class="small muted">/ service</div></div><div class="box"><div class="k">Bonus clients</div><div class="v green">+${m.client_bonus[0]} à +${m.client_bonus[1]}</div></div><div class="box"><div class="k">Chance VIP</div><div class="v">${Math.round(m.vip_chance * 100)} %</div></div><div class="box"><div class="k">Chance showcase</div><div class="v">${Math.round(m.showcase_chance * 100)} %</div></div><div class="box"><div class="k">Cooldown showcase</div><div class="v">${m.showcase_cooldown_ticks} services</div></div></div></div>
      <div class="actions">${isCurrent ? `<button class="btn sm red" data-fire>Licencier</button>` : `<button class="btn sm ${cur ? "ghost" : "gold"}" data-hire="${id}">${cur ? "Remplacer" : "Engager"}</button>`}</div></div>`;
  root.innerHTML = `
    ${head("Managers & manageuses", "Personnel")}
    <div class="notice" style="margin-bottom:14px">🖤 Votre manager travaille automatiquement à chaque service de ${C.tick_seconds / 60} minutes : publicité, VIP, showcases. Le salaire est payé à chaque service <b>seulement si la trésorerie le permet</b> — sinon il ne produit aucun bonus (mais n'est pas viré).</div>
    ${cur ? `<div class="panel accent-gold" style="margin-bottom:14px"><div class="kicker">Manager actuel</div>${card(cur.id, cur, true)}</div>` : `<div class="panel" style="margin-bottom:14px"><div class="kicker">Manager actuel</div><div class="muted">Aucun manager embauché.</div></div>`}
    <div class="list">${Object.entries(C.managers).filter(([id]) => !cur || id !== cur.id).map(([id, m]) => card(id, m, false)).join("")}</div>`;
  root.querySelectorAll("[data-hire]").forEach((b) => b.onclick = async () => {
    const m = C.managers[b.dataset.hire];
    const ok = await confirmBox({ title: `Engager ${m.name}`, html: `<p>Salaire : <b class="red">${money(m.salary)} / service</b>${cur ? `<br>${esc(cur.name)} sera remplacé(e).` : ""}</p>`, okLabel: "Signer le contrat" });
    if (!ok) return;
    try { await act("/api/club/manager", { manager_id: b.dataset.hire }); toast({ icon: "♣", title: "Contrat signé", text: `${m.name} devient votre manager.`, tone: "gold" }); manager(root); } catch {}
  });
  const fire = root.querySelector("[data-fire]");
  if (fire) fire.onclick = async () => { if (!(await confirmBox({ title: "Licencier le manager", html: `<p>${esc(cur.name)} quittera l'établissement immédiatement.</p>`, okLabel: "Licencier", tone: "red" }))) return; try { await act("/api/club/manager", null, { method: "DELETE" }); manager(root); } catch {} };
}

// ==========================================================
// ACTIVITÉS + BLACKJACK
// ==========================================================
export async function activities(root, params, keepBet) {
  const c = myClub(), d = derived(), C = cfg();
  const A = C.activities;
  const bj = A.blackjack;
  const game = d.blackjack;
  const mode = C.web.blackjack_mode;
  const bets = bj.bets;
  const selBet = keepBet || S.cache.bet || bets[0];
  const cards = (hand) => hand.map((k) => k.hidden ? `<div class="card back"></div>` : `<div class="card ${["♥", "♦"].includes(k.suit) ? "red" : ""}"><span>${k.rank}</span><span class="s">${k.suit}</span><span style="text-align:right">${k.rank}</span></div>`).join("");
  const total = c.blackjack_wins + c.blackjack_losses;
  root.innerHTML = `
    ${head("Salle des activités", "Pendant que la clientèle arrive…")}
    <div class="grid" style="grid-template-columns: minmax(0, 1.2fr) minmax(300px, 1fr)">
      <div class="panel"><div class="row between"><h3>🃏 Blackjack privé</h3><span class="pill">${c.blackjack_wins} V · ${c.blackjack_losses} D${total ? ` · ${Math.round((c.blackjack_wins / total) * 100)} %` : ""}</span></div>
        <div class="bj-table" id="bj">
          <div class="bj-total">Banque · <b id="bj-dealer">${game ? game.dealer_total : "—"}</b></div><div class="bj-hand">${game ? cards(game.dealer) : `<div class="card back"></div><div class="card back"></div>`}</div>
          <div class="bj-total" style="margin-top:14px">Vous · <b id="bj-player">${game ? game.player_total : "—"}</b></div><div class="bj-hand">${game ? cards(game.player) : `<div class="card back"></div><div class="card back"></div>`}</div>
          <div id="bj-result" class="num" style="font-size:22px;margin:10px 0;min-height:28px"></div>
          ${game ? `<div class="row" style="justify-content:center"><button class="btn gold" id="hit">Tirer</button><button class="btn red" id="stand">Rester</button><span class="pill gold">Mise ${money(game.bet)}</span></div>`
          : `<div class="bets">${bets.map((b) => `<button class="chip-bet ${b === selBet ? "on" : ""}" data-bet="${b}">${money(b)}</button>`).join("")}</div>
             <button class="btn gold lg" id="deal" style="margin-top:14px">${mode === "auto" ? "Jouer la main" : "Distribuer"} — <span id="bet-label">${money(selBet)}</span></button>`}
        </div>
        <p class="muted small">Mises de ${money(bj.min_bet)} à ${money(bj.max_bet)}. Une victoire paie votre mise en bénéfice, une défaite la fait perdre. ${mode === "auto" ? "Mode original : la main est jouée automatiquement (tirage jusqu'à 16, banque jusqu'à 17)." : "Mode table : vous décidez de tirer ou rester ; la banque tire jusqu'à 17."}</p></div>
      <div class="list">
        ${activityCard("drink", A.drink, `50 % de chance de finir bourré : <b class="red">-${A.drink.penalty} clients</b> au prochain service. Sinon bonne ambiance : <b class="green">+${A.drink.bonus} clients</b>.`, "Risque 50 %", c)}
        ${activityCard("promo", A.promo, `Ajoute <b class="green">+${A.promo.bonus} clients</b> au prochain service.`, "Sans risque", c)}
        ${activityCard("influencer", A.influencer, `${Math.round(A.influencer.chance * 100)} % de réussite : <b class="green">+${A.influencer.bonus} clients</b>. Sinon la campagne ne prend pas.`, `Risque ${Math.round((1 - A.influencer.chance) * 100)} %`, c)}
        ${activityCard("coca_cherry", A.coca_cherry, `Vous ramenez <b>Coca Cherry</b> : show twerk, <b class="green">+${A.coca_cherry.bonus} clients</b> au prochain service.${c.coca_cherry_pending ? " <span class='pill pink'>Présente ce soir</span>" : ""} <span class="muted">Une rumeur parle d'un combo avec un certain showcase…</span>`, "Sans risque", c)}
        <div class="panel tight"><div class="kicker">Prochain service</div><div class="row between"><span>Bonus clients en attente</span><b class="green">+${num(c.client_bonus_next)}</b></div><div class="row between"><span>Malus clients en attente</span><b class="red">-${num(c.client_penalty_next)}</b></div><div class="row between"><span>Verres bus</span><b>${c.drinks_taken}</b></div></div>
      </div>
    </div>`;
  if (window.innerWidth < 900) root.querySelector(".grid[style]").style.gridTemplateColumns = "1fr";
  root.querySelectorAll("[data-bet]").forEach((b) => b.onclick = () => { S.cache.bet = Number(b.dataset.bet); root.querySelectorAll("[data-bet]").forEach((x) => x.classList.toggle("on", x === b)); root.querySelector("#bet-label").textContent = money(S.cache.bet); });
  const deal = root.querySelector("#deal");
  if (deal) deal.onclick = () => bjAction(root, "start", S.cache.bet || selBet);
  const hit = root.querySelector("#hit"); if (hit) hit.onclick = () => bjAction(root, "hit");
  const stand = root.querySelector("#stand"); if (stand) stand.onclick = () => bjAction(root, "stand");
  root.querySelectorAll("[data-activity]").forEach((b) => b.onclick = async () => {
    const id = b.dataset.activity, a = A[id];
    const ok = await confirmBox({ title: a.name, html: `<p>Coût : <b class="red">${money(a.cost)}</b></p>`, okLabel: "Lancer" });
    if (!ok) return;
    try {
      const r = await act(`/api/activities/${id}`);
      overlay(`<div class="big" style="font-size:40px">${r.icon}</div><h2>${esc(r.title)}</h2><p class="center">${esc(r.text)}</p>${r.clients ? `<div class="big ${r.clients > 0 ? "green" : "red"}" style="font-size:28px">${r.clients > 0 ? "+" : ""}${r.clients} clients au prochain service</div>` : ""}<div class="row" style="justify-content:center;margin-top:12px"><button class="btn gold" data-close>Continuer</button></div>`);
      activities(root);
    } catch {}
  });
}

function activityCard(id, a, desc, risk, c) {
  const can = c.cash >= a.cost;
  return `<div class="item"><div class="ico">${a.emoji}</div><div class="body"><div class="title">${esc(a.name)} <span class="pill ${risk.startsWith("Sans") ? "green" : "red"}">${risk}</span></div><div class="desc">${desc}</div></div><div class="price">${money(a.cost)}</div><div class="actions"><button class="btn sm ${can ? "gold" : "ghost"}" data-activity="${id}" ${can ? "" : "disabled"}>Lancer</button></div></div>`;
}

async function bjAction(root, op, bet) {
  try {
    const r = await act(`/api/blackjack/${op}`, op === "start" ? { bet } : null);
    if (["WIN", "LOSE", "PUSH"].includes(r.status)) {
      const label = { WIN: `🃏 Victoire — bénéfice ${money(r.delta, { sign: true })}`, LOSE: `🃏 Défaite — perte ${money(r.delta)}`, PUSH: "🃏 Égalité — la mise vous revient" }[r.status];
      await activities(root, null, r.bet);
      const box = root.querySelector("#bj");
      const cards = (hand) => hand.map((k) => `<div class="card ${["♥", "♦"].includes(k.suit) ? "red" : ""}"><span>${k.rank}</span><span class="s">${k.suit}</span><span style="text-align:right">${k.rank}</span></div>`).join("");
      box.querySelector("#bj-dealer").textContent = r.dealer;
      box.querySelector("#bj-player").textContent = r.player;
      box.querySelectorAll(".bj-hand")[0].innerHTML = cards(r.dealer_cards);
      box.querySelectorAll(".bj-hand")[1].innerHTML = cards(r.player_cards);
      const res = box.querySelector("#bj-result");
      res.textContent = label; res.className = `num ${r.status === "WIN" ? "green" : r.status === "LOSE" ? "red" : "gold"}`;
      res.style.fontSize = "22px";
    } else {
      activities(root);
    }
  } catch {}
}

// ==========================================================
// BOUTIQUE
// ==========================================================
export { shop, updateMarketView } from "./market-ui.js";

// ==========================================================
// BANQUE — transferts, bouteilles, trades, braquage
// ==========================================================
export async function bank(root, params) {
  const [{ players }, { trades }] = await Promise.all([api("/api/players"), api("/api/trades")]);
  const c = myClub(), d = derived(), C = cfg(), me = S.state.user.id;
  const target = params?.id || (players[0] && players[0].user_id);
  const incoming = trades.filter((t) => t.target_id === me && t.status === "pending");
  const outgoing = trades.filter((t) => t.sender_id === me && t.status === "pending");
  const history = trades.filter((t) => t.status !== "pending").slice(0, 12);
  const none = !players.length;
  root.innerHTML = `
    ${head("Banque & marché", "Transactions entre joueurs", `<span class="pill gold">Trésorerie ${money(c.cash)}</span>`)}
    ${none ? `<div class="notice gold" style="margin-bottom:14px">Aucun autre joueur en ville pour l'instant. Invitez vos concurrents à ouvrir leur boîte.</div>` : ""}
    <div class="grid two">
      <div class="panel"><h3>💸 Envoyer de l'argent</h3><div class="field"><label>Joueur</label>${playerSelect(players, "t-money", target)}</div><div class="field"><label>Montant (€)</label><input id="amount" type="number" min="1" placeholder="Ex : 5000"></div><button class="btn gold" id="send" ${none ? "disabled" : ""}>Envoyer</button></div>
      <div class="panel"><h3>🍾 Service bouteilles</h3><div class="field"><label>Boîte destinataire</label>${playerSelect(players, "t-bottle", target)}</div>
        <div class="list">${Object.entries(C.bottle_packs).map(([id, p]) => `<div class="item"><div class="ico">${p.emoji}</div><div class="body"><div class="title">${esc(p.name)}</div><div class="desc">${esc(p.description)} · la boîte reçoit <b class="green">${money(p.receiver_bonus)}</b> et <b class="green">+${Math.max(C.bottle_clients_min, Math.floor(p.receiver_bonus / C.bottle_clients_divisor))} clients</b></div></div><div class="price">${money(p.cost)}</div><div class="actions"><button class="btn sm ${c.cash >= p.cost ? "gold" : "ghost"}" data-pack="${id}" ${c.cash >= p.cost && !none ? "" : "disabled"}>Envoyer</button></div></div>`).join("")}</div></div>
      <div class="panel"><h3>♣ Proposer un trade</h3><p class="muted small">Le destinataire devra accepter avant que l'objet ou l'argent soit transféré.</p>
        <div class="field"><label>Joueur</label>${playerSelect(players, "t-trade", target)}</div>
        <div class="field"><label>Type</label><select id="trade-type"><option value="money">💶 Argent</option><option value="bitcoin">🪙 Bitcoin (${c.bitcoin} BTC)</option><option value="cars">🚘 Voiture</option><option value="watches">⌚ Montre</option></select></div>
        <div class="field" id="trade-value-wrap"><label>Montant (€)</label><input id="trade-value" type="number" min="1"></div>
        <button class="btn violet" id="propose" ${none ? "disabled" : ""}>Proposer</button>
        ${incoming.length ? `<div class="divider"></div><div class="kicker">Propositions reçues</div><div class="list">${incoming.map((t) => `<div class="item active"><div class="ico">♣</div><div class="body"><div class="title">${esc(t.sender_name)} propose ${esc(t.detail)}</div><div class="desc">${ago(t.created_at)}</div></div><div class="actions"><button class="btn sm gold" data-accept="${t.id}">Accepter</button><button class="btn sm red" data-refuse="${t.id}">Refuser</button></div></div>`).join("")}</div>` : ""}
        ${outgoing.length ? `<div class="divider"></div><div class="kicker">En attente</div><div class="list">${outgoing.map((t) => `<div class="item"><div class="ico">⏳</div><div class="body"><div class="title">${esc(t.detail)} → ${esc(t.target_name)}</div><div class="desc">${ago(t.created_at)}</div></div><div class="actions"><button class="btn sm ghost" data-cancel="${t.id}">Annuler</button></div></div>`).join("")}</div>` : ""}
        ${history.length ? `<div class="divider"></div><div class="kicker">Historique</div><div class="list">${history.map((t) => `<div class="feed-item"><span class="t">${clock(t.created_at)}</span><span class="i">${t.status === "accepted" ? "✅" : "❌"}</span><span>${esc(t.sender_name)} → ${esc(t.target_name)} : ${esc(t.detail)} (${t.status === "accepted" ? "accepté" : t.status === "refused" ? "refusé" : t.status})</span></div>`).join("")}</div>` : ""}</div>
      <div class="panel accent-red"><h3>🚨 Braquage</h3><p class="muted small">Tenter de voler <b>${Math.round(C.robbery.steal_rate * 100)} %</b> de la trésorerie d'une autre boîte. Chance = ${C.robbery.base_chance} % + votre puissance − la sienne (entre ${C.robbery.min_chance} et ${C.robbery.max_chance} %). En cas d'échec : vous perdez ${Math.round(C.robbery.fail_loss_rate * 100)} % de votre trésorerie. Un essai tous les ${C.robbery.cooldown_services} services.</p>
        <div class="field"><label>Cible</label>${playerSelect(players, "t-rob", target)}</div>
        <div class="impact" id="rob-impact"></div>
        <button class="btn red" id="rob" style="margin-top:12px" ${none || d.robbery_cooldown > 0 ? "disabled" : ""}>${d.robbery_cooldown > 0 ? `Vos hommes doivent se faire oublier (${d.robbery_cooldown} service${d.robbery_cooldown > 1 ? "s" : ""})` : "Envoyer mes hommes"}</button></div>
    </div>`;
  const byId = Object.fromEntries(players.map((p) => [String(p.user_id), p]));
  const robImpact = async () => {
    const sel = root.querySelector("#t-rob"); if (!sel || !sel.value) return;
    const v = await api(`/api/clubs/${sel.value}`);
    const chance = Math.max(C.robbery.min_chance, Math.min(C.robbery.max_chance, C.robbery.base_chance + d.robbery_power - v.robbery_power));
    root.querySelector("#rob-impact").innerHTML = `<div class="box"><div class="k">Chance</div><div class="v ${chance >= 50 ? "green" : "red"}">${chance} %</div></div><div class="box"><div class="k">Butin potentiel</div><div class="v gold">${money(Math.floor(v.cash * C.robbery.steal_rate))}</div></div><div class="box"><div class="k">Perte si échec</div><div class="v red">${money(Math.floor(c.cash * C.robbery.fail_loss_rate))}</div></div><div class="box"><div class="k">Puissances</div><div class="v">${d.robbery_power} vs ${v.robbery_power}</div></div>`;
  };
  if (!none) { robImpact(); root.querySelector("#t-rob").onchange = robImpact; }
  root.querySelector("#send").onclick = async () => {
    const tid = root.querySelector("#t-money").value, amount = Number(root.querySelector("#amount").value);
    const p = byId[tid]; if (!p || !amount) return toast({ icon: "♣", title: "Montant invalide", tone: "red" });
    if (!(await confirmBox({ title: "Confirmer le transfert", html: `<p>Envoyer <b class="gold">${money(amount)}</b> à <b>${esc(p.club)}</b> (${esc(p.display_name)}) ?</p>`, okLabel: "Envoyer" }))) return;
    try { const r = await act("/api/bank/transfer", { target_id: tid, amount }); toast({ icon: "💸", title: "Transfert effectué", text: `${money(r.amount)} envoyés à ${r.target_club}.`, tone: "gold" }); bank(root, { id: tid }); } catch {}
  };
  root.querySelectorAll("[data-pack]").forEach((b) => b.onclick = async () => {
    const tid = root.querySelector("#t-bottle").value, p = byId[tid], pack = C.bottle_packs[b.dataset.pack];
    if (!(await confirmBox({ title: pack.name, html: `<p>Envoyer un <b>${esc(pack.name)}</b> à <b>${esc(p.club)}</b> pour <b class="red">${money(pack.cost)}</b> ?<br><span class="muted small">La boîte reçoit ${money(pack.receiver_bonus)} et quelques clients.</span></p>`, okLabel: "Envoyer le pack" }))) return;
    try { const r = await act("/api/bank/bottle", { target_id: tid, pack_id: b.dataset.pack }); overlay(`<div class="big" style="font-size:48px">${pack.emoji}</div><h2>PACK ENVOYÉ</h2><p class="center">Vous venez d'envoyer un <b>${esc(pack.name)}</b> à <b>${esc(r.target_club)}</b>.</p><div class="lines"><div class="line"><span>Coût</span><b class="red">${money(-r.cost)}</b></div><div class="line"><span>La boîte reçoit</span><b class="green">${money(r.bonus, { sign: true })}</b></div><div class="line"><span>Clients offerts</span><b class="green">+${r.clients}</b></div></div><div class="row" style="justify-content:center"><button class="btn gold" data-close>Santé</button></div>`); bank(root, { id: tid }); } catch {}
  });
  const tt = root.querySelector("#trade-type");
  const refreshTradeValue = () => {
    const wrap = root.querySelector("#trade-value-wrap"), k = tt.value;
    if (k === "money") wrap.innerHTML = `<label>Montant (€)</label><input id="trade-value" type="number" min="1">`;
    else if (k === "bitcoin") wrap.innerHTML = `<label>Nombre de BTC</label><input id="trade-value" type="number" min="0.00000001" step="0.00000001" max="${c.bitcoin}">`;
    else { const list = k === "cars" ? c.cars : c.watches, items = C.shop[k]; wrap.innerHTML = `<label>Objet</label><select id="trade-value">${[...new Set(list)].map((id) => `<option value="${id}">${esc(items[id]?.name || id)}</option>`).join("") || `<option value="">Aucun objet disponible</option>`}</select>`; }
  };
  tt.onchange = refreshTradeValue;
  root.querySelector("#propose").onclick = async () => {
    const tid = root.querySelector("#t-trade").value, type = tt.value, value = root.querySelector("#trade-value").value;
    if (!value) return toast({ icon: "♣", title: "Valeur invalide", tone: "red" });
    try { const r = await act("/api/trades", { target_id: tid, type, value }, { silent: true }); toast({ icon: "♣", title: "Proposition envoyée", text: `${r.detail} → ${byId[tid]?.club}`, tone: "violet" }); bank(root, { id: tid }); } catch (e) { toast({ icon: "♣", title: "Impossible", text: e.message, tone: "red" }); }
  };
  root.querySelectorAll("[data-accept]").forEach((b) => b.onclick = async () => { try { await act(`/api/trades/${b.dataset.accept}/accept`); toast({ icon: "✅", title: "Trade accepté", tone: "green" }); bank(root, params); } catch {} });
  root.querySelectorAll("[data-refuse]").forEach((b) => b.onclick = async () => { try { await act(`/api/trades/${b.dataset.refuse}/refuse`); bank(root, params); } catch {} });
  root.querySelectorAll("[data-cancel]").forEach((b) => b.onclick = async () => { try { await act(`/api/trades/${b.dataset.cancel}/cancel`); bank(root, params); } catch {} });
  const rob = root.querySelector("#rob");
  if (rob) rob.onclick = async () => {
    const tid = root.querySelector("#t-rob").value, p = byId[tid];
    if (!(await confirmBox({ title: `Braquer ${p.club}`, html: `<p class="red">En cas d'échec vous perdez ${Math.round(C.robbery.fail_loss_rate * 100)} % de votre trésorerie et des clients. Vos hommes devront ensuite se faire oublier ${C.robbery.cooldown_services} services.</p>`, okLabel: "Lancer le braquage", tone: "red" }))) return;
    try {
      const r = await act("/api/robbery", { target_id: tid });
      const ok = r.result === "SUCCESS";
      overlay(`<div class="big" style="font-size:44px">${ok ? "💰" : "🚔"}</div><h2>${ok ? "BRAQUAGE RÉUSSI" : "BRAQUAGE RATÉ"}</h2><p class="center muted">${ok ? `Les hommes de ${esc(c.name)} ont frappé la boîte de ${esc(r.target_club)}.` : `Le coup contre la boîte de ${esc(r.target_club)} a mal tourné.`}</p>
        <div class="lines"><div class="line"><span>${ok ? "Butin" : "Pertes"}</span><b class="${ok ? "gold" : "red"}">${money(ok ? r.amount : -r.amount)}</b></div><div class="line"><span>Votre réputation</span><b class="${r.attacker_clients >= 0 ? "green" : "red"}">${r.attacker_clients >= 0 ? "+" : ""}${r.attacker_clients} clients</b></div><div class="line"><span>Boîte adverse</span><b class="${r.victim_clients >= 0 ? "green" : "red"}">${r.victim_clients >= 0 ? "+" : ""}${r.victim_clients} clients</b></div><div class="line"><span>Chance de réussite</span><b>${r.chance} %</b></div></div>
        <div class="row" style="justify-content:center"><button class="btn ${ok ? "gold" : "red"}" data-close>Continuer</button></div>`, { cls: ok ? "" : "combo" });
      bank(root, { id: tid });
    } catch {}
  };
}

// ==========================================================
// CLASSEMENT
// ==========================================================
export async function leaderboard(root, params) {
  const by = params?.id || "cash";
  const data = await api(`/api/leaderboard?by=${by}`);
  const me = S.state.user.id;
  const val = (r) => ({ cash: money(r.cash), net_worth: money(r.net_worth), income: money(r.income_24h), clients: num(r.total_clients), vip: num(r.total_vip_clients), showcases: num(r.showcases_done), level: `${r.level} · ${r.level_name}` }[by]);
  root.innerHTML = `
    ${head("Classement des boîtes de nuit", "Direction générale")}
    <div class="tabs" style="flex-wrap:wrap">${Object.entries(data.boards).map(([k, l]) => `<button class="${k === by ? "on" : ""}" onclick="location.hash='#/leaderboard/${k}'">${l}</button>`).join("")}</div>
    <div class="panel"><div class="table-wrap"><table class="table"><thead><tr><th>Rang</th><th>Club</th><th>Propriétaire</th><th>Niveau</th><th class="r">${esc(data.label)}</th><th class="r">Trésorerie</th><th></th></tr></thead>
      <tbody>${data.rows.map((r) => `<tr style="${r.user_id === me ? "background:var(--gold-dim)" : ""}"><td>${r.rank <= 3 ? `<span class="rank-medal">${["🥇", "🥈", "🥉"][r.rank - 1]}</span>` : `<span class="rank-n">#${r.rank}</span>`}</td><td><b>${esc(r.name)}</b>${r.online ? ` <span class="pill green"><span class="dot"></span></span>` : ""}</td><td class="muted">${esc(r.avatar)} ${esc(r.owner)}</td><td>${levelPill(r.level, r.level_name)}</td><td class="r num gold">${val(r)}</td><td class="r num muted">${money(r.cash)}</td><td class="r"><a class="btn sm ghost" href="#/${r.user_id === me ? "club" : "visit/" + r.user_id}">Voir</a></td></tr>`).join("") || `<tr><td colspan="7" class="muted">Aucune boîte de nuit enregistrée.</td></tr>`}</tbody></table></div>
      <p class="muted small">♣ Classement principal par trésorerie, puis niveau. Les équipements ne sont pas affichés.</p></div>`;
}

// ==========================================================
// PROFIL
// ==========================================================
export async function profile(root, params) {
  const id = Number(params.id || S.state.user.id);
  const p = await api(`/api/profile/${id}`);
  const C = cfg(), sh = C.shop, mine = id === S.state.user.id;
  const coll = (list, items, icon) => list.length ? [...new Set(list)].map((x) => `<div class="coll-item owned"><div class="i">${icon}</div><div class="n">${esc(items[x]?.name || x)}</div><div class="p">${money(items[x]?.price || 0)}</div>${list.filter((y) => y === x).length > 1 ? `<div class="q">×${list.filter((y) => y === x).length}</div>` : ""}</div>`).join("") : `<div class="muted small">Aucun.</div>`;
  const total = p.blackjack_wins + p.blackjack_losses;
  root.innerHTML = `
    ${head(`${esc(p.owner)}`, "Profil du joueur", mine ? `<a class="btn sm ghost" href="#/club">Ma boîte</a>` : `<a class="btn sm gold" href="#/visit/${id}">Visiter ${esc(p.name)}</a><a class="btn sm ghost" href="#/bank/${id}">Banque</a>`)}
    <div class="grid" style="grid-template-columns: 320px minmax(0,1fr)">
      <div class="panel accent-gold center"><div class="avatar lg" style="margin:0 auto 10px">${esc(p.avatar)}</div><h2>${esc(p.owner)}</h2><div class="muted small">@${esc(p.username || "")} · ${p.online ? `<span class="green">en ligne</span>` : `vu ${ago(p.last_seen || p.created_at)}`}</div>
        <div class="divider"></div><div class="kicker">Boîte</div><div style="font-family:var(--font-display);font-size:20px">${esc(p.name)}</div><div style="margin-top:6px">${levelPill(p.level, p.level_name)}</div>
        <div class="grid two" style="margin-top:12px"><div class="metric gold"><span class="k">Trésorerie</span><span class="v">${money(p.cash)}</span></div><div class="metric"><span class="k">Richesse totale</span><span class="v">${money(p.net_worth)}</span></div></div></div>
      <div>
        <div class="grid four" style="margin-bottom:14px">
          <div class="metric"><span class="k">Clients reçus</span><span class="v">${num(p.total_clients)}</span></div><div class="metric violet"><span class="k">VIP reçus</span><span class="v">${num(p.total_vip_clients)}</span></div><div class="metric"><span class="k">Showcases</span><span class="v">${num(p.showcases_done)}</span></div><div class="metric"><span class="k">Services</span><span class="v">${num(p.service_count)}</span></div>
          <div class="metric green"><span class="k">Blackjack victoires</span><span class="v">${num(p.blackjack_wins)}</span></div><div class="metric red"><span class="k">Blackjack défaites</span><span class="v">${num(p.blackjack_losses)}</span><span class="s">${total ? `${Math.round((p.blackjack_wins / total) * 100)} % de réussite` : ""}</span></div><div class="metric"><span class="k">Verres bus</span><span class="v">${num(p.drinks_taken)}</span></div><div class="metric gold"><span class="k">Cryptomonnaies</span><span class="v">${money(p.bitcoin * sh.bitcoin_price + Object.entries(p.crypto || {}).reduce((sum, [key, qty]) => sum + Number(qty) * (sh.crypto_quotes?.[key]?.price || 0), 0))}</span><span class="s">${Number(p.bitcoin || 0).toLocaleString("fr-FR", { maximumFractionDigits: 8 })} BTC${Object.entries(p.crypto || {}).filter(([, q]) => Number(q) > 0).map(([k, q]) => ` · ${Number(q).toLocaleString("fr-FR", { maximumFractionDigits: 8 })} ${esc(k)}`).join("")}</span></div>
        </div>
        <div class="grid two"><div class="panel"><h3>🚘 Garage</h3><div class="collection">${coll(p.cars, sh.cars, "🚘")}</div></div><div class="panel"><h3>⌚ Montres</h3><div class="collection">${coll(p.watches, sh.watches, "⌚")}</div></div></div>
        <div class="panel" style="margin-top:14px"><h3>Historique récent</h3><div class="list">${p.recent_services.length ? p.recent_services.map((s) => `<div class="feed-item"><span class="t">${clock(s.ts)}</span><span class="i">${s.showcase_artist ? "🎤" : "💰"}</span><span>Service #${s.service_no} · ${num(s.clients)} clients · ${s.vips} VIP · <b class="gold">${money(s.total)}</b>${s.showcase_artist ? ` · ${esc(s.showcase_artist)}` : ""}</span></div>`).join("") : `<div class="muted small">Pas encore de service.</div>`}</div></div>
      </div>
    </div>`;
  if (window.innerWidth < 900) root.querySelector(".grid[style]").style.gridTemplateColumns = "1fr";
}

// ==========================================================
// VISITE D'UN CLUB
// ==========================================================
export async function visit(root, params) {
  const id = Number(params.id);
  if (id === S.state.user.id) return club(root);
  const v = await api(`/api/clubs/${id}`);
  if (S.route.name !== "visit" || Number(S.route.params.id) !== id) return;
  const C = cfg(), me = myClub(), d = derived();
  const cars = C.shop.cars; let best = null; for (const cid of v.cars) { const it = cars[cid]; if (it && (!best || it.price > best.price)) best = it; }
  const chance = Math.max(C.robbery.min_chance, Math.min(C.robbery.max_chance, C.robbery.base_chance + d.robbery_power - v.robbery_power));
  const inside = S.cache[`inside-${id}`];
  const occ = Math.round(v.occupancy * 100);
  const music = v.showcase_pending ? `Showcase de ${v.showcase_artist} en direct` : v.equipment.includes("dj") ? "DJ résident aux platines" : v.equipment.includes("sound") ? "Sono haut de gamme à fond" : "Playlist maison";
  const ambience = occ >= 90 ? "La salle est pleine à craquer, la file déborde sur le trottoir." : occ >= 60 ? "Grosse affluence, le carré est animé et les bouteilles partent vite." : occ >= 25 ? "Ambiance correcte, la piste se remplit doucement." : "Soirée calme, quelques habitués au bar.";
  root.innerHTML = `
    <div class="visit-hero scene-wrap club-cinematic">
      <div class="title"><div><div class="kicker">Visite du club</div><h1>${esc(v.name)}</h1><div class="muted">par ${esc(v.avatar)} ${esc(v.owner)} ${v.online ? `<span class="pill green"><span class="dot"></span>en ligne</span>` : ""}</div></div><div class="row">${statusPill(v.status)}${levelPill(v.level, v.level_name)}</div></div>
      <div class="scene-overlay"><div class="chip">Fréquentation<b>${num(v.last_clients)}</b></div><div class="chip">Occupation<b>${occ} %</b></div><div class="chip gold">Entrée<b>${money(v.entry_price)}</b></div><div class="chip gold">Trésorerie<b>${money(v.cash)}</b></div></div>
    </div>
    <div class="row" style="margin:14px 0"><button class="btn gold lg" id="enter">${inside ? "🚪 Ressortir" : "🚪 Entrer"}</button><a class="btn ghost" href="#/profile/${id}">Profil du patron</a><a class="btn ghost" href="#/bank/${id}">🍾 Envoyer un pack</a><a class="btn ghost" href="#/bank/${id}">💸 Transférer · Trade</a><a class="btn red" href="#/bank/${id}">🚨 Braquer (${chance} %)</a></div>
    ${inside ? `<div class="panel accent-violet" style="margin-bottom:14px"><div class="kicker">À l'intérieur</div><h2>${esc(v.name)}</h2><p>${ambience}</p>
      <div class="grid four"><div class="metric"><span class="k">Musique</span><span class="v" style="font-size:16px">${esc(music)}</span></div><div class="metric"><span class="k">File d'attente</span><span class="v">${Math.round(v.occupancy * 40)} pers.</span></div><div class="metric violet"><span class="k">VIP ce soir</span><span class="v">${v.last_vips}</span></div><div class="metric"><span class="k">Activité</span><span class="v" style="font-size:16px">${v.showcase_pending ? "🎤 Showcase en cours" : v.last_event ? esc(v.last_event.title) : "Soirée normale"}</span></div></div>
      ${v.equipment.length ? `<div class="row" style="margin-top:10px">${v.equipment.map((e) => `<span class="pill">${C.equipment[e]?.emoji || ""} ${esc(C.equipment[e]?.name || e)}</span>`).join("")}</div>` : `<div class="muted small" style="margin-top:8px">Aucun équipement particulier.</div>`}</div>` : ""}
    <div class="grid three">
      <div class="panel"><h3>Informations publiques</h3><div class="list">
        <div class="row between"><span class="muted">Niveau</span><b>${v.level} · ${esc(v.level_name)}</b></div><div class="row between"><span class="muted">Prix d'entrée</span><b>${money(v.entry_price)}</b></div><div class="row between"><span class="muted">Dernier service</span><b>${num(v.last_clients)} clients · ${v.last_vips} VIP</b></div><div class="row between"><span class="muted">Clients reçus</span><b>${num(v.total_clients)}</b></div><div class="row between"><span class="muted">Showcases</span><b>${v.showcases_done}</b></div><div class="row between"><span class="muted">Équipements</span><b>${v.equipment_count}/${Object.keys(C.equipment).length}</b></div><div class="row between"><span class="muted">Puissance (défense)</span><b>${v.robbery_power}</b></div></div></div>
      <div class="panel"><h3>Activité</h3>${v.showcase_pending ? `<div class="notice gold">🎤 <b>${esc(v.showcase_artist)}</b> passe au prochain service.</div>` : v.last_showcase ? `<div class="small">Dernier showcase : <b>${esc(v.last_showcase.artist)}</b> (${v.last_showcase.clients >= 0 ? "+" : ""}${v.last_showcase.clients} clients, ${ago(v.last_showcase.time)})</div>` : `<div class="muted small">Aucun showcase récent.</div>`}${v.last_event ? `<div class="notice red" style="margin-top:8px"><b>${esc(v.last_event.title)}</b> · ${ago(v.last_event.time)}</div>` : ""}</div>
      <div class="panel"><h3>Comparé à ${esc(me.name)}</h3><div class="list"><div class="row between"><span class="muted">Trésorerie</span><b class="${me.cash >= v.cash ? "green" : "red"}">${money(me.cash - v.cash, { sign: true })}</b></div><div class="row between"><span class="muted">Niveau</span><b>${me.level} vs ${v.level}</b></div><div class="row between"><span class="muted">Fréquentation</span><b class="${me.last_clients >= v.last_clients ? "green" : "red"}">${me.last_clients - v.last_clients >= 0 ? "+" : ""}${num(me.last_clients - v.last_clients)}</b></div><div class="row between"><span class="muted">Chance de braquage</span><b class="${chance >= 50 ? "green" : "red"}">${chance} %</b></div></div></div>
    </div>`;
  // Contexte audio : la vue consultée est CE club (pas le mien) → son showcase à lui, uniquement ici.
  audio.setView(inside ? { clubId: id, level: v.level, showcase: v.showcase_screen } : null);
  root.querySelector("#enter").onclick = () => { S.cache[`inside-${id}`] = !inside; if (inside) audio.setView(null); visit(root, params); if (!inside) toast({ icon: "🚪", title: `Bienvenue au ${v.name}`, text: ambience, tone: "violet" }); };
}

// ==========================================================
// NOTIFICATIONS
// ==========================================================
export async function notifications(root) {
  const data = await api("/api/notifications");
  root.innerHTML = `${head("Centre de notifications", `${data.unread} non lue${data.unread > 1 ? "s" : ""}`, `<button class="btn sm ghost" id="readall">Tout marquer comme lu</button>`)}
    <div class="list">${data.notifications.length ? data.notifications.map((n) => `<div class="notif ${n.read ? "" : "unread"}"><div class="i">${esc(n.icon)}</div><div><div class="t">${esc(n.title)}</div><div class="d">${esc(n.text)}</div></div><div class="when">${dateTime(n.ts)}</div></div>`).join("") : `<div class="empty-state">${icon("notifications")}<h2>Une nuit tranquille.</h2><p>Vos nouvelles notifications apparaîtront ici.</p></div>`}</div>`;
  const mark = async () => { const r = await api("/api/notifications/read", { method: "POST", body: {} }); S.unread = r.unread; };
  root.querySelector("#readall").onclick = async () => { await mark(); notifications(root); };
  await mark();
  renderTopbar();
}

// ==========================================================
// PROGRESSION / STATISTIQUES
// ==========================================================
export async function levels(root) {
  const c = myClub(), d = derived(), C = cfg();
  root.innerHTML = `${head("Progression & statistiques", esc(c.name))}
    <div class="grid two">
      <div class="panel"><h3>Niveaux du club</h3><div class="level-path">${C.levels.map((l) => `<div class="level-step ${l.level < c.level ? "done" : l.level === c.level ? "current" : ""}"><div class="n">${l.level < c.level ? "✓" : l.level}</div><div><div class="name" style="color:${LEVEL_THEMES[l.level].neon}">${LEVEL_THEMES[l.level].symbol} ${esc(l.name)}</div><div class="meta">Bonus ${pct(l.income_mult - 1)} · ${l.clients_min}–${l.clients_max} clients/service · entrée max ${money(l.max_entry)} · showcase ${pct(l.showcase_mult - 1)}</div></div><div class="num ${l.level === c.level + 1 ? "gold" : "muted"}">${l.upgrade_cost ? money(l.upgrade_cost) : "—"}</div></div>`).join("")}</div>
        ${d.next_level ? `<div class="divider"></div><div class="row between"><div><div class="kicker">Prochain niveau</div><b>${esc(d.next_level.name)}</b> — ${money(d.next_level.upgrade_cost)}</div><button class="btn ${c.cash >= d.next_level.upgrade_cost ? "gold" : "ghost"}" id="up" ${c.cash >= d.next_level.upgrade_cost ? "" : "disabled"}>Améliorer</button></div><div class="bar" style="margin-top:8px"><i style="width:${Math.min(100, (c.cash / d.next_level.upgrade_cost) * 100).toFixed(1)}%"></i></div>` : `<div class="notice gold" style="margin-top:12px">♛ Le Olivia — standing maximum.</div>`}</div>
      <div>
        <div class="grid two" style="margin-bottom:14px"><div class="metric"><span class="k">Services</span><span class="v">${num(c.service_count)}</span></div><div class="metric"><span class="k">Clients reçus</span><span class="v">${num(c.total_clients)}</span></div><div class="metric violet"><span class="k">VIP reçus</span><span class="v">${num(c.total_vip_clients)}</span></div><div class="metric"><span class="k">Showcases</span><span class="v">${num(c.showcases_done)}</span></div><div class="metric gold"><span class="k">Richesse totale</span><span class="v" data-own-wealth>${money(d.net_worth)}</span></div><div class="metric"><span class="k">Estimation / service</span><span class="v">${money(d.estimate.total)}</span><span class="s">≈ ${num(d.estimate.clients)} clients</span></div></div>
        <div class="panel"><h3>Économie actuelle</h3><div class="list small">
          <div class="row between"><span class="muted">Bonus général (standing)</span><b class="green">${pct(d.income_mult - 1)}</b></div><div class="row between"><span class="muted">Bar par service</span><b>${money(C.bar_min)} – ${money(C.bar_max)} × ${d.income_mult} × ${(1 + d.bonuses.bar).toFixed(2)}</b></div><div class="row between"><span class="muted">Clients par service</span><b>${d.client_range[0]} – ${d.client_range[1]} × ${d.price_client_mult.toFixed(3)}</b></div><div class="row between"><span class="muted">Dépense VIP</span><b>${money(C.vip_base_spend)} × ${d.income_mult} × ${(1 + d.bonuses.vip).toFixed(2)}</b></div><div class="row between"><span class="muted">VIP par service</span><b>${Math.round(C.vip_roll.two * 100)} % deux · ${Math.round(C.vip_roll.one * 100)} % un</b></div><div class="row between"><span class="muted">Événements</span><b>toutes les ${C.event_interval / 60} min, ${Math.round(C.event_chance * 100)} %</b></div><div class="row between"><span class="muted">Petits événements</span><b>${Math.round(C.fun_event_chance * 100)} % par service</b></div></div></div>
      </div>
    </div>`;
  const up = root.querySelector("#up"); if (up) up.onclick = () => upgradeDialog();
}

// ==========================================================
// PARAMÈTRES (audio)
// ==========================================================
export async function settings(root) {
  const hostAccess = await api("/api/auth/local-admin");
  const p = audio.prefs;
  const st = audio.status();
  const slider = (key, icon, label, hint) => `<div class="setting"><div class="row between"><label for="s-${key}">${icon} ${label}</label><span class="num" id="v-${key}">${Math.round((p[key] ?? 0) * 100)} %</span></div>
    <input type="range" id="s-${key}" data-pref="${key}" min="0" max="100" value="${Math.round((p[key] ?? 0) * 100)}"><div class="small muted">${hint}</div></div>`;
  root.innerHTML = `${head("Paramètres", "Préférences du joueur")}
    <div class="grid two">
      <div class="panel accent-gold"><h3>🎚️ Audio</h3>
        ${st.blocked ? `<div class="notice gold" style="margin-bottom:10px">Le navigateur bloque le son tant que vous n'avez pas interagi avec la page. <button class="btn sm gold" id="unlock">🔊 Activer le son</button></div>` : ""}
        <div class="row between" style="margin-bottom:10px"><span>Couper tous les sons</span><button class="btn ${p.muted ? "red" : "ghost"}" id="mute">${p.muted ? "🔇 MUTE activé" : "🔊 Son actif — MUTE"}</button></div>
        ${slider("master", "🔊", "Volume général", "S'applique à tout.")}
        ${slider("showcase", "🎵", "Volume showcase", "Extraits joués uniquement dans la vue du club concerné.")}
        ${slider("ambient", "🎧", "Volume ambiance", "Ambiance du club consulté ; baisse automatiquement pendant un showcase.")}
        ${slider("notifications", "🔔", "Volume notifications", "Sons d'interface, services, notifications.")}
        ${slider("fx", "⚡", "Volume FX", "FX critiques : braquages (événement mondial) et événements spéciaux.")}
        <div class="divider"></div>
        <div class="row"><button class="btn sm ghost" data-test="robbery">Tester FX braquage</button><button class="btn sm ghost" data-test="showcase">Tester showcase</button><button class="btn sm ghost" data-test="ambient">Tester ambiance</button><button class="btn sm ghost" data-test="notify">Tester notification</button></div>
        <p class="muted small" style="margin-top:10px">Préférences sauvegardées dans votre profil (et localement).</p></div>
      <div>
        <div class="panel"><h3>Comment fonctionne le son</h3>
          <div class="list small">
            <div class="notice red"><b>🚨 Braquage — GLOBAL.</b> Quand un braquage est validé par le serveur, l'événement <code>robbery_created</code> est diffusé à tous les joueurs connectés (braqueur compris) : FX + notification synchronisés, où que vous soyez dans le jeu. Anti-spam : au plus ${audio.settings.fx_max} sons par ${audio.settings.fx_window} s, volumes décroissants — l'événement de jeu n'est jamais bloqué.</div>
            <div class="notice"><b>🎤 Showcase — LOCAL.</b> Le son d'un showcase ne joue que si vous consultez la vue du club concerné (« Ma boîte » ou « Visite »). Changer de page ou de club coupe le son (fondu court). Chaque club a son propre état ; plusieurs showcases simultanés ne se mélangent jamais. Le serveur choisit les clips YouTube : vidéo et musique sont partagées uniquement entre les joueurs à l’intérieur de la même boîte.</div>
            <div class="notice gold"><b>🎧 Ambiance.</b> Propre à la vue du club ; réduite à ${Math.round(audio.settings.ducking * 100)} % pendant un extrait de showcase, puis revient progressivement.</div>
          </div></div>
        <div class="panel" style="margin-top:14px"><h3>État</h3><div class="list small">
          <div class="row between"><span class="muted">Moteur audio</span><b class="${st.ready ? "green" : "red"}">${st.ready ? "actif" : st.blocked ? "en attente d'interaction" : "inactif"}</b></div>
          <div class="row between"><span class="muted">Vue de club active</span><b>${st.view != null ? `club #${st.view}` : "aucune"}</b></div>
          <div class="row between"><span class="muted">Showcase en lecture</span><b>${st.showcase || "—"}</b></div>
          <div class="row between"><span class="muted">Ambiance</span><b>${st.ambient ? "en lecture" : "—"}</b></div></div></div>
      </div>
    </div>`;
  root.insertAdjacentHTML("beforeend", `<div class="panel host-access" style="margin-top:18px"><div><div class="eyebrow">ORDINATEUR HÔTE</div><h3>Administration du jeu</h3><p class="muted small">${S.state.user.is_admin ? "Votre compte peut gérer les joueurs et supprimer une boîte problématique." : hostAccess.available ? "Vous êtes sur l’ordinateur qui héberge le jeu. Vous pouvez activer l’administration pour votre compte." : "Pour activer l’administration depuis le PC qui héberge le jeu, ouvrez le jeu avec l’adresse localhost et connectez-vous à votre compte."}</p></div>${S.state.user.is_admin ? `<a class="btn violet" href="#/admin">${icon("admin")} Ouvrir l’administration</a>` : hostAccess.available ? `<button class="btn violet" id="claim-admin">${icon("admin")} Activer mon accès administrateur</button>` : ""}</div>`);
  const claim = root.querySelector("#claim-admin");
  if (claim) claim.onclick = async () => {
    claim.disabled = true;
    try { await act("/api/auth/local-admin", {}); location.hash = "#/admin"; await render(); toast({ title: "Accès administrateur activé", text: "Ce compte peut maintenant gérer les établissements.", tone: "violet" }); }
    catch { claim.disabled = false; }
  };
  root.querySelectorAll("[data-pref]").forEach((inp) => inp.oninput = () => { audio.setPref(inp.dataset.pref, Number(inp.value) / 100); root.querySelector(`#v-${inp.dataset.pref}`).textContent = `${inp.value} %`; });
  root.querySelector("#mute").onclick = () => { audio.toggleMute(); settings(root); };
  const unlock = root.querySelector("#unlock"); if (unlock) unlock.onclick = () => { audio.unlock(); setTimeout(() => settings(root), 300); };
  root.querySelectorAll("[data-test]").forEach((b) => b.onclick = () => { audio.test(b.dataset.test); });
}

// ==========================================================
// ADMIN
// ==========================================================
export async function admin(root) {
  if (!S.state.user.is_admin) { root.innerHTML = `<div class="panel">Réservé à l'administration.</div>`; return; }
  const [conf, { users }, { assets }] = await Promise.all([api("/api/admin/config"), api("/api/admin/users"), api("/api/admin/audio")]);
  const byCat = {};
  for (const a of assets) (byCat[a.category] = byCat[a.category] || []).push(a);
  root.innerHTML = `${head("Administration", "Panneau réservé")}
    <section class="panel" style="margin-bottom:22px"><div class="row between"><div><div class="eyebrow">COMPTES & PROGRESSIONS</div><h2>Sauvegarde complète</h2><p class="muted small">Téléchargez une copie de tous les comptes, clubs et historiques avant une mise à jour. Conservez ce fichier en privé : il contient aussi les informations de connexion. Une copie téléchargée ne remplace pas un stockage persistant sur le serveur.</p></div><a class="btn violet" href="/api/admin/backup" download>Télécharger la sauvegarde</a></div></section>
    <section class="panel club-moderation" style="margin-bottom:22px"><div class="row between"><div><div class="eyebrow">GESTION DES ÉTABLISSEMENTS</div><h2>Les boîtes de la ville</h2></div><span class="pill violet">${users.filter(u => u.club).length} établissements</span></div><p class="muted small">Supprimez une boîte précise si elle pose problème. Son propriétaire conserve son compte et pourra repartir avec un nouvel établissement.</p><div class="grid three">${users.filter(u => u.club).map(u => `<article class="moderation-card"><div class="row between">${icon("club")}<span class="pill">Niveau ${u.level}</span></div><h3>${esc(u.club)}</h3><p class="muted small">@${esc(u.username)} · ${money(u.cash)}</p>${u.id === S.state.user.id ? `<span class="pill violet">Votre établissement</span>` : `<button class="btn red sm" data-delete-club="${u.id}">Supprimer cette boîte</button>`}</article>`).join("") || `<p class="muted">Aucun établissement.</p>`}</div></section>
    <div class="grid two">
      <div class="panel" style="grid-column:1 / -1"><h3>🎬 Clips YouTube des showcases</h3>
        <p class="muted small">Le catalogue propose des clips pour chaque artiste. Ajoute des liens pour enrichir les prochains showcases : la même diffusion sera visible et audible par les joueurs à l'intérieur de la boîte concernée.</p>
        <label>Artiste<select id="youtube-artist">${conf.effective.artist_order.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join("")}</select></label>
        <label>Liens YouTube<textarea id="youtube-urls" placeholder="Un lien YouTube par ligne"></textarea></label>
        <button class="btn gold" id="youtube-add">Ajouter les clips</button><span id="youtube-result" class="small" role="status"></span>
      </div>
      <div class="panel" style="grid-column: 1 / -1"><div class="row between"><h3>🎚️ Assets audio (${assets.length})</h3><button class="btn sm gold" id="rescan">Rescanner les assets</button></div>
        <p class="muted small">Dossier <code>web/audio/</code> : <code>robbery/</code>, <code>showcases/&lt;artiste&gt;/</code>, <code>ambient/</code>, <code>ui/</code>, <code>events/</code>. Déposez des fichiers .mp3/.ogg/.wav puis rescannez. Les dossiers d'artistes vides utilisent <code>showcases/_placeholder/</code>. Aucun contenu protégé n'est fourni : les placeholders sont synthétisés (<code>tools/make_placeholder_audio.py</code>).</p>
        <div class="grid three">${Object.entries(byCat).map(([cat, list]) => `<div><div class="kicker">${cat}</div><div class="list">${list.map((a) => `<div class="item tight" style="padding:6px 10px"><div class="body"><div class="small">${esc(a.file_url.replace("audio/", ""))}</div><div class="small muted">${a.key} · ${a.duration ? a.duration.toFixed(1) + " s" : "?"} · poids ${a.weight}</div></div><div class="actions"><button class="btn sm ${a.enabled ? "green" : "ghost"}" data-asset="${a.id}" data-enabled="${a.enabled ? 0 : 1}">${a.enabled ? "Activé" : "Désactivé"}</button></div></div>`).join("")}</div></div>`).join("")}</div></div>
      <div class="panel"><h3>Joueurs</h3><div class="table-wrap"><table class="table"><thead><tr><th>ID</th><th>Utilisateur</th><th>Club</th><th class="r">Niv.</th><th class="r">Trésorerie</th><th></th></tr></thead><tbody>${users.map((u) => `<tr><td class="muted">${u.id}</td><td>${esc(u.username)}${u.is_admin ? " <span class='pill gold'>admin</span>" : ""}${u.discord_id ? ` <span class='pill violet'>discord</span>` : ""}</td><td>${esc(u.club || "—")}</td><td class="r">${u.level ?? "—"}</td><td class="r num">${u.cash != null ? money(u.cash) : "—"}</td><td class="r"><button class="btn sm ghost" data-grant="${u.id}">€</button> <button class="btn sm ghost" data-pass="${u.id}">🔑</button> <button class="btn sm ghost" data-promote="${u.id}" data-admin="${u.is_admin ? 0 : 1}">${u.is_admin ? "⬇" : "⬆"}</button></td></tr>`).join("")}</tbody></table></div></div>
      <div class="panel" style="border-color:rgba(190,60,70,.55);background:linear-gradient(180deg,rgba(100,20,30,.12),rgba(20,10,15,.18))"><div class="row between"><div><h3>⚠️ Réinitialiser le serveur</h3><p class="muted small" style="margin:6px 0 0">Supprime tous les comptes joueurs, clubs, argent, historiques, transactions, notifications, échanges, événements, braquages et réglages persistants. Ton compte administrateur reste disponible pour te reconnecter.</p></div><button class="btn sm" id="reset-server" style="border-color:#a83d4a">Réinitialiser le serveur</button></div></div>
      <div class="panel"><h3>Configuration (surcharges JSON)</h3><p class="muted small">Toute clé de la configuration peut être surchargée (prix, bonus, coûts, artistes, managers, équipements, événements, taux, probabilités, cooldowns, niveaux, mode blackjack…). Fusion profonde avec les valeurs par défaut du bot.</p>
        <div class="row" style="margin-bottom:8px"><button class="btn sm ghost" id="bj-mode">Blackjack : ${conf.effective.web.blackjack_mode === "auto" ? "original (auto)" : "table interactive"} — basculer</button><button class="btn sm ghost" id="show-eff">Voir la config effective</button></div>
        <textarea class="code" id="ov">${esc(JSON.stringify(conf.overrides, null, 2))}</textarea>
        <div class="row" style="margin-top:8px"><button class="btn gold" id="save">Enregistrer</button><button class="btn ghost" id="reset">Réinitialiser aux valeurs du bot</button></div><div class="error" id="err"></div></div>
      <div class="panel"><h3>Importer les joueurs du bot Discord</h3><p class="muted small">Collez le contenu de <code>nightclub_data.json</code>. Chaque joueur Discord devient un compte <code>discord_&lt;id&gt;</code> avec son club à l'identique ; définissez ensuite son mot de passe (🔑). Plus tard, Discord pourra devenir une méthode de connexion.</p><textarea class="code" id="imp" style="min-height:160px" placeholder='{ "734865069904756766": { "name": "…", "cash": 0, … } }'></textarea><button class="btn violet" style="margin-top:8px" id="import">Importer</button><div id="imp-res" class="small" style="margin-top:8px"></div></div>
      <div class="panel"><h3>Config effective</h3><textarea class="code" id="eff" readonly style="min-height:300px">${esc(JSON.stringify(conf.effective, null, 2))}</textarea></div>
    </div>`;
  root.querySelectorAll("[data-delete-club]").forEach(button => button.onclick = () => {
    const target = users.find(u => u.id === Number(button.dataset.deleteClub));
    if (!target) return;
    const close = overlay(`<div class="eyebrow center">GESTION DES ÉTABLISSEMENTS</div><h2>Supprimer ${esc(target.club)} ?</h2><p class="muted small">La boîte, sa progression et son historique financier seront supprimés. Ses échanges en attente seront annulés. Le compte @${esc(target.username)} est conservé. Cette action est définitive.</p><div class="field"><label for="delete-club-name">Recopiez le nom de la boîte pour confirmer</label><input id="delete-club-name" autocomplete="off" placeholder="${esc(target.club)}"></div><div class="row between"><button class="btn ghost" data-close>Annuler</button><button class="btn red" id="delete-club-confirm" disabled>Supprimer cette boîte</button></div><p id="delete-club-error" class="error" role="alert"></p>`);
    const input = document.getElementById("delete-club-name"), confirm = document.getElementById("delete-club-confirm");
    input.oninput = () => { confirm.disabled = input.value !== target.club; };
    confirm.onclick = async () => {
      confirm.disabled = true;
      try { await api(`/api/admin/clubs/${target.id}`, { method: "DELETE", body: { confirm_name: input.value } }); close(); toast({ title: "Boîte supprimée", text: target.club, tone: "violet" }); await admin(root); }
      catch (e) { document.getElementById("delete-club-error").textContent = e.message; confirm.disabled = input.value !== target.club; }
    };
    input.focus();
  });
  const save = async (ov) => { try { await api("/api/admin/config", { method: "PUT", body: { overrides: ov } }); toast({ icon: "⚙", title: "Configuration enregistrée", tone: "gold" }); await refresh(); admin(root); } catch (e) { root.querySelector("#err").textContent = e.message; } };
  root.querySelector("#youtube-add").onclick = async () => {
    const button = root.querySelector("#youtube-add"), result = root.querySelector("#youtube-result");
    button.disabled = true;
    result.textContent = "Ajout en cours…";
    try {
      const data = await api("/api/admin/audio/youtube", { method: "POST", body: { artist: root.querySelector("#youtube-artist").value, urls: root.querySelector("#youtube-urls").value } });
      result.textContent = `${data.added.length} clip(s) ajouté(s), ${data.skipped.length} déjà présent(s). Disponibles au prochain showcase.`;
    } catch (e) { result.textContent = e.message; }
    finally { button.disabled = false; }
  };
  root.querySelector("#save").onclick = () => { try { save(JSON.parse(root.querySelector("#ov").value || "{}")); } catch (e) { root.querySelector("#err").textContent = "JSON invalide : " + e.message; } };
  root.querySelector("#reset").onclick = async () => { if (await confirmBox({ title: "Réinitialiser", html: "<p>Toutes les surcharges seront supprimées.</p>", tone: "red" })) save({}); };
  root.querySelector("#reset-server").onclick = async () => {
    const ok = await confirmBox({
      title: "Réinitialisation TOTALE",
      html: "<p><b>Cette action est irréversible.</b></p><p>Tous les joueurs et toutes leurs sauvegardes seront supprimés. Les données de jeu seront recréées à zéro.</p><p>Ton compte administrateur sera conservé.</p>",
      tone: "red"
    });
    if (!ok) return;
    try {
      await api("/api/admin/reset-server", { method: "POST" });
      toast({ icon: "⚠️", title: "Serveur réinitialisé", text: "Toutes les sauvegardes ont été supprimées.", tone: "gold" });
      await refresh();
      admin(root);
    } catch (e) {
      toast({ icon: "♣", title: "Échec de la réinitialisation", text: e.message, tone: "red" });
    }
  };
  root.querySelector("#bj-mode").onclick = () => { const ov = conf.overrides || {}; ov.web = { ...(ov.web || {}), blackjack_mode: conf.effective.web.blackjack_mode === "auto" ? "interactive" : "auto" }; save(ov); };
  root.querySelector("#show-eff").onclick = () => root.querySelector("#eff").scrollIntoView({ behavior: "smooth" });
  root.querySelectorAll("[data-grant]").forEach((b) => b.onclick = async () => { const v = prompt("Montant à ajouter (négatif pour retirer) :", "1000000"); if (v == null) return; try { await api("/api/admin/grant", { method: "POST", body: { user_id: b.dataset.grant, amount: Number(v) } }); toast({ icon: "€", title: "Trésorerie ajustée", tone: "gold" }); admin(root); } catch (e) { toast({ icon: "♣", title: e.message, tone: "red" }); } });
  root.querySelectorAll("[data-pass]").forEach((b) => b.onclick = async () => { const v = prompt("Nouveau mot de passe (6 caractères min.) :"); if (!v) return; try { await api("/api/admin/password", { method: "POST", body: { user_id: b.dataset.pass, password: v } }); toast({ icon: "🔑", title: "Mot de passe défini", tone: "gold" }); } catch (e) { toast({ icon: "♣", title: e.message, tone: "red" }); } });
  root.querySelectorAll("[data-promote]").forEach((b) => b.onclick = async () => { try { await api("/api/admin/promote", { method: "POST", body: { user_id: b.dataset.promote, is_admin: b.dataset.admin === "1" } }); admin(root); } catch (e) { toast({ icon: "♣", title: e.message, tone: "red" }); } });
  root.querySelector("#rescan").onclick = async () => { try { const r = await api("/api/admin/audio/rescan", { method: "POST" }); toast({ icon: "🎚️", title: "Assets rescannés", text: `${r.added} ajouté(s), ${r.removed} retiré(s), ${r.total} au total.`, tone: "gold" }); admin(root); } catch (e) { toast({ icon: "♣", title: e.message, tone: "red" }); } };
  root.querySelectorAll("[data-asset]").forEach((b) => b.onclick = async () => { try { await api(`/api/admin/audio/${b.dataset.asset}`, { method: "PUT", body: { enabled: b.dataset.enabled === "1" } }); admin(root); } catch (e) { toast({ icon: "♣", title: e.message, tone: "red" }); } });
  root.querySelector("#import").onclick = async () => { try { const data = JSON.parse(root.querySelector("#imp").value); const r = await api("/api/admin/import-bot", { method: "POST", body: { data } }); root.querySelector("#imp-res").innerHTML = `<b class="green">${r.imported.length} importé(s)</b>, ${r.skipped.length} ignoré(s).<br>${r.imported.map((i) => `${esc(i.club)} → ${esc(i.username)}`).join("<br>")}`; } catch (e) { root.querySelector("#imp-res").innerHTML = `<span class="red">${esc(e.message)}</span>`; } };
}
