import assert from 'node:assert/strict';
import {test} from 'node:test';
import {YouTubeStage} from '../web/js/youtube.js';

class Element {
  constructor() {
    this.children = new Map();
    const classes = new Set();
    this.classList = {add: x => classes.add(x), remove: x => classes.delete(x), contains: x => classes.has(x), toggle: (x, on) => on ? classes.add(x) : classes.delete(x)};
  }
  setAttribute() {}
  querySelector(name) { if (!this.children.has(name)) this.children.set(name, new Element()); return this.children.get(name); }
}
globalThis.document = {createElement: () => new Element(), body: {appendChild() {}}};
globalThis.location = {origin: 'http://localhost:8766'};
let player;
class FakePlayer {
  constructor(id, options) { this.options = options; this.pauses = 0; player = this; }
  setVolume(value) { this.volume = value; }
  unMute() { this.muted = false; }
  mute() { this.muted = true; }
  loadVideoById(value) { this.loaded = value; }
  pauseVideo() { this.pauses++; }
  playVideo() { this.resumed = true; }
  seekTo(value) { this.position = value; }
}
globalThis.window = {YT: {Player: FakePlayer, PlayerState: {PLAYING: 1, ENDED: 0}}};

test('YouTube reçoit le bon clip, la position actuelle et un volume audible ; sortie immédiate', async () => {
  const stage = new YouTubeStage();
  let now = 10;
  const loading = stage.playClip({videoId:'BtyHYIpykN0', volume:0.56, artist:'PNL', getStart: () => now});
  await Promise.resolve();
  assert.equal(player.options.videoId, 'BtyHYIpykN0');
  now = 14;
  player.options.events.onReady({target:player});
  await loading;
  assert.equal(player.loaded.startSeconds, 14);
  assert.equal(player.volume, 56);
  assert.equal(player.muted, false);
  player.options.events.onAutoplayBlocked();
  assert.equal(stage.blocked, true);
  now = 20;
  stage.tryResume();
  assert.equal(player.position, 20);
  assert.equal(player.resumed, true);
  stage.setVolume(0);
  assert.equal(player.muted, true);
  stage.stop();
  assert.equal(stage.active, false);
  assert.equal(stage.el.classList.contains('hidden'), true);
  assert.ok(player.pauses > 0);
});

test('une sortie pendant le chargement empêche le démarrage tardif de la musique', async () => {
  const stage = new YouTubeStage();
  const loading = stage.playClip({videoId:'BtyHYIpykN0', volume:0.7});
  await Promise.resolve();
  const pending = player;
  stage.stop();
  pending.options.events.onReady({target:pending});
  await loading;
  assert.equal(pending.loaded, undefined);
  assert.equal(stage.active, false);
});
