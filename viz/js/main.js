// main.js — boot, game loading (live API -> fixture fallback), loop, wiring.
import { createScene } from './scene.js';
import { createBoard, cellPos } from './board.js';
import { createAgents } from './agents.js';
import { createScent } from './scent.js';
import { createBarriers } from './barriers.js';
import { createRig } from './camera_rig.js';
import { createFinales } from './finales.js';
import { createRail } from './crypto_rail.js';
import { createHud, bindTransport } from './hud.js';
import { createViews } from './views.js';
import { initCapture } from './capture.js';
import { createShowtime } from './showtime.js';
import { bindKeys } from './keys.js';
import { bindMatchPanel, createLive, serverHasMatch } from './live.js';
import * as D from './data.js';
import * as T from './timeline.js';

const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, $ = id => document.getElementById(id);
const sc = createScene();
const board = createBoard(sc.scene);
const agents = createAgents(sc.scene, reduce);
const scent = createScent(sc.scene);
const walls = createBarriers(sc.scene, reduce);
const rig = createRig(sc.camera, sc.controls, reduce);
const views = createViews(sc.scene);
const hud = createHud();
const rail = createRail($('rail'), $('banner'), $('popover'));
const finales = createFinales({ scene: sc.scene, camera: sc.camera,
  controls: sc.controls, agents, rig, reduce });
const shoot = initCapture(sc);

const S = { game: null, turn: 0, playing: true, speed: 1, honest: true,
  last: -1, ended: false, dist: [], err: [] };
let dragging = false;
const showtime = createShowtime({ sc, rig, views, board, agents, scent, setTurn, reduce, captionEl: $('tour-cap'), frameCount: () => S.game?.frames.length ?? 0 });

async function fetchGame(fresh){
  if (!S.honest) return (await fetch('replay3d_tampered.json')).json();
  if (fresh){
    try { return await (await fetch('/api/game?ts=' + Date.now())).json(); }
    catch (e){ /* offline: fall through to the bundled replay */ }
  }
  return (await fetch('replay3d.json')).json();
}

async function loadGame(fresh, override){
  let raw;
  try { raw = D.parseGame(override ?? await fetchGame(fresh)); }
  catch (e){ if (!S.game) throw e; return; }             // keep current game on failure
  const grew = !S.game || S.game.size !== raw.size;       // avoid rebuild flicker live
  S.game = raw; S.turn = 0; S.last = -1; S.ended = false; S.playing = true;
  S.dist = D.distanceSeries(raw); S.err = D.beliefErrorSeries(raw);
  S.hints = raw.frames.reduce((acc, f, i) => {
    acc.push(f.hint ? { text: f.hint, intent: f.intent, turn: f.turn } : acc[i - 1] ?? null);
    return acc;
  }, []);
  if (grew) board.rebuild(raw.size);
  scent.reset(); walls.reset(); finales.reset();
  rail.setGame(D.glyphModel(raw)); rail.reset();
  hud.setMarkers(D.deriveEvents(raw), raw.frames.length);
  $('play').textContent = 'Pause';
  $('scrub').max = raw.frames.length - 1;
}

const frameAt = i => S.game.frames[T.clampTurn(i, S.game.frames.length)];

function applyDiscrete(i, forward){
  const f = frameAt(i);
  views.apply(f, { board, agents, scent, N: S.game.size });
  if (forward){ agents.pulse(); } else { scent.reset(); }
  scent.spawnFrame(f.scent, S.game.size);            // field visible even when scrubbed/paused
  walls.sync(f.barriers, S.game.size, forward);
  rail.reveal(f.turn);
  const h = S.hints[i];
  hud.setHint(h && `“${h.text}” · t${h.turn}`, h?.intent, views.view === 3);
  hud.update({ gap: S.dist[i], barriers: f.barriers.length,
    score: i >= S.game.frames.length - 1 ? D.scoreEstimate(S.game, f.turn) : null,
    turn: f.turn, nTurns: S.game.frames.length });
  hud.drawSpark(S.dist, S.err, i);
}

function endGame(){
  S.ended = true; S.playing = false;
  $('play').textContent = 'Replay';
  const f = frameAt(S.game.frames.length - 1);
  finales.trigger(S.game.outcome, { score: D.scoreEstimate(S.game, f.turn),
    pos: cellPos(f.thief[0], f.thief[1], S.game.size) });
  rail.startAudit();
}

function setTurn(t){
  S.turn = T.clampTurn(t, S.game.frames.length);
  if (S.ended && S.turn < S.game.frames.length - 1){
    S.ended = false; finales.reset(); rail.rearm();
  }
}

function update(dt){
  if (!S.game) return;
  const n = S.game.frames.length;
  if (S.playing && !dragging){
    const slow = !reduce && !S.ended &&
      S.game.outcome === 'capture' && S.turn > n - 2.2;   // 0.25x capture slow-mo
    S.turn += dt * S.speed * 0.85 * (slow ? 0.25 : 1);
    if (S.turn >= n - 1){ S.turn = n - 1; S.playing = false; if (!S.ended) endGame(); }
  }
  const i = T.frameIndex(S.turn), f = T.frameFrac(S.turn);
  if (i !== S.last){ applyDiscrete(i, i === S.last + 1); S.last = i; }
  agents.update({ a: frameAt(i), b: frameAt(i + 1), f, N: S.game.size, dt });
  scent.update(dt); walls.update(dt); finales.update(dt); showtime.update(dt);
  if (!finales.active() && !showtime.active())
    rig.update(dt, agents.copPos(), agents.thiefPos(), S.dist[i]);
  if (!dragging) $('scrub').value = S.turn;
}

bindTransport({
  onPlay(){
    if (S.ended){ setTurn(0); S.last = -1; }
    S.playing = !S.playing;
    $('play').textContent = S.playing ? 'Pause' : 'Play';
  },
  onScrub(v){ dragging = true; S.playing = false; $('play').textContent = 'Play'; setTurn(v); },
  onScrubEnd(){ dragging = false; },
  onSpeed(s){ S.speed = s; },
  onNew(){ loadGame(true); },
  onFixture(honest){ S.honest = honest; loadGame(false); },
  onView(v){ views.set(v); S.last = -1; },
  onQuality(){ return sc.toggleQuality(); },
});

bindKeys({ $, S, T, setTurn, shoot });

const live = createLive({
  onGame: g => loadGame(false, g).then(() => { S.turn = S.game.frames.length - 1; S.playing = false; }),
  onEnd: () => { $('play').textContent = 'Ended'; },
});
bindMatchPanel({ onStart: () => { document.body.classList.add('live'); live.start(); } });
serverHasMatch().then(ok => { if (!ok) $('match')?.setAttribute('hidden', ''); });

let prev = performance.now();
function tick(now){
  requestAnimationFrame(tick);
  const dt = Math.min(0.05, (now - prev) / 1000); prev = now;
  update(dt);
  sc.controls.update();
  if (!showtime.paintSplit(S.game ? frameAt(T.frameIndex(S.turn)) : null, S.game?.size)) sc.render();
}
await loadGame(true);
requestAnimationFrame(tick);
