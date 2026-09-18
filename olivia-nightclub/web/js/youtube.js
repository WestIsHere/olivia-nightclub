/* ==========================================================
   YouTubeStage — « écran de scène » : lecteur YouTube officiel
   (IFrame Player API) utilisé pour les showcases.

   Conforme aux règles YouTube : pas de téléchargement, lecteur
   visible (≥ 200 px), vidéo streamée depuis youtube.com.
   Piloté par l'AudioManager : même règle LOCALE que les fichiers
   (uniquement dans la vue du club concerné), extrait aléatoire,
   fondu, arrêt immédiat en quittant la vue.
   ========================================================== */

let apiPromise = null;

function loadApi() {
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve, reject) => {
    if (window.YT && window.YT.Player) return resolve(window.YT);
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { if (prev) try { prev(); } catch {} resolve(window.YT); };
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    s.onerror = () => reject(new Error("YouTube API indisponible"));
    document.head.appendChild(s);
    setTimeout(() => reject(new Error("YouTube API : délai dépassé")), 15000);
  });
  apiPromise.catch(() => { apiPromise = null; });
  return apiPromise;
}

function esc(s) { return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

export class YouTubeStage {
  constructor() {
    this.el = null;
    this.player = null;
    this.readyPromise = null;
    this.current = null;      // { token, onEnded, seconds, started }
    this.volume = 0.7;        // 0..1
    this.fadeTimer = null;
    this.clipTimer = null;
    this.watchTimer = null;
    this.blocked = false;
    this.onBlocked = null;    // () => void
    this.onPlaying = null;
  }

  mount() {
    if (this.el) return this.el;
    const el = document.createElement("div");
    el.id = "yt-stage";
    el.className = "yt-stage hidden";
    el.innerHTML = `<div class="yt-head"><span class="yt-live">● LIVE</span><span class="yt-artist"></span><span class="yt-title"></span></div>
      <div class="yt-frame"><div id="yt-player"></div></div>
      <div class="yt-foot"><span class="muted small">Scène · clip officiel via YouTube</span><button class="btn sm ghost yt-skip" title="Extrait suivant">⏭</button></div>`;
    document.body.appendChild(el);
    el.querySelector(".yt-skip").onclick = () => this.finish("skip");
    this.el = el;
    return el;
  }

  async ensurePlayer() {
    this.mount();
    if (this.player) return this.readyPromise;
    const YT = await loadApi();
    this.readyPromise = new Promise((resolve) => {
      this.player = new YT.Player("yt-player", {
        width: 356, height: 200,
        playerVars: { autoplay: 0, controls: 1, rel: 0, modestbranding: 1, playsinline: 1, iv_load_policy: 3, origin: location.origin },
        events: {
          onReady: () => { try { this.player.setVolume(Math.round(this.volume * 100)); } catch {} resolve(this.player); },
          onStateChange: (e) => this.handleState(e.data),
          onError: () => this.finish("error"),
        },
      });
    });
    return this.readyPromise;
  }

  handleState(state) {
    const YT = window.YT;
    if (!YT || !this.current) return;
    if (state === YT.PlayerState.PLAYING) {
      clearTimeout(this.watchTimer);
      this.blocked = false;
      if (!this.current.started) {
        this.current.started = true;
        this.updateTitle();
        if (this.onPlaying) this.onPlaying();
        const seconds = Number(this.current.seconds || 0);
        if (seconds > 0) {
          clearTimeout(this.clipTimer);
          this.clipTimer = setTimeout(() => this.finish("clip"), Math.max(3, seconds - 1.5) * 1000);
        }
      }
    } else if (state === YT.PlayerState.ENDED) {
      this.finish("ended");
    }
  }

  updateTitle() {
    if (!this.el || !this.player) return;
    try {
      const data = this.player.getVideoData();
      const t = this.el.querySelector(".yt-title");
      if (data && data.title) t.textContent = data.title;
    } catch {}
  }

  /**
   * Joue un extrait. { videoId, start, seconds, volume, artist, title, onEnded }
   * onEnded est appelé quand l'extrait se termine (durée, fin de vidéo, erreur, skip).
   */
  async playClip(opts) {
    const token = Symbol("yt");
    this.current = { token, onEnded: opts.onEnded, seconds: opts.seconds, started: false };
    this.volume = Math.max(0, Math.min(1, opts.volume ?? this.volume));
    try {
      await this.ensurePlayer();
    } catch (e) {
      console.warn("YouTube", e);
      const cur = this.current; this.current = null;
      if (cur && cur.token === token && cur.onEnded) cur.onEnded("unavailable");
      return;
    }
    if (!this.current || this.current.token !== token) return;
    this.el.classList.remove("hidden");
    this.el.querySelector(".yt-artist").textContent = opts.artist || "";
    this.el.querySelector(".yt-title").textContent = opts.title || "";
    clearInterval(this.fadeTimer);
    try {
      this.player.setVolume(Math.round(this.volume * 100));
      this.player.loadVideoById({ videoId: opts.videoId, startSeconds: Math.max(0, Number(opts.start) || 0) });
    } catch (e) {
      this.finish("error");
      return;
    }
    // Autoplay bloqué ? (l'état ne passe jamais à PLAYING)
    clearTimeout(this.watchTimer);
    this.watchTimer = setTimeout(() => {
      if (this.current && this.current.token === token && !this.current.started) {
        this.blocked = true;
        if (this.onBlocked) this.onBlocked();
      }
    }, 6000);
  }

  /** À appeler dans un geste utilisateur si l'autoplay a été bloqué. */
  tryResume() {
    if (!this.blocked || !this.player || !this.current) return;
    try { this.player.playVideo(); } catch {}
  }

  finish(reason) {
    const cur = this.current;
    if (!cur) return;
    clearTimeout(this.clipTimer);
    clearTimeout(this.watchTimer);
    this.current = null;
    this.fadeTo(0, 1.2, () => { try { this.player && this.player.pauseVideo(); } catch {} });
    if (cur.onEnded) cur.onEnded(reason);
  }

  fadeTo(target, seconds, done) {
    clearInterval(this.fadeTimer);
    if (!this.player) { if (done) done(); return; }
    let v; try { v = this.player.getVolume() / 100; } catch { v = this.volume; }
    const steps = Math.max(1, Math.round(seconds / 0.06));
    const delta = (target - v) / steps;
    let i = 0;
    this.fadeTimer = setInterval(() => {
      i += 1; v += delta;
      try { this.player.setVolume(Math.round(Math.max(0, Math.min(1, v)) * 100)); } catch {}
      if (i >= steps) { clearInterval(this.fadeTimer); this.fadeTimer = null; if (done) done(); }
    }, 60);
  }

  setVolume(v) {
    this.volume = Math.max(0, Math.min(1, v));
    if (this.player && this.current && !this.fadeTimer) { try { this.player.setVolume(Math.round(this.volume * 100)); } catch {} }
  }

  /** Arrêt immédiat (fondu court) et masquage de l'écran de scène. */
  stop(fade = 0.35) {
    clearTimeout(this.clipTimer);
    clearTimeout(this.watchTimer);
    this.current = null;
    this.blocked = false;
    if (this.player) {
      this.fadeTo(0, fade, () => {
        try { this.player.pauseVideo(); } catch {}
        try { this.player.setVolume(Math.round(this.volume * 100)); } catch {}
      });
    }
    if (this.el) this.el.classList.add("hidden");
  }

  get active() { return !!this.current; }
}
