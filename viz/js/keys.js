// keys.js — the arena keyboard map (extracted so main.js stays lean). 4/T/R and
// Esc are owned by split.js/tour.js; this covers transport, views, and utilities.
import { pressView } from './hud.js';

export function bindKeys({ $, S, T, setTurn, shoot }){
  addEventListener('keydown', e => {
    if (e.key === ' '){ e.preventDefault(); $('play').click(); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight'){
      e.preventDefault(); S.playing = false; $('play').textContent = 'Play';
      if (S.game) setTurn(T.stepTurn(S.turn, e.key === 'ArrowRight' ? 1 : -1, S.game.frames.length));
    }
    else if (e.key === '1' || e.key === '2' || e.key === '3') pressView(e.key);
    else if (e.key === 'n' || e.key === 'N') $('new').click();
    else if (e.key === 's' || e.key === 'S') shoot();
    else if (e.key === 'q' || e.key === 'Q') $('quality').click();
  });
}
