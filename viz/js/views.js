// views.js — 1 Cop view / 2 Thief view / 3 Truth view.
// Cop view: floor = cop belief, scent visible, thief hidden (ghost at belief argmax).
// Thief view: floor = thief_belief, cop hidden (ghost at its belief argmax), no scent.
// Truth view: both tokens + belief-error ribbon from belief-argmax to the true thief.
import * as THREE from 'three';
import { cellPos } from './board.js';
import { argmax2d } from './data.js';

export function createViews(scene){
  let view = 3;
  const ribbon = new THREE.Mesh(new THREE.BoxGeometry(1, 0.03, 0.05),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5,
      blending: THREE.AdditiveBlending, depthWrite: false }));
  ribbon.visible = false;
  scene.add(ribbon);

  function ribbonBetween(a, b, N){
    const pa = cellPos(...a, N, 0.12), pb = cellPos(...b, N, 0.12);
    const d = pb.clone().sub(pa), len = d.length();
    ribbon.visible = len > 0.01;
    if (!ribbon.visible) return;
    ribbon.position.copy(pa).addScaledVector(d, 0.5);
    ribbon.scale.set(len, 1, 1);
    ribbon.rotation.y = -Math.atan2(d.z, d.x);
  }

  function apply(f, { board, agents, scent, N }){
    const copPeak = argmax2d(f.belief);
    const thiefPeak = f.thief_belief ? argmax2d(f.thief_belief) : null;
    board.setBelief(view === 2 ? f.thief_belief : f.belief);
    ribbon.visible = false;
    if (view === 1){
      agents.setVis({ copVis: true, thiefVis: false, ghostThiefAt: copPeak, N });
      scent.setVisible(true);
    } else if (view === 2){
      agents.setVis({ copVis: false, thiefVis: true, ghostCopAt: thiefPeak, N });
      scent.setVisible(false);
    } else {
      agents.setVis({ copVis: true, thiefVis: true, N });
      scent.setVisible(true);
      if (copPeak) ribbonBetween(copPeak, f.thief, N);
    }
  }

  return { apply, set: v => { view = v; }, get view(){ return view; } };
}
