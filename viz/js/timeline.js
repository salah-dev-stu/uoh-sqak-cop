// timeline.js — pure scrub-bar / turn math (no DOM, no three.js; node-testable)

export function clampTurn(t, nFrames){
  return Math.max(0, Math.min(nFrames - 1, t));
}

export function frameIndex(t){ return Math.floor(t); }

export function frameFrac(t){ return t - Math.floor(t); }

// Fraction 0..1 along the scrub bar for a 1-indexed turn number.
export function turnFraction(turn, nFrames){
  return nFrames > 1 ? (turn - 1) / (nFrames - 1) : 0;
}

// Event list -> marker positions for the scrub bar.
export function markers(events, nFrames){
  return events.map(e => ({ frac: turnFraction(e.turn, nFrames), type: e.type, turn: e.turn }));
}

// Step one whole turn from a possibly-fractional position.
export function stepTurn(t, dir, nFrames){
  return clampTurn(Math.round(t) + dir, nFrames);
}

// Which glyph chips are revealed once `turn` has passed.
export function visibleChips(chips, turn){
  return chips.filter(c => c.step <= turn);
}
