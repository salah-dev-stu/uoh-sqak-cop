// barriers.js — amber walls with a slam: squash-stretch drop + expanding ground ring
import * as THREE from 'three';
import { COLORS } from './scene.js';
import { cellPos } from './board.js';

export function createBarriers(scene, reduce){
  const map = new Map();
  const rings = [];
  const boxGeo = new THREE.BoxGeometry(0.8, 0.85, 0.8);
  const ringGeo = new THREE.RingGeometry(0.42, 0.52, 26);

  function spawn(r, c, N, animate){
    const b = new THREE.Mesh(boxGeo, new THREE.MeshStandardMaterial({
      color: 0x6b4a12, emissive: COLORS.barrier, emissiveIntensity: 0.45,
      roughness: 0.5, metalness: 0.2 }));
    b.position.copy(cellPos(r, c, N, 0.425));
    if (animate && !reduce){ b.position.y = 3.2; b.userData.t = 0; }
    scene.add(b); map.set(r + ',' + c, b);
  }

  function slamRing(x, z){
    const m = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({
      color: COLORS.barrier, transparent: true, opacity: 0.8,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.position.set(x, 0.03, z);
    scene.add(m); rings.push(m);
  }

  // Reconcile scene walls with the frame's barrier list (handles scrubbing back).
  function sync(list, N, animate){
    const want = new Set(list.map(([r, c]) => r + ',' + c));
    for (const [id, b] of map)
      if (!want.has(id)){ scene.remove(b); b.material.dispose(); map.delete(id); }
    for (const [r, c] of list)
      if (!map.has(r + ',' + c)) spawn(r, c, N, animate);
  }

  function update(dt){
    for (const b of map.values()){
      if (b.userData.t === undefined) continue;
      b.userData.t += dt * 2.4;
      const t = b.userData.t;
      if (t < 1){ b.position.y = 3.2 - (3.2 - 0.425) * t * t; }   // accelerating drop
      else if (t < 1.5){                                          // slam: squash + ring
        const s = (t - 1) / 0.5, sq = Math.sin(s * Math.PI) * 0.35;
        b.scale.set(1 + sq * 0.6, 1 - sq, 1 + sq * 0.6);
        b.position.y = 0.425 * (1 - sq * 0.5);
        if (!b.userData.rung){ b.userData.rung = 1; slamRing(b.position.x, b.position.z); }
      } else { b.scale.set(1, 1, 1); b.position.y = 0.425; delete b.userData.t; }
    }
    for (let i = rings.length - 1; i >= 0; i--){
      const m = rings[i];
      m.scale.multiplyScalar(1 + dt * 3.2);
      m.material.opacity -= dt * 1.6;
      if (m.material.opacity <= 0){ scene.remove(m); m.material.dispose(); rings.splice(i, 1); }
    }
  }

  function reset(){
    for (const b of map.values()){ scene.remove(b); b.material.dispose(); }
    map.clear();
    rings.forEach(m => { scene.remove(m); m.material.dispose(); });
    rings.length = 0;
  }

  return { sync, update, reset };
}
