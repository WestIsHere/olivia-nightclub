import assert from 'node:assert/strict';
import {test} from 'node:test';
import {ClubScreen} from '../web/js/club-screen.js';

function fixture() {
  const stage = {plays: [], stops: 0, playClip(opts) { this.plays.push(opts); }, stop() { this.stops++; }, showMessage() {}};
  const screen = new ClubScreen(stage, {now: () => 1040, volume: () => 0.56});
  return {stage, screen};
}
const pnl = {club_id: 1, showcase_id: 3, artist: 'PNL', ends_at: 1180, video: {key: '3:0:0', video_id: 'BtyHYIpykN0', title: 'Au DD', started_at: 1000, ends_at: 1180}};
const gims = {club_id: 2, showcase_id: 4, artist: 'Gims', ends_at: 1180, video: {...pnl.video, key: '4:0:0', video_id: 'KG6ft_YDp5k'}};

test('deux visiteurs de Palmeray voient le même clip et rejoignent à 40 secondes', () => {
  const a = fixture(), b = fixture();
  a.screen.setClub(1, pnl); b.screen.setClub(1, pnl);
  assert.equal(a.stage.plays[0].videoId, b.stage.plays[0].videoId);
  assert.equal(a.stage.plays[0].getStart(), 40);
  assert.equal(a.stage.plays[0].volume, 0.56);
  a.screen.stop(); b.screen.stop();
});
test('Gims à Babinski ne remplace pas PNL à Palmeray', () => {
  const {screen, stage} = fixture();
  screen.setClub(1, pnl); screen.accept(gims); screen.end({club_id:2, showcase_id:4});
  assert.equal(stage.plays.length, 1);
  assert.equal(screen.snapshot.artist, 'PNL');
  screen.setClub(2, gims);
  assert.equal(stage.plays.at(-1).videoId, gims.video.video_id);
  screen.stop();
});
test('dehors aucun lecteur ; sortir coupe la diffusion ; un événement ancien est ignoré', () => {
  const {screen, stage} = fixture();
  screen.accept(pnl);
  assert.equal(stage.plays.length, 0);
  screen.setClub(1, pnl);
  screen.end({club_id:1, showcase_id:2});
  assert.equal(screen.snapshot.showcase_id, 3);
  screen.setClub(null);
  screen.accept(pnl);
  assert.equal(screen.key, null);
  assert.equal(stage.plays.length, 1);
});
test('réponse réseau tardive ignorée après changement de boîte', async () => {
  const {screen, stage} = fixture();
  let resolve;
  screen.fetchScreen = () => new Promise(r => {resolve = r;});
  screen.setClub(1, pnl);
  const firstResolve = resolve;
  screen.setClub(2, gims);
  firstResolve({server_time:1040, showcase:pnl});
  await Promise.resolve();
  assert.equal(screen.snapshot.artist, 'Gims');
  assert.equal(stage.plays.at(-1).videoId, gims.video.video_id);
  screen.stop();
});
test('une réponse antérieure au démarrage SSE ne coupe pas le nouveau showcase', async () => {
  const {screen} = fixture();
  let resolve;
  screen.fetchScreen = () => new Promise(r => {resolve = r;});
  screen.setClub(1, null);
  screen.accept(pnl);
  resolve({server_time:1039, showcase:null});
  await Promise.resolve();
  assert.equal(screen.snapshot.artist, 'PNL');
  screen.stop();
});
test('les rafraîchissements ne redémarrent pas le clip ; expiration arrête le lecteur', () => {
  const {screen, stage} = fixture();
  screen.setClub(1, pnl); screen.setClub(1, pnl);
  assert.equal(stage.plays.length, 1);
  screen.accept({...pnl, ends_at:1040});
  assert.equal(screen.key, null);
  screen.stop();
});
