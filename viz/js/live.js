// live.js — LIVE league mode: poll /api/spectate, merge own-knowledge frames,
// map them into the renderer's schema-v2 shape, and drive the match-room panel.
// The merge + mapping are pure (node-tested); the poller + panel are DOM/fetch
// only (no three.js). Truth view is meaningless live — own knowledge is the show.
import { argmax2d } from './data.js';

export function frameKey(f){ return `${f.sub_game}:${f.turn}:${f.phase}`; }

export function mergeFrames(seen, incoming){
  const keys = new Set(seen.map(frameKey));
  const out = seen.slice();
  for (const f of incoming){
    const k = frameKey(f);
    if (!keys.has(k)){ keys.add(k); out.push(f); }
  }
  return out;
}

function toViz(sf){                              // opponent = belief peak (a ghost), never truth
  const ghost = argmax2d(sf.belief), isCop = sf.role === 'police';
  return { turn: sf.turn, cop: isCop ? sf.me : ghost, thief: isCop ? ghost : sf.me,
    belief: isCop ? sf.belief : null, thief_belief: isCop ? null : sf.belief,
    scent: {}, barriers: sf.known_barriers || [], hint: sf.last_hint, intent: sf.last_intent };
}

export function spectateToViz(frames){
  const outcome = frames.reduce((o, f) => (f.outcome ? f.outcome.result : o), null);
  return { viz_schema: 2, size: 7, frames: frames.map(toViz), outcome };
}

export function createLive({ onGame, onEnd, intervalMs = 800 }){
  let seen = [], timer = null;
  async function poll(){
    try {
      const data = await (await fetch('/api/spectate?ts=' + Date.now())).json();
      const before = seen.length;
      seen = mergeFrames(seen, data.frames || []);
      if (seen.length > before) onGame(spectateToViz(seen));
      if (seen.some(f => f.outcome)){ stop(); if (onEnd) onEnd(); }
    } catch (e){ /* server gone mid-match: keep the last rendered state */ }
  }
  function start(){ seen = []; stop(); timer = setInterval(poll, intervalMs); poll(); }
  function stop(){ if (timer){ clearInterval(timer); timer = null; } }
  return { start, stop };
}

export function bindMatchPanel({ onStart }){
  const go = document.getElementById('match-go');
  if (!go) return;
  const err = document.getElementById('match-err');
  go.addEventListener('click', async () => {
    err.textContent = '';
    const body = { opponent_url: document.getElementById('match-url').value.trim(),
      role: document.getElementById('match-role').value };
    try {
      const r = await fetch('/api/match', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const j = await r.json();
      if (!r.ok || !j.ok) err.textContent = j.error || ('error ' + r.status);
      else onStart();
    } catch (e){ err.textContent = 'server unreachable'; }
  });
}

export async function serverHasMatch(){
  try { return (await fetch('/api/spectate')).ok; }
  catch (e){ return false; }
}
