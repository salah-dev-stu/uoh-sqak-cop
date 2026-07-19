// scent.js — particle wake: emitted from the scent field each turn, rises & fades
// with the field's decay. Additive Points; a black color is invisible, so fading
// the color to black doubles as per-particle opacity.
import * as THREE from 'three';
import { COLORS } from './scene.js';

const MAX = 280;

export function createScent(scene){
  const pos = new Float32Array(MAX * 3), col = new Float32Array(MAX * 3);
  const life = new Float32Array(MAX), amp = new Float32Array(MAX);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const mat = new THREE.PointsMaterial({ size: 0.16, vertexColors: true,
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  scene.add(points);
  const green = new THREE.Color(COLORS.scent);
  let head = 0;

  function emit(r, c, N, v){
    const i = head; head = (head + 1) % MAX;
    pos[i * 3] = c - (N - 1) / 2 + (Math.random() - 0.5) * 0.6;
    pos[i * 3 + 1] = 0.05 + Math.random() * 0.1;
    pos[i * 3 + 2] = r - (N - 1) / 2 + (Math.random() - 0.5) * 0.6;
    life[i] = 1; amp[i] = Math.min(0.9, v);
  }

  // One call per discrete frame advance: emission rate follows field intensity.
  function spawnFrame(scentMap, N){
    for (const k in scentMap){
      const v = scentMap[k];
      if (v <= 0.05) continue;
      const [r, c] = k.split(',').map(Number);
      for (let j = Math.max(1, Math.round(v * 3)); j > 0; j--) emit(r, c, N, v);
    }
  }

  function update(dt){
    for (let i = 0; i < MAX; i++){
      if (life[i] <= 0){ col[i * 3] = col[i * 3 + 1] = col[i * 3 + 2] = 0; continue; }
      life[i] -= dt * 0.55;
      pos[i * 3 + 1] += dt * 0.35;
      const a = Math.max(0, life[i]) * amp[i];
      col[i * 3] = green.r * a; col[i * 3 + 1] = green.g * a; col[i * 3 + 2] = green.b * a;
    }
    geo.attributes.position.needsUpdate = true;
    geo.attributes.color.needsUpdate = true;
  }

  function reset(){ life.fill(0); col.fill(0); geo.attributes.color.needsUpdate = true; }
  function setVisible(v){ points.visible = v; }
  reset();
  return { spawnFrame, update, reset, setVisible };
}
