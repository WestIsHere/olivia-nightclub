/* ==========================================================
   AudioManager — moteur audio du jeu (Web Audio API).

   Bus : master → { fx, showcase, ambient, notifications }
     fx            : FX critiques (braquage) + événements
     showcase      : extraits de showcase — LOCAL à la vue du club consulté
     ambient       : ambiance de club — LOCAL à la vue du club consulté
     notifications : interface / notifications

   Règle fondamentale :
     BRAQUAGE  = GLOBAL  → joué dès que le serveur diffuse ROBBERY_CREATED
     SHOWCASE  = LOCAL   → joué uniquement si activeClubView === showcase.clubId

   Le serveur reste la source de vérité : ce module ne fait que réagir
   aux événements validés (SSE) et à la vue courante (setView).
   ========================================================== */

import { YouTubeStage } from "./youtube.js";
import { ClubScreen } from "./club-screen.js";

const BUSES = ["fx", "showcase", "ambient", "notifications"];
const DEFAULT_PREFS = { master: 0.8, fx: 0.9, showcase: 0.7, ambient: 0.2, notifications: 0.6, muted: false };
const STORAGE_KEY = "olivia.audio.prefs";

export class AudioManager {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.buses = {};
    this.prefs = { ...DEFAULT_PREFS };
    this.manifest = null;
    this.settings = { ducking: 0.35, clip_gap: [4, 9], fx_window: 10, fx_max: 3, fx_volumes: [1, 0.7, 0.5], fx_gap: 1.2, fade: 0.35 };
    this.buffers = new Map();       // url -> Promise<AudioBuffer>
    this.lastPick = new Map();      // key -> url (jamais deux fois de suite le même extrait)
    this.needsGesture = false;
    this.hidden = document.hidden;
    this.view = { clubId: null, showcase: null, level: 0 };
    this.showcase = { key: null, token: null, handle: null, timer: null, artist: null, clubId: null };
    this.ambient = { clubId: null, handle: null };
    this.fxQueue = [];
    this.fxBusy = false;
    this.fxTimes = [];
    this.onSave = null;             // (prefs) => void — persistance serveur (app.js)
    this.onStateChange = null;      // () => void — rafraîchir l'UI (bouton mute / activer le son)
    this._saveTimer = null;
    // Écran de scène YouTube (showcases) — même règle locale que les fichiers audio.
    this.stage = new YouTubeStage();
    this.screen = new ClubScreen(this.stage, {
      volume: () => this.effectiveShowcaseVolume(),
      onActive: (active) => this.duck(active),
    });
    this.screen.onSnapshot = (snapshot) => { this.view.showcase = snapshot; };
    this.stage.onBlocked = () => { this.needsGesture = true; this.notify(); };
    this.stage.onPlaying = () => { this.needsGesture = false; this.notify(); };
    this.loadLocalPrefs();
  }

  /** Volume effectif du bus showcase (pour le lecteur YouTube, hors graphe Web Audio). */
  effectiveShowcaseVolume() {
    if (this.prefs.muted) return 0;
    return Math.max(0, Math.min(1, Number(this.prefs.master) * Number(this.prefs.showcase)));
  }

  // ---------------- initialisation / autoplay ----------------
  init() {
    const unlock = () => this.unlock();
    for (const ev of ["pointerdown", "keydown", "touchstart"]) document.addEventListener(ev, unlock, { capture: true, passive: true });
    document.addEventListener("visibilitychange", () => { this.hidden = document.hidden; this.reconcile(); });
  }

  ensureContext() {
    if (this.ctx) return this.ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.connect(this.ctx.destination);
    for (const b of BUSES) {
      const g = this.ctx.createGain();
      g.connect(this.master);
      this.buses[b] = g;
    }
    this.ctx.onstatechange = () => { this.notify(); if (this.ready()) { this.needsGesture = false; this.reconcile(); } };
    this.applyPrefs();
    return this.ctx;
  }

  unlock() {
    const ctx = this.ensureContext();
    this.stage.tryResume();   // relance le lecteur YouTube si l'autoplay avait été bloqué
    if (!ctx) return;
    if (ctx.state !== "running") ctx.resume().then(() => { this.needsGesture = false; this.notify(); this.reconcile(); }).catch(() => {});
  }

  ready() { return !!this.ctx && this.ctx.state === "running"; }

  notify() { if (this.onStateChange) try { this.onStateChange(); } catch {} }

  /** Vrai si le navigateur bloque le son tant qu'aucune interaction n'a eu lieu. */
  get blocked() { return (this.needsGesture && !this.ready()) || this.stage.blocked; }

  // ---------------- préférences ----------------
  loadLocalPrefs() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) this.prefs = { ...DEFAULT_PREFS, ...JSON.parse(raw) };
    } catch {}
  }

  setPrefs(prefs, { persist = true } = {}) {
    this.prefs = { ...DEFAULT_PREFS, ...this.prefs, ...(prefs || {}) };
    this.applyPrefs();
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(this.prefs)); } catch {}
    if (persist && this.onSave) {
      clearTimeout(this._saveTimer);
      this._saveTimer = setTimeout(() => this.onSave(this.prefs), 600);
    }
    this.notify();
  }

  setPref(key, value) { this.setPrefs({ [key]: value }); }
  toggleMute() { this.setPrefs({ muted: !this.prefs.muted }); }

  applyPrefs() {
    this.stage.setVolume(this.effectiveShowcaseVolume());
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.master.gain.setTargetAtTime(this.prefs.muted ? 0 : this.prefs.master, t, 0.05);
    for (const b of BUSES) this.buses[b].gain.setTargetAtTime(Number(this.prefs[b] ?? 0.7), t, 0.05);
  }

  // ---------------- manifeste / assets ----------------
  setManifest(manifest) {
    this.manifest = manifest;
    if (manifest?.settings) this.settings = { ...this.settings, ...manifest.settings };
    if (manifest?.defaults && !localStorage.getItem(STORAGE_KEY)) this.setPrefs(manifest.defaults, { persist: false });
    this.preloadCore();
  }

  preloadCore() {
    if (!this.manifest) return;
    for (const a of this.manifest.assets.robbery || []) this.load(a.url).catch(() => {});
    for (const name of ["notify", "cash"]) for (const a of this.manifest.assets.ui?.[name] || []) this.load(a.url).catch(() => {});
  }

  load(url) {
    if (!this.buffers.has(url)) {
      const ctx = this.ensureContext();
      if (!ctx) return Promise.reject(new Error("no audio"));
      const p = fetch(url).then((r) => { if (!r.ok) throw new Error(url); return r.arrayBuffer(); })
        .then((ab) => ctx.decodeAudioData(ab));
      p.catch(() => this.buffers.delete(url));
      this.buffers.set(url, p);
    }
    return this.buffers.get(url);
  }

  /** Sélection aléatoire pondérée, sans répéter l'extrait précédent quand il y a le choix. */
  pick(list, key) {
    if (!list || !list.length) return null;
    let candidates = list;
    const last = this.lastPick.get(key);
    if (list.length > 1 && last) candidates = list.filter((a) => a.url !== last);
    const total = candidates.reduce((s, a) => s + (Number(a.weight) || 1), 0);
    let r = Math.random() * total;
    let chosen = candidates[candidates.length - 1];
    for (const a of candidates) { r -= (Number(a.weight) || 1); if (r <= 0) { chosen = a; break; } }
    this.lastPick.set(key, chosen.url);
    return chosen;
  }

  showcaseAssets(artist) {
    if (!this.manifest) return { list: [], key: null };
    const key = this.manifest.artist_keys?.[artist] || String(artist).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    const own = this.manifest.assets.showcases?.[key];
    if (own && own.length) return { list: own, key };
    if (this.manifest.showcase_fallback) {
      const fb = this.manifest.assets.showcases?.[this.manifest.fallback_key || "_placeholder"] || [];
      return { list: fb, key: `fallback:${key}` };
    }
    return { list: [], key };
  }

  // ---------------- lecture bas niveau ----------------
  playBuffer(buffer, bus, { volume = 1, loop = false, fadeIn = 0 } = {}) {
    const ctx = this.ctx;
    const t = ctx.currentTime;
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = loop;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(fadeIn > 0 ? 0.0001 : volume, t);
    if (fadeIn > 0) gain.gain.linearRampToValueAtTime(volume, t + fadeIn);
    src.connect(gain).connect(this.buses[bus]);
    const handle = { src, gain, volume, done: false, stopped: false };
    handle.ended = new Promise((resolve) => { src.onended = () => { handle.done = true; resolve(); }; });
    handle.stop = (fade = this.settings.fade) => {
      if (handle.stopped) return;
      handle.stopped = true;
      const now = ctx.currentTime;
      try {
        gain.gain.cancelScheduledValues(now);
        gain.gain.setValueAtTime(gain.gain.value, now);
        gain.gain.linearRampToValueAtTime(0.0001, now + fade);
        src.stop(now + fade + 0.02);
      } catch {}
    };
    handle.setVolume = (v, time = 0.4) => {
      try {
        const now = ctx.currentTime;
        gain.gain.cancelScheduledValues(now);           // annule un fade-in encore en cours
        gain.gain.setValueAtTime(Math.max(0.0001, gain.gain.value), now);
        gain.gain.setTargetAtTime(v, now, time / 3);
      } catch {}
    };
    src.start(t);
    return handle;
  }

  async playAsset(asset, bus, opts = {}) {
    if (!asset) return null;
    if (!this.ready()) { this.needsGesture = true; this.notify(); this.ensureContext(); if (!this.ready()) return null; }
    const buffer = await this.load(asset.url);
    if (!this.ready()) return null;
    return this.playBuffer(buffer, bus, opts);
  }

  // ---------------- sons simples ----------------
  playUi(name, volume = 1) {
    const list = this.manifest?.assets.ui?.[name];
    return this.playAsset(this.pick(list, `ui:${name}`), "notifications", { volume }).catch(() => null);
  }

  playEvent(name, volume = 1) {
    const list = this.manifest?.assets.events?.[name];
    return this.playAsset(this.pick(list, `ev:${name}`), "fx", { volume }).catch(() => null);
  }

  // ---------------- FX BRAQUAGE (global) — file anti-spam ----------------
  playRobbery() {
    const now = Date.now();
    const win = this.settings.fx_window * 1000;
    this.fxTimes = this.fxTimes.filter((t) => now - t < win);
    const recent = this.fxTimes.length;
    if (recent >= this.settings.fx_max) return false;          // trop de braquages : on garde l'événement, pas le son
    this.fxTimes.push(now);
    const volume = this.settings.fx_volumes[Math.min(recent, this.settings.fx_volumes.length - 1)] ?? 0.5;
    this.fxQueue.push({ volume });
    this.drainFx();
    return true;
  }

  async drainFx() {
    if (this.fxBusy) return;
    const item = this.fxQueue.shift();
    if (!item) return;
    this.fxBusy = true;
    try {
      const asset = this.pick(this.manifest?.assets.robbery, "robbery");
      const handle = await this.playAsset(asset, "fx", { volume: item.volume });
      const wait = Math.max(this.settings.fx_gap, Math.min(asset?.duration || 3, 4)) * 1000;
      await new Promise((r) => setTimeout(r, handle ? wait : 200));
    } catch {}
    this.fxBusy = false;
    if (this.fxQueue.length) this.drainFx();
  }

  // ---------------- contexte de vue : ACTIVE_CLUB_VIEW ----------------
  /**
   * setView({ clubId, showcase: { artist, ends_at } | null, level })
   * Appelé par les pages "Ma boîte" et "Visite". setView(null) partout ailleurs.
   * Idempotent : même club + même artiste → rien ne redémarre.
   */
  setView(view) {
    this.view = view ? { clubId: view.clubId ?? null, showcase: view.showcase || null, level: view.level || 0 } : { clubId: null, showcase: null, level: 0 };
    this.reconcile();
  }

  get activeClubView() { return this.view.clubId; }

  onShowcaseStarted(p) {
    if (p.club_id !== this.view.clubId) return;
    this.view.showcase = p;
    this.reconcile();
  }

  onShowcaseEnded(p) {
    if (p.club_id !== this.view.clubId) return;
    if (this.view.showcase?.showcase_id && this.view.showcase.showcase_id !== p.showcase_id) return;
    this.screen.end(p);
    this.view.showcase = null;
    this.reconcile();
  }

  /** Réconcilie l'état audio avec la vue courante (source : setView + événements serveur). */
  reconcile() {
    this.screen.setClub(!this.hidden ? this.view.clubId : null, this.view.showcase);
    const active = !this.hidden && this.ready() && this.view.clubId != null;
    const wantAmbient = active ? this.view.clubId : null;
    if (this.ambient.clubId !== wantAmbient) {
      this.stopAmbient();
      if (wantAmbient != null) this.startAmbient(wantAmbient);
    }
    // On voudrait jouer (vue club) mais le navigateur attend une interaction → proposer « Activer le son ».
    if (!this.ready() && !this.hidden && this.view.clubId != null) {
      this.ensureContext();
      if (!this.ready()) this.needsGesture = true;
    }
    this.notify();
  }

  // ---------------- ambiance ----------------
  async startAmbient(clubId) {
    this.ambient = { clubId, handle: null, token: Symbol("amb") };
    const token = this.ambient.token;
    const list = this.manifest?.assets.ambient || [];
    const byLevel = list.filter((a) => a.url.includes(`lvl${this.view.level}`));
    const asset = this.pick(byLevel.length ? byLevel : list, "ambient");
    if (!asset) return;
    try {
      const handle = await this.playAsset(asset, "ambient", { volume: this.stage.active ? this.settings.ducking : 1, loop: true, fadeIn: 1.2 });
      if (this.ambient.token !== token) { handle?.stop(0.2); return; }
      this.ambient.handle = handle;
    } catch {}
  }

  stopAmbient() {
    if (this.ambient.handle) this.ambient.handle.stop(0.6);
    this.ambient = { clubId: null, handle: null, token: null };
  }

  duck(on) {
    if (this.ambient.handle) this.ambient.handle.setVolume(on ? this.settings.ducking : 1, on ? 0.6 : 2.0);
  }

  // ---------------- tests (page Paramètres) ----------------
  test(kind) {
    this.unlock();
    if (kind === "robbery") return this.playRobbery();
    if (kind === "notify") return this.playUi("notify");
    if (kind === "showcase") {
      const { list, key } = this.showcaseAssets("Lagui");
      return this.playAsset(this.pick(list, `show:${key}`), "showcase", { fadeIn: 0.3 }).then((h) => { setTimeout(() => h?.stop(0.5), 6000); });
    }
    if (kind === "ambient") return this.playAsset(this.pick(this.manifest?.assets.ambient, "ambient"), "ambient", { fadeIn: 0.5 }).then((h) => { setTimeout(() => h?.stop(0.8), 6000); });
    return null;
  }

  status() {
    return {
      ready: this.ready(), blocked: this.blocked, muted: this.prefs.muted, view: this.view.clubId,
      showcase: this.screen.snapshot?.artist || null, ambient: this.ambient.clubId != null, queue: this.fxQueue.length,
    };
  }
}

export const audio = new AudioManager();
