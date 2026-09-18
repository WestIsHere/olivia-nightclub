/* Lecteur officiel YouTube : vidéo et son, jamais de fichier téléchargé. */
let apiPromise;
function loadApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("YouTube indisponible")), 15000);
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      clearTimeout(timeout);
      try { previous?.(); } catch {}
      resolve(window.YT);
    };
    const script = document.createElement("script");
    script.src = "https://www.youtube.com/iframe_api";
    script.onerror = () => { clearTimeout(timeout); reject(new Error("YouTube indisponible")); };
    document.head.appendChild(script);
  }).catch((error) => { apiPromise = null; throw error; });
  return apiPromise;
}

export class YouTubeStage {
  constructor() {
    this.el = null;
    this.player = null;
    this.readyPromise = null;
    this.current = null;
    this.volume = 0.7;
    this.blocked = false;
    this.onBlocked = null;
    this.onPlaying = null;
    this.watchTimer = null;
  }

  mount() {
    if (this.el) return this.el;
    const el = document.createElement("section");
    el.id = "yt-stage";
    el.className = "yt-stage hidden";
    el.setAttribute("aria-label", "Écran du showcase de cette boîte");
    el.innerHTML = `<div class="yt-head"><span class="pill red">● En scène</span><b class="yt-artist"></b></div>
      <div class="yt-title"></div><div class="yt-frame"><div id="yt-player"></div></div>
      <div class="yt-status" role="status"></div>
      <div class="yt-foot"><span class="muted small">Vidéo et musique · YouTube · Cette boîte uniquement</span><button class="btn sm gold yt-resume hidden">Activer le clip et le son</button></div>`;
    document.body.appendChild(el);
    this.el = el;
    el.querySelector(".yt-resume").onclick = () => this.tryResume();
    return el;
  }

  ensurePlayer() {
    this.mount();
    if (this.readyPromise) return this.readyPromise;
    this.readyPromise = loadApi().then((YT) => new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("Lecteur YouTube indisponible")), 15000);
      this.player = new YT.Player("yt-player", {
        host: "https://www.youtube-nocookie.com",
        videoId: this.current?.videoId,
        width: "100%", height: "100%",
        playerVars: { autoplay: 0, controls: 1, rel: 0, playsinline: 1, origin: location.origin },
        events: {
          onReady: (event) => { clearTimeout(timeout); resolve(event.target); },
          onStateChange: (event) => {
            if (!this.current) return;
            if (event.data === YT.PlayerState.PLAYING) {
              clearTimeout(this.watchTimer);
              this.blocked = false;
              this.current.started = true;
              this.el.querySelector(".yt-status").textContent = "";
              this.el.querySelector(".yt-resume").classList.add("hidden");
              this.onPlaying?.();
            } else if (event.data === YT.PlayerState.ENDED) this.finish("ended");
          },
          onAutoplayBlocked: () => this.showBlocked(),
          onError: () => this.finish("error"),
        },
      });
    })).catch((error) => {
      this.player?.destroy?.();
      this.player = null;
      this.readyPromise = null;
      this.el.querySelector(".yt-frame").innerHTML = '<div id="yt-player"></div>';
      throw error;
    });
    return this.readyPromise;
  }

  async playClip(opts) {
    this.stop(0);
    const current = { ...opts, token: Symbol("video"), started: false };
    this.current = current;
    this.volume = opts.volume ?? this.volume;
    this.mount();
    this.el.classList.remove("hidden");
    this.el.querySelector(".yt-frame").classList.remove("hidden");
    this.el.querySelector(".yt-artist").textContent = opts.artist || "";
    this.el.querySelector(".yt-title").textContent = opts.title || "";
    this.el.querySelector(".yt-status").textContent = "Connexion à la scène YouTube…";
    try {
      const player = await this.ensurePlayer();
      if (this.current !== current) return;
      player.setVolume(Math.round(this.volume * 100));
      if (this.volume > 0) player.unMute(); else player.mute();
      player.loadVideoById({ videoId: opts.videoId, startSeconds: opts.getStart?.() ?? opts.start ?? 0 });
      this.watchTimer = setTimeout(() => { if (this.current === current && !current.started) this.showBlocked(); }, 4000);
    } catch (error) {
      console.warn("Lecteur showcase YouTube :", error);
      if (this.current === current) this.finish("unavailable");
    }
  }

  showBlocked() {
    if (!this.current) return;
    this.blocked = true;
    this.el.querySelector(".yt-status").textContent = "Clique pour rejoindre le clip avec la musique.";
    const button = this.el.querySelector(".yt-resume");
    button.classList.remove("hidden");
    button.textContent = "Activer le clip et le son";
    button.onclick = () => this.tryResume();
    this.onBlocked?.();
  }

  tryResume() {
    if (!this.blocked || !this.player || !this.current) return;
    try {
      if (this.current.getStart) this.player.seekTo(this.current.getStart(), true);
      this.player.setVolume(Math.round(this.volume * 100));
      if (this.volume > 0) this.player.unMute();
      this.player.playVideo();
    } catch {}
  }

  showMessage(artist, message, retry) {
    this.stop(0);
    this.mount();
    this.el.classList.remove("hidden");
    this.el.querySelector(".yt-artist").textContent = artist;
    this.el.querySelector(".yt-title").textContent = "";
    this.el.querySelector(".yt-frame").classList.add("hidden");
    this.el.querySelector(".yt-status").textContent = message;
    const button = this.el.querySelector(".yt-resume");
    button.classList.toggle("hidden", !retry);
    button.textContent = "Réessayer le clip";
    button.onclick = retry || (() => {});
  }

  finish(reason) {
    const callback = this.current?.onEnded;
    this.stop(0);
    callback?.(reason);
  }

  setVolume(value) {
    this.volume = Math.max(0, Math.min(1, value));
    if (!this.current) return;
    try {
      this.player?.setVolume(Math.round(this.volume * 100));
      if (this.volume > 0) this.player?.unMute(); else this.player?.mute();
    } catch {}
  }

  stop() {
    clearTimeout(this.watchTimer);
    this.current = null;
    this.blocked = false;
    try { this.player?.pauseVideo(); } catch {}
    this.el?.classList.add("hidden");
    this.el?.querySelector(".yt-resume").classList.add("hidden");
  }

  get active() { return !!this.current; }
}
