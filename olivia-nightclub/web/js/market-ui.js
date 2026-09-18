import { S, api, act, money, esc, now, toast, confirmBox } from "./app.js";
import { icon } from "./design.js";

export const units = value => Number(value || 0).toLocaleString("fr-FR", { maximumFractionDigits: 8 });
export const quoteMoney = value => value == null ? "—" : Number(value).toLocaleString("fr-FR", {
  style: "currency", currency: "EUR", maximumFractionDigits: Number(value) < 1 ? 6 : 2,
});
const held = (club, symbol) => Number(symbol === "BTC" ? club.bitcoin : club.crypto?.[symbol]) || 0;
const change = value => `${value >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)} %`;
const date = ts => new Date(ts * 1000).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const fresh = row => !!row?.updated_at && now() - row.updated_at >= 0 && now() - row.updated_at <= 90;
const movement = value => `<span class="market-change ${value >= 0 ? "green" : "red"}">${change(value)}</span>`;

export function chart(points = [], range = 86400, stamp = now()) {
  const visible = points.filter(p => p[0] >= stamp - range && Number.isFinite(p[1]));
  if (visible.length < 2) return `<div class="market-chart-empty">La courbe se construit avec les cours reçus.<br><span>Les prochains points apparaîtront automatiquement.</span></div>`;
  const values = visible.map(p => p[1]), low = Math.min(...values), high = Math.max(...values);
  const gap = high - low || Math.max(high * .001, .000001);
  const t0 = visible[0][0], t1 = visible.at(-1)[0];
  const xy = visible.map(p => [12 + (p[0] - t0) / (t1 - t0 || 1) * 696, 184 - (p[1] - low) / gap * 158]);
  const path = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
  const up = values.at(-1) >= values[0], tone = up ? "market-up" : "market-down";
  return `<div class="market-chart ${tone}"><div class="row between small muted"><span>Haut ${quoteMoney(high)}</span><span>Bas ${quoteMoney(low)}</span></div>
    <svg viewBox="0 0 720 205" role="img" aria-label="Courbe du cours : de ${esc(quoteMoney(values[0]))} à ${esc(quoteMoney(values.at(-1)))}">
      <path class="market-grid" d="M12 26H708 M12 105H708 M12 184H708"/>
      <path class="market-area" d="${path} L708 205 L12 205 Z"/>
      <path class="market-line" d="${path}"/>
      <circle cx="${xy.at(-1)[0]}" cy="${xy.at(-1)[1]}" r="4" class="market-dot"/>
    </svg><div class="row between small muted"><span>${date(t0)}</span><span>${date(t1)}</span></div></div>`;
}

function valueOfPortfolio(club, shop) {
  let total = held(club, "BTC") * (shop.bitcoin_price || 0);
  for (const [symbol, quantity] of Object.entries(club.crypto || {})) {
    if (symbol !== "BTC") total += Number(quantity) * (shop.crypto_quotes?.[symbol]?.price || 0);
  }
  return total;
}

export function updateMarketView() {
  const root = document.querySelector("#market-shop");
  if (!root || !S.state?.club || !S.cache.markets) return;
  const m = S.cache.markets, club = S.state.club, sh = S.state.config.shop;
  const tab = root.dataset.tab, range = S.cache.marketRange || 86400;
  root.querySelector("[data-market-cash]").textContent = money(club.cash);
  root.querySelector("[data-market-wealth]").textContent = money(Math.floor(valueOfPortfolio(club, sh)
    + ["cars", "watches"].reduce((sum, cat) => sum + (club[cat] || []).reduce((v, id) => v + (sh[cat][id]?.price || 0), 0), 0)));
  if (tab === "crypto") {
    const symbol = S.cache.marketSymbol || "BTC", row = m.crypto[symbol] || {}, ok = fresh(row);
    root.querySelector("[data-market-status]").innerHTML = `${ok ? (row.leverage ? '<span class="live-dot"></span> Bitcoin du jeu ×5 · référence Kraken' : '<span class="live-dot"></span> Cours réels · Kraken') : 'Cours en attente · échanges suspendus'} <span class="muted">/ EUR · actualisation 15 s</span>`;
    root.querySelectorAll("[data-coin]").forEach(button => {
      const coin = m.crypto[button.dataset.coin];
      button.classList.toggle("selected", button.dataset.coin === symbol);
      button.querySelector("[data-coin-price]").textContent = quoteMoney(coin.price);
      button.querySelector("[data-coin-change]").innerHTML = coin.price == null ? "En attente" : movement(coin.change_pct);
    });
    root.querySelector("[data-market-display]").innerHTML = `<div class="row between"><div><div class="eyebrow">${esc(row.name || symbol)}${row.leverage ? " DU JEU ×5" : ""} / EUR</div><h2 class="market-price">${quoteMoney(row.price)}</h2></div><div>${movement(row.change_pct)}<div class="small muted">${row.leverage ? "historique du jeu (max. 24 h)" : "depuis 00 h UTC"}</div></div></div>
      ${row.leverage ? `<div class="market-amplified">Variations amplifiées ×5 · cours fictif du jeu.<br>Bitcoin réel : <b>${quoteMoney(row.market_price)}</b>. Votre prix de jeu monte et baisse plus vite.</div>` : ""}${chart(row.history, range)}<p class="market-caption">${row.updated_at ? `Dernière réception à ${date(row.updated_at)}` : "Connexion au marché…"} · courbe sur ${range === 3600 ? "1 h" : "24 h"}, points de 5 min et dernier cours.</p>`;
    root.querySelector("[data-trade-title]").textContent = `${symbol} · ${units(held(club, symbol))} détenu(s)`;
    const amount = Number(root.querySelector("#market-qty").value), fee = m.fee_rate;
    const valid = Number.isFinite(amount) && amount > 0 && amount <= 1000000;
    const cost = Math.ceil(amount * (row.price || 0) * (1 + fee));
    const gain = Math.floor(amount * (row.price || 0) * (1 - fee));
    root.querySelector("[data-trade-estimate]").textContent = valid && row.price ? `Achat ≈ ${money(cost)} · revente ≈ ${money(gain)}` : "Saisissez une quantité.";
    root.querySelector("#market-buy").disabled = !ok || !valid || cost > club.cash || cost < 1;
    root.querySelector("#market-sell").disabled = !ok || !valid || amount > held(club, symbol) || gain < 1;
    const positions = Object.entries(m.crypto).filter(([key]) => held(club, key) > 0);
    root.querySelector("[data-market-portfolio]").innerHTML = `<div class="row between"><h3>Mon portefeuille</h3><b class="gold">${money(Math.floor(valueOfPortfolio(club, sh)))}</b></div>${positions.map(([key, quote]) => `<div class="portfolio-row"><div><b>${esc(key)}</b><span class="muted small">${units(held(club, key))} unités</span></div><div><b>${quote.price ? money(Math.floor(held(club, key) * quote.price)) : "Non valorisé"}</b><span class="small muted">${fresh(quote) ? "Cours reçu" : "Dernier cours connu"}</span></div></div>`).join("") || '<p class="muted">Votre première crypto vous attend.</p>'}`;
  } else {
    const id = S.cache.luxurySelected?.[tab] || Object.keys(sh[tab])[0], row = m[tab][id];
    root.querySelector("[data-market-status]").innerHTML = '<span class="live-dot"></span> Cote simulée Olivia <span class="muted">/ actualisation 1 min</span>';
    root.querySelector("[data-market-display]").innerHTML = `<div class="eyebrow">${esc(sh[tab][id].name)}</div><div class="row between"><h2 class="market-price">${money(row.price)}</h2>${movement(row.change_pct)}</div>${row.leverage ? `<div class="market-amplified">Variations amplifiées ×5 · cours fictif du jeu.<br>Bitcoin réel : <b>${quoteMoney(row.market_price)}</b>. Votre prix de jeu monte et baisse plus vite.</div>` : ""}${chart(row.history, range)}<p class="market-caption">Variation sur l’historique disponible (24 h maximum). Cote de jeu, indépendante des prix réels.</p>`;
    root.querySelectorAll("[data-luxury-item]").forEach(card => {
      const key = card.dataset.luxuryItem, price = sh[tab][key].price;
      const count = (club[tab] || []).filter(x => x === key).length;
      card.classList.toggle("selected", key === id);
      card.querySelector("[data-item-price]").innerHTML = `${money(price)} ${movement(m[tab][key].change_pct)}`;
      card.querySelector("[data-item-resale]").textContent = `Revente ${money(Math.floor(price * sh.resale_rate))} · possédé ×${count}`;
      card.querySelector("[data-buy]").disabled = club.cash < price;
      card.querySelector("[data-sell]").disabled = count === 0;
    });
  }
}

export async function shop(root, params) {
  let tab = params?.id || S.cache.shopTab || "cars";
  if (tab === "bitcoin") tab = "crypto";
  if (!["cars", "watches", "crypto"].includes(tab)) tab = "cars";
  S.cache.shopTab = tab;
  const data = await api("/api/markets");
  if (S.route.name !== "shop" || !root.isConnected) return;
  S.cache.markets = data;
  const sh = S.state.config.shop;
  // Endpoint and state may have crossed a quote update: use this snapshot in the shop.
  for (const cat of ["cars", "watches"]) for (const [key, row] of Object.entries(data[cat])) sh[cat][key].price = row.price;
  sh.crypto_quotes = data.crypto; sh.bitcoin_price = data.crypto.BTC.price || 0;
  root.innerHTML = `<section id="market-shop" data-tab="${tab}">
    <header class="page-head"><div><div class="kicker">OLIVIA / PATRIMOINE</div><h1>La valeur du désir.</h1><p>Collectionnez. Investissez. Regardez votre patrimoine évoluer.</p></div><div class="page-emblem">${icon("shop")}</div></header>
    <div class="market-overview"><div><span class="eyebrow">TRÉSORERIE</span><b data-market-cash></b></div><div><span class="eyebrow">CRYPTO & COLLECTIONS</span><b data-market-wealth></b></div><div class="market-status" data-market-status role="status"></div></div>
    <div class="tabs market-tabs"><button data-t="cars" class="${tab === "cars" ? "on" : ""}">${icon("car")} Voitures</button><button data-t="watches" class="${tab === "watches" ? "on" : ""}">${icon("watch")} Montres</button><button data-t="crypto" class="${tab === "crypto" ? "on" : ""}">₿ Cryptomonnaies</button></div>
    ${tab === "crypto" ? `<div class="crypto-ticker">${Object.entries(data.crypto).map(([symbol, coin]) => `<button class="coin-tile" data-coin="${symbol}" aria-label="Voir ${esc(coin.name)}"><span class="coin-symbol">${symbol}</span><span class="coin-name">${esc(coin.name)}${symbol === "BTC" ? " ×5" : ""}</span><b data-coin-price></b><span data-coin-change></span></button>`).join("")}</div>` : ""}
    <div class="market-layout"><div class="panel market-main"><div class="row between"><span class="eyebrow">${tab === "crypto" ? "LE MARCHÉ EN DIRECT" : "OBSERVATOIRE DES COLLECTIONS"}</span><div class="market-ranges"><button class="btn sm ghost" data-range="3600">1 h</button><button class="btn sm ghost" data-range="86400">24 h</button></div></div><div data-market-display></div>
    ${tab === "crypto" ? `<div class="market-order"><h3 data-trade-title></h3><label for="market-qty">Quantité à acheter ou revendre</label><input id="market-qty" type="number" inputmode="decimal" min="0.00000001" step="0.00000001" max="1000000" value="${esc(S.cache.marketQty || "0.01")}"><p class="small muted" data-trade-estimate></p><div class="row"><button class="btn gold" id="market-buy">Acheter</button><button class="btn ghost" id="market-sell">Revendre</button></div><p class="small muted">Frais de jeu : 0,5 % par opération. Montants arrondis à l’euro. Exécution au cours serveur, qui peut évoluer. Argent du jeu uniquement.</p></div>` : `<p class="small muted">Les cotes montent ou baissent pour tous les joueurs. Revente à ${Math.round(sh.resale_rate * 100)} % de la cote actuelle.</p>`}</div>
    ${tab === "crypto" ? `<aside class="panel" data-market-portfolio></aside>` : `<div class="luxury-market-list">${Object.entries(sh[tab]).map(([key, item]) => `<article class="panel luxury-market-item" data-luxury-item="${key}"><div class="row between"><span class="luxury-market-icon">${icon(tab === "cars" ? "car" : "watch")}</span><button class="btn sm ghost" data-chart="${key}">Courbe</button></div><h3>${esc(item.name)}</h3><div data-item-price></div><p class="small muted" data-item-resale></p><div class="row"><button class="btn sm gold" data-buy="${key}">Acheter</button><button class="btn sm ghost" data-sell="${key}">Revendre</button></div></article>`).join("")}</div>`}</div>
    <p class="market-footnote">${tab === "crypto" ? 'Bitcoin : cours de jeu amplifié ×5. Autres cryptos : cours réels. Source : <a href="https://www.kraken.com/prices" target="_blank" rel="noopener noreferrer">Kraken</a> · EUR. Les cours anciens restent visibles ; les échanges sont suspendus après 90 s sans données fraîches.' : 'Marché fictif Olivia : les variations des collections participent à votre richesse et au classement.'}</p></section>`;
  root.querySelectorAll("[data-t]").forEach(b => b.onclick = () => { location.hash = `#/shop/${b.dataset.t}`; });
  root.querySelectorAll("[data-coin]").forEach(b => b.onclick = () => { S.cache.marketSymbol = b.dataset.coin; updateMarketView(); });
  root.querySelectorAll("[data-range]").forEach(b => b.onclick = () => {
    S.cache.marketRange = Number(b.dataset.range); updateMarketView();
    root.querySelectorAll("[data-range]").forEach(btn => btn.classList.toggle("on", btn === b));
  });
  root.querySelectorAll("[data-chart]").forEach(b => b.onclick = () => {
    S.cache.luxurySelected = { ...S.cache.luxurySelected, [tab]: b.dataset.chart }; updateMarketView();
  });
  const input = root.querySelector("#market-qty");
  if (input) {
    input.oninput = () => { S.cache.marketQty = input.value; updateMarketView(); };
    for (const op of ["buy", "sell"]) root.querySelector(`#market-${op}`).onclick = async () => {
      const symbol = S.cache.marketSymbol || "BTC", amount = input.value;
      const row = S.cache.markets.crypto[symbol], factor = op === "buy" ? 1.005 : .995;
      const total = (op === "buy" ? Math.ceil : Math.floor)(Number(amount) * row.price * factor);
      if (!(await confirmBox({ title: `${op === "buy" ? "Acheter" : "Revendre"} ${units(amount)} ${symbol}`, html: `<p>Montant estimé, frais inclus : <b>${money(total)}</b>.</p><p class="muted small">Le cours serveur à l’exécution détermine le montant final.</p>`, okLabel: "Confirmer" }))) return;
      try {
        const result = await act(`/api/crypto/${op}`, { symbol, quantity: amount });
        toast({ title: op === "buy" ? "Achat confirmé" : "Vente confirmée", text: `${result.quantity} ${symbol} · ${money(result.cost ?? result.gain)}`, tone: "gold" });
        updateMarketView();
      } catch {}
    };
  }
  for (const op of ["buy", "sell"]) root.querySelectorAll(`[data-${op}]`).forEach(b => b.onclick = async () => {
    const id = b.dataset[op], item = S.state.config.shop[tab][id], price = item.price;
    const amount = op === "buy" ? price : Math.floor(price * S.state.config.shop.resale_rate);
    if (!(await confirmBox({ title: `${op === "buy" ? "Acheter" : "Revendre"} ${item.name}`, html: `<p>Montant : <b>${money(amount)}</b>.</p><p class="small muted">Si la cote évolue pendant la confirmation, une nouvelle validation sera nécessaire.</p>`, okLabel: "Confirmer" }))) return;
    try {
      const result = await act(`/api/shop/${op}`, { category: tab, item_id: id, expected_price: price });
      toast({ title: op === "buy" ? "Collection enrichie" : "Vente confirmée", text: `${item.name} · ${money(result.cost ?? result.gain)}`, tone: "gold" }); updateMarketView();
    } catch {}
  });
  updateMarketView();
}
