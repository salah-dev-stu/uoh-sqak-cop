// showtime.js — one seam for the P7 replay-side features (guided tour + WebM
// recorder; split-screen joins here later). main.js gets a single update()/active()
// hook, keeping it under the ≤150-line budget while the features live in their
// own focused modules.
import { createTour } from './tour.js';
import { createRecorder } from './recorder.js';

export function createShowtime({ sc, rig, setTurn, frameCount, reduce, captionEl }){
  const recorder = createRecorder(sc.renderer.domElement);
  const tour = createTour({ camera: sc.camera, controls: sc.controls, rig, setTurn,
    frameCount, reduce, captionEl, recorder });
  return { update: dt => tour.update(dt), active: () => tour.active() };
}
