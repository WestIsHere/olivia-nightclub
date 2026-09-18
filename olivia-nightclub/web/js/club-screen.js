/* Un programme serveur par boîte ; aucun tirage vidéo dans le navigateur. */
export class ClubScreen {
  constructor(stage, { fetchScreen, now, volume, onActive } = {}) {
    this.stage = stage;
    this.fetchScreen = fetchScreen;
    this.now = now || (() => Date.now() / 1000);
    this.volume = volume || (() => 0.7);
    this.onActive = onActive || (() => {});
    this.clubId = null;
    this.generation = 0;
    this.key = null;
    this.snapshot = null;
    this.timer = null;
    this.deadline = null;
    this.offset = 0;
    this.onSnapshot = null;
    this.revision = 0;
  }

  setClub(clubId, snapshot) {
    const changed = clubId !== this.clubId;
    if (changed) {
      this.stop();
      this.clubId = clubId;
    }
    if (clubId != null && snapshot !== undefined) this.accept(snapshot);
    if (changed && clubId != null) this.poll(this.generation);
  }

  async poll(generation = this.generation) {
    if (this.clubId == null || generation !== this.generation || !this.fetchScreen) return;
    const id = this.clubId;
    const revision = this.revision;
    clearTimeout(this.timer);
    try {
      const data = await this.fetchScreen(id);
      if (generation !== this.generation || id !== this.clubId) return;
      if (revision === this.revision) {
        if (Number.isFinite(data.server_time)) this.offset = data.server_time - this.now();
        if (this.onSnapshot) this.onSnapshot(data.showcase);
        this.accept(data.showcase, true);
      }
    } catch { /* Le délai local arrête le clip même si le réseau est coupé. */ }
    if (generation === this.generation && id === this.clubId) {
      this.timer = setTimeout(() => this.poll(generation), 5000);
    }
  }

  accept(showcase, fromPoll = false) {
    if (showcase && Number(showcase.club_id) !== Number(this.clubId)) return;
    if (showcase && this.snapshot && showcase.showcase_id < this.snapshot.showcase_id) return;
    if (showcase?.showcase_id === this.snapshot?.showcase_id && showcase?.video && this.snapshot?.video && showcase.video.started_at < this.snapshot.video.started_at) return;
    if (!fromPoll) this.revision += 1;
    const now = this.now() + this.offset;
    this.snapshot = showcase;
    if (!showcase || showcase.ends_at <= now) {
      clearTimeout(this.deadline);
      this.key = null;
      this.stage.stop(0);
      this.onActive(false);
      return;
    }
    const video = showcase.video;
    const key = video?.key || `missing:${showcase.showcase_id}`;
    if (key === this.key) return;
    this.key = key;
    clearTimeout(this.deadline);
    this.stage.stop(0);
    const end = Math.min(video?.ends_at || showcase.ends_at, showcase.ends_at);
    this.deadline = setTimeout(() => {
      this.stage.stop(0);
      this.key = null;
      this.onActive(false);
      this.poll();
    }, Math.max(0, end - now) * 1000);
    if (!video) {
      this.stage.showMessage(showcase.artist, "Aucun clip YouTube configuré pour cet artiste.");
      this.onActive(false);
      return;
    }
    if (end <= now) return;
    this.onActive(true);
    this.stage.playClip({
      videoId: video.video_id, artist: showcase.artist, title: video.title,
      start: Math.max(0, now - video.started_at), seconds: end - now,
      // Calculé après chargement du lecteur, pour rejoindre la position courante.
      getStart: () => Math.max(0, this.now() + this.offset - video.started_at),
      volume: this.volume(), shared: true,
      onEnded: (reason) => {
        if (key !== this.key) return;
        this.onActive(false);
        this.stage.showMessage(showcase.artist, reason === "ended" ? "Le clip est terminé. La scène reprend au prochain morceau." : "Ce clip est indisponible dans le lecteur YouTube. Tu peux réessayer.", () => {
          this.key = null;
          this.accept(this.snapshot);
        });
      },
    });
  }

  end(event) {
    if (Number(event.club_id) !== Number(this.clubId)) return;
    if (this.snapshot && event.showcase_id !== this.snapshot.showcase_id) return;
    this.accept(null);
  }

  stop() {
    this.generation += 1;
    clearTimeout(this.timer);
    clearTimeout(this.deadline);
    this.clubId = null;
    this.snapshot = null;
    this.key = null;
    this.stage.stop(0);
    this.onActive(false);
  }
}
