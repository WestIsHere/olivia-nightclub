/* ==========================================================
   Scène du club — SVG procédural.
   Évolue avec : niveau, équipements, fréquentation, showcase,
   événement en cours, voitures possédées.
   ========================================================== */

export const LEVEL_THEMES = [
  { neon: "#e9e2d2", glow: "#b8b0a0", facade: "#1a1820", facade2: "#0f0e14", accent: "#6b6578", symbol: "", w: 340, h: 170, rows: 1 },
  { neon: "#f5f5ff", glow: "#c9c9ff", facade: "#0c0b10", facade2: "#050408", accent: "#ffffff", symbol: "♠", w: 420, h: 200, rows: 1 },
  { neon: "#c084fc", glow: "#8b5cf6", facade: "#17122a", facade2: "#0c0918", accent: "#a78bfa", symbol: "◆", w: 500, h: 230, rows: 2 },
  { neon: "#fb7185", glow: "#e11d48", facade: "#1f0f16", facade2: "#12080c", accent: "#f43f5e", symbol: "✦", w: 580, h: 260, rows: 2 },
  { neon: "#67e8f9", glow: "#22d3ee", facade: "#0e1a22", facade2: "#071016", accent: "#22d3ee", symbol: "≋", w: 660, h: 290, rows: 3 },
  { neon: "#fda4af", glow: "#f472b6", facade: "#231326", facade2: "#140a16", accent: "#fb923c", symbol: "🌴", w: 740, h: 320, rows: 3 },
  { neon: "#f7e08a", glow: "#d4af37", facade: "#1b160c", facade2: "#0f0c06", accent: "#f3d77a", symbol: "♛", w: 820, h: 360, rows: 4 },
];

let uid = 0;
function nextId() { uid += 1; return "sc" + uid; }

function seeded(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

function esc(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function person(x, y, rnd, opts = {}) {
  const s = opts.scale ?? 1;
  const palette = ["#08070d", "#0d0b13", "#120e1a", "#0a0a0f"];
  const dress = ["#c0392b", "#d4af37", "#8b5cf6", "#f472b6", "#22d3ee", "#e5e5e5"];
  const body = opts.color || palette[Math.floor(rnd() * palette.length)];
  const hasDress = !opts.color && rnd() < 0.25;
  const dressColor = dress[Math.floor(rnd() * dress.length)];
  const h = 34 * s;
  const w = 12 * s;
  const lean = (rnd() - 0.5) * 3;
  const bob = opts.animate && rnd() < 0.4 ? ' class="sc-bob"' : "";
  return `<g transform="translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${lean.toFixed(1)})"${bob}>
    <circle cx="0" cy="${-h + 4 * s}" r="${4.4 * s}" fill="${body}"/>
    <path d="M${-w / 2},${-h + 10 * s} q${w / 2},-4 ${w},0 l${2 * s},${h * 0.55} h${-w - 4 * s} z" fill="${hasDress ? dressColor : body}" opacity="${hasDress ? 0.85 : 1}"/>
    <rect x="${-w / 2}" y="${-h * 0.42}" width="${w * 0.42}" height="${h * 0.42}" fill="${body}"/>
    <rect x="${w * 0.08}" y="${-h * 0.42}" width="${w * 0.42}" height="${h * 0.42}" fill="${body}"/>
    ${opts.armband ? `<rect x="${w / 2 - 3 * s}" y="${-h + 14 * s}" width="${3 * s}" height="${6 * s}" fill="#f3d77a"/>` : ""}
    ${opts.earpiece ? `<circle cx="${3.5 * s}" cy="${-h + 5 * s}" r="${1.2 * s}" fill="#fff"/>` : ""}
    ${opts.phone ? `<rect x="${-1.5 * s}" y="${-h + 8 * s}" width="${3 * s}" height="${5 * s}" fill="#fff" class="sc-twinkle"/>` : ""}
  </g>`;
}

function car(x, y, color, opts = {}) {
  const s = opts.scale ?? 1;
  const label = opts.label ? `<text x="0" y="${-4 * s}" text-anchor="middle" font-size="${9 * s}" fill="#f3d77a" font-family="Barlow Condensed, sans-serif" letter-spacing="1">${esc(opts.label)}</text>` : "";
  return `<g transform="translate(${x},${y}) scale(${s})">
    <ellipse cx="0" cy="18" rx="62" ry="6" fill="#000" opacity=".55"/>
    <path d="M-60,12 q0,-10 8,-12 l14,-14 q6,-6 14,-6 h34 q10,0 16,6 l16,14 q10,2 10,12 v6 h-112 z" fill="${color}"/>
    <path d="M-36,-2 l12,-12 q4,-4 10,-4 h26 q6,0 10,4 l10,12 z" fill="#0a0a12" opacity=".9"/>
    <rect x="-64" y="8" width="8" height="4" rx="1" fill="#fff6d5" opacity=".95"/>
    <rect x="56" y="8" width="8" height="4" rx="1" fill="#ff2d55"/>
    <circle cx="-34" cy="18" r="9" fill="#111"/><circle cx="-34" cy="18" r="4" fill="#666"/>
    <circle cx="36" cy="18" r="9" fill="#111"/><circle cx="36" cy="18" r="4" fill="#666"/>
    <path d="M-56,8 h112" stroke="rgba(255,255,255,.15)" stroke-width="1"/>
    ${label}
  </g>`;
}

function stanchion(x, y) {
  return `<g transform="translate(${x},${y})"><rect x="-1.5" y="-26" width="3" height="26" fill="#d4af37"/><circle cx="0" cy="-27" r="3" fill="#f3d77a"/><ellipse cx="0" cy="0" rx="6" ry="2" fill="#a8862a"/></g>`;
}

function fitFont(text, maxWidth, maxSize, ratio = 0.72) {
  const len = Math.max(1, String(text).length);
  return Math.max(14, Math.min(maxSize, maxWidth / (len * ratio)));
}

/**
 * Rendu de la scène.
 * club : vue publique ou état privé (name, level, equipment[], occupancy, showcase_pending,
 *        showcase_artist, last_event{title,time}, cars[], status)
 * opts : { mini, config, serverTime, carName }
 */
export function renderScene(club, opts = {}) {
  const level = Math.max(0, Math.min(6, Number(club.level || 0)));
  const theme = LEVEL_THEMES[level];
  const levelName = opts.levelName || (opts.config ? opts.config.levels[level].name : "");
  const mini = !!opts.mini;
  const id = nextId();
  const rnd = seeded((club.user_id || 1) * 7919 + level * 31 + (club.equipment?.length || 0));
  const equipment = new Set(club.equipment || []);
  const occ = Math.max(0, Math.min(1.5, Number(club.occupancy ?? 0.5)));
  const showcase = !!club.showcase_pending;
  const now = opts.serverTime || Date.now() / 1000;
  const lastEvent = club.last_event && (now - Number(club.last_event.time || 0) < 600) ? club.last_event : null;
  const eventKind = lastEvent ? detectEvent(lastEvent.title) : null;
  const power = eventKind === "power";

  const W = theme.w, H = theme.h;
  const cx = 500, ground = 400;
  const left = cx - W / 2, top = ground - H;
  const neon = power ? "#5b5566" : theme.neon;
  const glow = power ? "#222" : theme.glow;

  const parts = [];

  // ---------- defs ----------
  parts.push(`<defs>
    <linearGradient id="${id}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05040a"/><stop offset=".6" stop-color="#0d0a18"/><stop offset="1" stop-color="#1a1226"/></linearGradient>
    <linearGradient id="${id}-street" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#15121d"/><stop offset="1" stop-color="#07060a"/></linearGradient>
    <linearGradient id="${id}-facade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${theme.facade}"/><stop offset="1" stop-color="${theme.facade2}"/></linearGradient>
    <radialGradient id="${id}-door" cx=".5" cy="1" r=".9"><stop offset="0" stop-color="#ffd37a" stop-opacity=".95"/><stop offset="1" stop-color="#ffb347" stop-opacity="0"/></radialGradient>
    <radialGradient id="${id}-reflect" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="${glow}" stop-opacity=".45"/><stop offset="1" stop-color="${glow}" stop-opacity="0"/></radialGradient>
    <filter id="${id}-glow" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="${mini ? 3 : 6}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="${id}-soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="10"/></filter>
    <clipPath id="${id}-clip"><rect x="0" y="0" width="1000" height="540"/></clipPath>
  </defs>`);

  // ---------- ciel ----------
  parts.push(`<rect width="1000" height="540" fill="url(#${id}-sky)"/>`);
  const stars = mini ? 12 : 40;
  for (let i = 0; i < stars; i++) {
    const x = rnd() * 1000, y = rnd() * 220, r = rnd() * 1.2 + 0.3;
    parts.push(`<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(1)}" fill="#fff" opacity=".7" class="sc-twinkle" style="animation-delay:${(rnd() * 3).toFixed(1)}s"/>`);
  }
  // skyline lointain
  let sx = 0;
  const skyline = [];
  while (sx < 1000) {
    const bw = 40 + rnd() * 80, bh = 90 + rnd() * 190;
    skyline.push(`<rect x="${sx}" y="${(ground - bh).toFixed(0)}" width="${bw.toFixed(0)}" height="${bh.toFixed(0)}" fill="#0b0912"/>`);
    const cols = Math.floor(bw / 14), rows = Math.floor(bh / 18);
    for (let c = 0; c < cols; c++) for (let r = 0; r < rows; r++) {
      if (rnd() < 0.35) {
        const colors = ["#f3d77a", "#c084fc", "#67e8f9", "#fb7185", "#ffffff"];
        skyline.push(`<rect x="${(sx + 4 + c * 14).toFixed(0)}" y="${(ground - bh + 6 + r * 18).toFixed(0)}" width="6" height="8" fill="${colors[Math.floor(rnd() * colors.length)]}" opacity="${(0.25 + rnd() * 0.5).toFixed(2)}"/>`);
      }
    }
    sx += bw + 6 + rnd() * 20;
  }
  parts.push(`<g opacity=".8">${skyline.join("")}</g>`);
  // halo urbain
  parts.push(`<ellipse cx="500" cy="${ground}" rx="700" ry="180" fill="${glow}" opacity=".08" filter="url(#${id}-soft)"/>`);

  // ---------- rue ----------
  parts.push(`<rect x="0" y="${ground}" width="1000" height="140" fill="url(#${id}-street)"/>`);
  parts.push(`<rect x="0" y="${ground}" width="1000" height="3" fill="#2a2536"/>`);
  parts.push(`<ellipse cx="500" cy="${ground + 60}" rx="${W * 0.7}" ry="45" fill="url(#${id}-reflect)"/>`);
  parts.push(`<g opacity=".35">${Array.from({ length: 9 }, (_, i) => `<rect x="${60 + i * 110}" y="${ground + 92}" width="60" height="4" rx="2" fill="#d4af37" opacity=".5"/>`).join("")}</g>`);
  // reflet enseigne (flou)
  parts.push(`<g opacity=".25" transform="translate(0,${ground * 2 + 40}) scale(1,-1)" filter="url(#${id}-soft)"><rect x="${left}" y="${ground - 60}" width="${W}" height="60" fill="${glow}"/></g>`);

  // ---------- bâtiment ----------
  const decor = equipment.has("decor");
  parts.push(`<rect x="${left - 14}" y="${top + 24}" width="${W + 28}" height="${H - 24}" fill="#08070c"/>`);
  parts.push(`<rect x="${left}" y="${top}" width="${W}" height="${H}" fill="url(#${id}-facade)" stroke="${decor ? "#d4af37" : "#26212f"}" stroke-width="${decor ? 3 : 1.5}"/>`);
  parts.push(`<rect x="${left - 10}" y="${top - 8}" width="${W + 20}" height="10" fill="${decor ? "#a8862a" : "#2a2536"}"/>`);
  if (decor) {
    parts.push(`<rect x="${left + 8}" y="${top + 8}" width="${W - 16}" height="${H - 16}" fill="none" stroke="#d4af37" stroke-width="1" opacity=".5"/>`);
    for (let i = 0; i <= 4; i++) parts.push(`<rect x="${left + (W / 4) * i - 3}" y="${top}" width="6" height="${H}" fill="#d4af37" opacity=".25"/>`);
  }
  // niveau 6 : rooftop
  if (level >= 5) {
    const rt = top - 34;
    parts.push(`<rect x="${left + 40}" y="${rt}" width="${W - 80}" height="34" fill="${theme.facade2}" stroke="#2a2536"/>`);
    parts.push(`<rect x="${left + 30}" y="${rt - 6}" width="${W - 60}" height="6" fill="${decor ? "#d4af37" : "#3a3346"}"/>`);
    for (let i = 0; i < 9; i++) {
      const px = left + 60 + ((W - 120) / 8) * i;
      parts.push(`<circle cx="${px}" cy="${rt - 10}" r="3" fill="${theme.accent}" class="sc-twinkle" style="animation-delay:${(i * 0.3).toFixed(1)}s" filter="url(#${id}-glow)"/>`);
    }
    if (!mini) for (let i = 0; i < 6; i++) parts.push(person(left + 80 + rnd() * (W - 160), rt - 2, rnd, { scale: 0.75, animate: true }));
  }
  if (level >= 5) {
    // palmiers
    for (const px of [left - 40, left + W + 40]) {
      parts.push(`<g transform="translate(${px},${ground})"><path d="M0,0 q4,-90 -6,-150" stroke="#2b2418" stroke-width="7" fill="none"/>
        ${[-70, -30, 10, 50, 90, 130].map(a => `<path d="M-6,-150 q${Math.cos(a * Math.PI / 180) * 40},${Math.sin(a * Math.PI / 180) * 30 - 20} ${Math.cos(a * Math.PI / 180) * 70},${Math.sin(a * Math.PI / 180) * 40}" stroke="#1f6b3a" stroke-width="6" stroke-linecap="round" fill="none"/>`).join("")}</g>`);
    }
  }

  // fenêtres
  const winRows = theme.rows, winCols = Math.floor((W - 60) / 46);
  const litRatio = 0.35 + occ * 0.5;
  const winColors = [theme.accent, "#f3d77a", "#c084fc", "#fb7185"];
  const dancerWindows = equipment.has("dancers") ? new Set([1, winCols - 2]) : new Set();
  const djWindow = equipment.has("dj") ? Math.floor(winCols / 2) : -1;
  const barWindow = equipment.has("bar_staff") ? Math.max(0, Math.floor(winCols / 2) - 2) : -1;
  for (let r = 0; r < winRows; r++) {
    for (let c = 0; c < winCols; c++) {
      const wx = left + 30 + c * 46, wy = top + 22 + r * 44;
      if (r === winRows - 1 && Math.abs(c - (winCols - 1) / 2) < 1.6) continue; // porte
      const lit = rnd() < litRatio;
      const col = winColors[Math.floor(rnd() * winColors.length)];
      parts.push(`<rect x="${wx}" y="${wy}" width="28" height="30" rx="2" fill="${lit ? col : "#0c0b12"}" opacity="${lit ? 0.35 + rnd() * 0.4 : 1}" stroke="#2a2536"/>`);
      if (r === winRows - 1 && dancerWindows.has(c)) {
        parts.push(`<rect x="${wx}" y="${wy}" width="28" height="30" rx="2" fill="#f472b6" opacity=".45"/>`);
        parts.push(person(wx + 14, wy + 30, rnd, { scale: 0.7, color: "#1a0a14", animate: true }));
      }
      if (r === winRows - 1 && c === djWindow) {
        parts.push(`<rect x="${wx}" y="${wy}" width="28" height="30" rx="2" fill="#8b5cf6" opacity=".5"/>`);
        parts.push(`<rect x="${wx + 4}" y="${wy + 18}" width="20" height="8" fill="#0a0910"/><circle cx="${wx + 14}" cy="${wy + 12}" r="4" fill="#0a0910"/>`);
        parts.push(`<text x="${wx + 14}" y="${wy - 4}" text-anchor="middle" font-size="9" fill="#c084fc" font-family="Barlow Condensed" font-weight="700" filter="url(#${id}-glow)">DJ</text>`);
      }
      if (r === winRows - 1 && c === barWindow) {
        parts.push(`<rect x="${wx}" y="${wy}" width="28" height="30" rx="2" fill="#d4af37" opacity=".35"/>`);
        for (let b = 0; b < 5; b++) parts.push(`<rect x="${wx + 3 + b * 5}" y="${wy + 6}" width="3" height="9" fill="${["#22d3ee", "#f3d77a", "#fb7185", "#c084fc", "#34d399"][b]}"/>`);
        parts.push(`<rect x="${wx + 2}" y="${wy + 18}" width="24" height="3" fill="#a8862a"/>`);
      }
    }
  }

  // porte principale
  const doorW = level >= 4 ? 70 : 54, doorH = 64;
  const dx = cx - doorW / 2, dy = ground - doorH;
  parts.push(`<rect x="${dx - 8}" y="${dy - 10}" width="${doorW + 16}" height="${doorH + 10}" fill="${decor ? "#a8862a" : "#2a2536"}"/>`);
  parts.push(`<rect x="${dx}" y="${dy}" width="${doorW}" height="${doorH}" fill="#2b1a08"/>`);
  parts.push(`<rect x="${dx}" y="${dy}" width="${doorW}" height="${doorH}" fill="url(#${id}-door)"/>`);
  parts.push(`<rect x="${dx + doorW / 2 - 1}" y="${dy}" width="2" height="${doorH}" fill="#0a0910" opacity=".6"/>`);
  parts.push(`<ellipse cx="${cx}" cy="${ground + 4}" rx="${doorW}" ry="14" fill="#ffb347" opacity=".22" filter="url(#${id}-soft)"/>`);
  // auvent
  parts.push(`<path d="M${dx - 30},${dy - 10} h${doorW + 60} l-12,22 h${-doorW - 36} z" fill="${theme.facade2}" stroke="${decor ? "#d4af37" : "#3a3346"}"/>`);
  for (let i = 0; i < 6; i++) parts.push(`<circle cx="${dx - 20 + i * ((doorW + 40) / 5)}" cy="${dy + 10}" r="2.2" fill="${neon}" class="sc-twinkle" style="animation-delay:${(i * 0.2).toFixed(1)}s"/>`);

  // tapis rouge
  parts.push(`<path d="M${cx - doorW / 2},${ground} l-30,90 h${doorW + 60} l-30,-90 z" fill="#8f1130" opacity=".85"/>`);

  // ---------- enseigne ----------
  const signText = String(club.name || "CLUB").toUpperCase();
  const fs = fitFont(signText, W - 60, level >= 4 ? 54 : 44);
  const signBaseline = top - 26;
  // panneau d'enseigne au-dessus du bâtiment
  parts.push(`<rect x="${left + 10}" y="${top - fs - 30}" width="${W - 20}" height="${fs + 26}" rx="6" fill="#06050a" stroke="${decor ? "#d4af37" : "#26212f"}"/>`);
  if (theme.symbol) {
    parts.push(`<text x="${cx}" y="${top - fs - 40}" text-anchor="middle" font-size="${level >= 5 ? 30 : 22}" fill="${neon}" filter="url(#${id}-glow)" class="sc-neon">${theme.symbol}</text>`);
  }
  parts.push(`<text x="${cx}" y="${signBaseline}" text-anchor="middle" font-family="Cinzel, 'Times New Roman', serif" font-weight="800" font-size="${fs.toFixed(0)}" letter-spacing="${(fs * 0.12).toFixed(0)}" fill="${neon}" filter="url(#${id}-glow)" class="sc-neon" style="animation-delay:${(rnd() * 4).toFixed(1)}s">${esc(signText)}</text>`);
  parts.push(`<text x="${cx}" y="${top - 8}" text-anchor="middle" font-family="Barlow Condensed, sans-serif" font-weight="600" font-size="13" letter-spacing="5" fill="${theme.accent}" opacity=".9">${esc(String(levelName).toUpperCase())}</text>`);
  if (level >= 6) {
    parts.push(`<text x="${cx}" y="${top - fs - 64}" text-anchor="middle" font-size="40" fill="#f3d77a" filter="url(#${id}-glow)">♛</text>`);
  }

  // ---------- showcase ----------
  if (showcase) {
    const mw = Math.min(W - 40, 420);
    parts.push(`<g transform="translate(${cx - mw / 2},${dy - 62})">
      <rect x="0" y="0" width="${mw}" height="40" rx="4" fill="#0a0910" stroke="#f3d77a" stroke-width="2" filter="url(#${id}-glow)"/>
      <text x="${mw / 2}" y="16" text-anchor="middle" font-family="Barlow Condensed" font-weight="700" font-size="11" letter-spacing="4" fill="#f3d77a" class="sc-blink">SHOWCASE CE SOIR</text>
      <text x="${mw / 2}" y="34" text-anchor="middle" font-family="Cinzel, serif" font-weight="800" font-size="17" letter-spacing="2" fill="#fff">${esc(String(club.showcase_artist || "ARTISTE").toUpperCase())}</text>
    </g>`);
    for (const [px, cls] of [[left + 30, ""], [left + W - 30, " b"]]) {
      parts.push(`<path d="M${px},${ground} l-70,-${H + 160} l140,0 z" fill="#fff" opacity=".12" class="sc-spot${cls}"/>`);
    }
  }

  // ---------- équipements ----------
  if (equipment.has("lights")) {
    const beams = [["#c084fc", left + W * 0.25, ""], ["#22d3ee", cx, " b"], ["#f472b6", left + W * 0.75, ""]];
    for (const [col, bx, cls] of beams) {
      parts.push(`<path d="M${bx},${top - 6} l-14,-220 l28,0 z" fill="${col}" opacity=".45" class="sc-laser${cls}" filter="url(#${id}-glow)"/>`);
    }
  }
  if (equipment.has("smoke")) {
    for (let i = 0; i < 4; i++) {
      parts.push(`<ellipse cx="${cx - 40 + i * 30}" cy="${ground - 8 - i * 4}" rx="${40 + i * 10}" ry="${14 + i * 3}" fill="#cbd5e1" opacity=".3" class="sc-smoke" style="animation-delay:${(i * 1.2).toFixed(1)}s" filter="url(#${id}-soft)"/>`);
    }
  }
  if (equipment.has("sound")) {
    for (const sx2 of [dx - 46, dx + doorW + 18]) {
      parts.push(`<g transform="translate(${sx2},${ground - 74})"><rect x="0" y="0" width="28" height="74" rx="3" fill="#0a0910" stroke="#3a3346"/><circle cx="14" cy="18" r="9" fill="#1c1826" stroke="#5b5566"/><circle cx="14" cy="18" r="3" fill="#8b5cf6" class="sc-blink"/><circle cx="14" cy="50" r="11" fill="#1c1826" stroke="#5b5566"/><circle cx="14" cy="50" r="4" fill="#22d3ee" class="sc-blink" style="animation-delay:.5s"/></g>`);
    }
  }
  if (equipment.has("vip_room")) {
    const vx = left + W - 110;
    parts.push(`<g transform="translate(${vx},${ground - 58})">
      <rect x="-8" y="-10" width="76" height="68" fill="#a8862a"/><rect x="0" y="0" width="60" height="58" fill="#1a1408"/>
      <rect x="0" y="0" width="60" height="58" fill="url(#${id}-door)" opacity=".8"/>
      <text x="30" y="-16" text-anchor="middle" font-family="Cinzel, serif" font-weight="800" font-size="16" letter-spacing="3" fill="#f3d77a" filter="url(#${id}-glow)" class="sc-neon">VIP</text>
      <path d="M0,58 l-16,50 h92 l-16,-50 z" fill="#d4af37" opacity=".35"/>
    </g>`);
    parts.push(stanchion(vx - 20, ground + 40) + stanchion(vx + 80, ground + 40));
    parts.push(`<path d="M${vx - 20},${ground + 16} q50,14 100,0" stroke="#d4af37" stroke-width="2" fill="none"/>`);
  }

  // ---------- cordons / videurs ----------
  const ropeY = ground + 42;
  parts.push(stanchion(cx - doorW - 30, ropeY) + stanchion(cx + doorW + 30, ropeY));
  parts.push(`<path d="M${cx - doorW - 30},${ropeY - 22} q${doorW + 30},16 ${2 * (doorW + 30)},0" stroke="#e11d48" stroke-width="3" fill="none"/>`);
  const bouncers = level >= 5 ? 3 : level >= 3 ? 2 : level >= 1 ? 1 : 0;
  const security = equipment.has("security");
  for (let i = 0; i < bouncers + (security ? 2 : 0); i++) {
    const bx = i % 2 === 0 ? cx - doorW / 2 - 22 - Math.floor(i / 2) * 22 : cx + doorW / 2 + 22 + Math.floor(i / 2) * 22;
    parts.push(person(bx, ground + 22, rnd, { scale: 1.15, color: "#050409", armband: security, earpiece: true }));
  }

  // ---------- foule ----------
  const crowd = Math.min(mini ? 14 : 40, Math.round(3 + occ * (mini ? 12 : 26) + (showcase ? 10 : 0)));
  const influencer = eventKind === "influencer";
  for (let i = 0; i < crowd; i++) {
    const side = rnd() < 0.5 ? -1 : 1;
    const dist = 60 + rnd() * (W * 0.55);
    const px = cx + side * dist;
    const py = ground + 30 + rnd() * 70;
    parts.push(person(px, py, rnd, { scale: 0.9 + (py - ground) / 150, animate: !mini, phone: influencer && rnd() < 0.5 }));
  }

  // ---------- voitures ----------
  const carColors = ["#0b0b12", "#111827", "#1f1b2e", "#2a0a12"];
  const nCars = level >= 6 ? 3 : level >= 4 ? 2 : level >= 2 ? 1 : 0;
  const carSpots = [[left - 110, ground + 98], [left + W + 110, ground + 98], [cx - 260, ground + 118]];
  for (let i = 0; i < nCars; i++) {
    const [x, y] = carSpots[i];
    parts.push(car(x, y, carColors[i % carColors.length], { scale: 0.85 + i * 0.05, label: i === 0 ? opts.carName : null }));
  }
  if (eventKind === "vip_party") parts.push(car(cx + 240, ground + 120, "#1a1408", { scale: 0.95, label: "TABLE VIP" }));

  // ---------- événements ----------
  if (eventKind === "police") {
    parts.push(`<g transform="translate(${left - 200},${ground + 110})">${car(0, 0, "#0f172a", { scale: 0.8 })}<rect x="-24" y="-30" width="18" height="6" fill="#3b82f6" class="sc-blink"/><rect x="6" y="-30" width="18" height="6" fill="#ef4444" class="sc-blink" style="animation-delay:.5s"/></g>`);
  }
  if (eventKind === "road") {
    for (let i = 0; i < 5; i++) parts.push(`<g transform="translate(${80 + i * 70},${ground + 80})"><rect x="-22" y="-14" width="44" height="10" fill="#f97316"/><rect x="-22" y="-14" width="11" height="10" fill="#fff"/><rect x="0" y="-14" width="11" height="10" fill="#fff"/><rect x="-18" y="-4" width="4" height="14" fill="#333"/><rect x="14" y="-4" width="4" height="14" fill="#333"/></g>`);
  }
  if (eventKind === "fight") {
    parts.push(`<text x="${cx + doorW + 60}" y="${ground - 20}" font-size="28" class="sc-blink">💥</text>`);
  }

  // ---------- pluie ----------
  const drops = mini ? 20 : 70;
  const rain = [];
  for (let i = 0; i < drops; i++) {
    const x = rnd() * 1000, y = rnd() * 540, l = 10 + rnd() * 14;
    rain.push(`<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x - 3).toFixed(0)}" y2="${(y + l).toFixed(0)}"/>`);
  }
  parts.push(`<g stroke="#cdd5ff" stroke-opacity=".28" stroke-width="1" class="sc-rain">${rain.join("")}</g>`);

  return `<svg viewBox="0 0 1000 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${esc(club.name)}" preserveAspectRatio="xMidYMid slice"><g clip-path="url(#${id}-clip)">${parts.join("\n")}</g></svg>`;
}

function detectEvent(title = "") {
  const t = title.toLowerCase();
  if (t.includes("police")) return "police";
  if (t.includes("bagarre")) return "fight";
  if (t.includes("route")) return "road";
  if (t.includes("coupure")) return "power";
  if (t.includes("influenceur")) return "influencer";
  if (t.includes("vip")) return "vip_party";
  return null;
}

/** Façade compacte pour la carte de la ville (même moteur, moins de détails). */
export function renderMini(club, opts = {}) {
  return renderScene(club, { ...opts, mini: true });
}

/** Visuel de connexion : boulevard animé. */
export function renderLoginVisual() {
  const fake = [
    { user_id: 11, name: "L'Olivia", level: 6, equipment: ["lights", "vip_room", "sound", "decor", "smoke"], occupancy: 1.2, showcase_pending: true, showcase_artist: "Lagui" },
  ];
  return renderScene(fake[0], { mini: false, levelName: "Le Olivia", carName: "Lamborghini SVJ" });
}
