// tour.js — a scripted ~25 s guided flight over the honest fixture. No three.js
// import: it drives the injected camera/controls (.position.set/.target.set) and
// the shared transport (setTurn), so its math stays node-testable. Esc restores
// the user camera; reduced-motion keeps the captions but cancels the flight.

// Absolute-timed keyframes; `turn` scrubs the replay forward beat by beat.
export function tourBeats(nFrames){
  const last = Math.max(0, nFrames - 1);
  const at = f => Math.round(last * f);
  return [
    { t: 0,  pos: [0, 10, 11], target: [0, 0, 0],   turn: 0,        caption: 'A 7×7 board. Two agents. No referee.' },
    { t: 5,  pos: [7, 3.5, 7], target: [0, 0, 0],   turn: at(0.25), caption: 'The thief leaves a scent wake in the grid.' },
    { t: 10, pos: [-7, 5, 6],  target: [0, 0.3, 0], turn: at(0.5),  caption: 'A matched filter turns that wake into belief.' },
    { t: 15, pos: [9, 5, -2],  target: [0, 0.3, 0], turn: at(0.78), caption: 'Every move is sealed — commit first, reveal later.' },
    { t: 20, pos: [0, 12, 9],  target: [0, 0, 0],   turn: last,     caption: 'End-game: the nonces open, the audit runs… Verified OK.' },
    { t: 24, pos: [0, 10, 11], target: [0, 0, 0],   turn: last,     caption: '' },
  ];
}

const smooth = x => x * x * (3 - 2 * x);

export function sampleTour(beats, clock){
  const end = beats[beats.length - 1].t;
  const c = Math.max(0, Math.min(end, clock));
  let i = 0;
  while (i < beats.length - 1 && beats[i + 1].t <= c) i++;
  const a = beats[i], b = beats[Math.min(i + 1, beats.length - 1)];
  const e = smooth(((c - a.t) / ((b.t - a.t) || 1)));
  const mix = (p, q) => p.map((v, k) => v + (q[k] - v) * e);
  return { pos: mix(a.pos, b.pos), target: mix(a.target, b.target),
    turn: a.turn, caption: a.caption, done: c >= end };
}

export function createTour({ camera, controls, rig, setTurn, frameCount, reduce, captionEl, recorder }){
  let active = false, clock = 0, beats = [];

  function start(){
    if (active) return;
    active = true; clock = 0; beats = tourBeats(frameCount());
    rig.setEnabled(false);
    captionEl.hidden = false; captionEl.classList.add('on');
    recorder && recorder.start();
  }

  function stop(finished){
    if (!active) return;
    active = false;
    captionEl.classList.remove('on');
    captionEl.hidden = true;
    rig.setEnabled(true);
    recorder && recorder.stop(finished);   // finished tour → save the clip
  }

  function update(dt){
    if (!active) return;
    clock += dt;
    const s = sampleTour(beats, clock);
    setTurn(s.turn);
    captionEl.textContent = s.caption;
    if (!reduce){
      camera.position.set(s.pos[0], s.pos[1], s.pos[2]);
      controls.target.set(s.target[0], s.target[1], s.target[2]);
    }
    if (s.done) stop(true);
  }

  addEventListener('keydown', e => {
    if (e.key === 't' || e.key === 'T'){ active ? stop(false) : start(); }
    else if (e.key === 'Escape' && active) stop(false);
    else if ((e.key === 'r' || e.key === 'R') && recorder) recorder.toggle();
  });

  return { start, stop, update, active: () => active };
}
