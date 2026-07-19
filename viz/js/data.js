// data.js — pure game-data parsing & derivation (no DOM, no three.js; node-testable)

export function parseGame(raw){
  if (!raw || raw.viz_schema !== 2 || !Array.isArray(raw.frames) || !raw.frames.length)
    throw new Error('unsupported replay: expected viz_schema 2 with frames');
  return raw;
}

export function manhattan(a, b){ return Math.abs(a[0]-b[0]) + Math.abs(a[1]-b[1]); }

export function argmax2d(grid){
  if (!grid) return null;
  let best = -Infinity, pos = [0, 0];
  for (let r = 0; r < grid.length; r++)
    for (let c = 0; c < grid[r].length; c++)
      if (grid[r][c] > best){ best = grid[r][c]; pos = [r, c]; }
  return pos;
}

// Per-turn events for the scrub bar: barrier placements, capture, end-of-game audit.
export function deriveEvents(game){
  const ev = [];
  let prev = 0;
  for (const f of game.frames){
    if (f.barriers.length > prev) ev.push({ turn: f.turn, type: 'barrier' });
    prev = f.barriers.length;
  }
  const last = game.frames[game.frames.length - 1];
  if (game.outcome === 'capture') ev.push({ turn: last.turn, type: 'capture' });
  ev.push({ turn: last.turn, type: 'audit' });
  return ev;
}

export function distanceSeries(game){
  return game.frames.map(f => manhattan(f.cop, f.thief));
}

// Manhattan distance from the cop's belief peak to the true thief cell, per frame.
export function beliefErrorSeries(game){
  return game.frames.map(f => {
    const p = argmax2d(f.belief);
    return p ? manhattan(p, f.thief) : 0;
  });
}

// Glyph chips in DISPLAY (chronological) order: cop step k, thief step k, ...
// Records arrive as all cop steps 1..N then all thief steps 1..N; verdicts align.
export function glyphModel(game){
  const recs = game.records || [], verds = game.verdicts || [];
  const half = recs.length / 2;
  const chips = recs.map((rec, i) => ({
    side: i < half ? 'cop' : 'thief',
    step: rec.payload.step,
    short: '#' + rec.commit.slice(0, 8),
    payload: rec.payload, nonce: rec.nonce, commit: rec.commit,
    status: (verds[i] && verds[i].status) || 'Verified OK',
  }));
  chips.sort((a, b) => (a.step - b.step) || (a.side === 'cop' ? -1 : 1));
  const firstBad = chips.findIndex(c => c.status !== 'Verified OK');
  return { chips, firstBad, tampered: firstBad >= 0 };
}

// Rough scoreboard estimate: thief earns a point per turn evaded, cop 100 on capture.
// A tamper forfeit voids the match for both sides (0/0).
export function scoreEstimate(game, turn){
  if (game.outcome === 'tamper_forfeit') return { cop: 0, thief: 0 };
  const n = game.frames.length, t = Math.min(turn, n);
  const captured = game.outcome === 'capture' && t >= n;
  return { cop: captured ? 100 : 0, thief: captured ? 0 : t };
}
