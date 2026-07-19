// finales.js — capture: slow-mo dolly-in + beam flare + frozen scoreboard.
// Survival: clock ring completes + thief fireworks. Tamper: red theme pulse.
// prefers-reduced-motion: finales become instant cuts.
import * as THREE from 'three';
import { COLORS } from './scene.js';

export function createFinales({ scene, camera, controls, agents, rig, reduce }){
  const sb = document.getElementById('scoreboard');
  const ring = document.getElementById('ring');
  let mode = null, t = 0, ctx = null, burst = null, shown = false;

  function fireworks(at){
    const n = 140, pos = new Float32Array(n * 3), vel = [];
    for (let i = 0; i < n; i++){
      pos.set([at.x, at.y + 0.6, at.z], i * 3);
      const th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
      vel.push(new THREE.Vector3(Math.sin(ph) * Math.cos(th), Math.abs(Math.cos(ph)) + 0.4,
        Math.sin(ph) * Math.sin(th)).multiplyScalar(1.5 + Math.random() * 2));
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    burst = new THREE.Points(g, new THREE.PointsMaterial({ color: COLORS.thief,
      size: 0.09, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    burst.userData = { vel }; burst.frustumCulled = false;
    scene.add(burst);
  }

  function board(title, cls, score){
    sb.hidden = false; sb.className = cls; shown = true;
    document.getElementById('sb-title').textContent = title;
    document.getElementById('sb-score').textContent = `cop ${score.cop} : ${score.thief} thief`;
  }
  function finish(){
    ring.hidden = true;
    if (mode === 'capture') board('Capture', 'cop', ctx.score);
    else board('Thief escapes', 'thief', ctx.score);
  }

  function trigger(outcome, c){
    mode = outcome; t = 0; ctx = c;
    rig.setEnabled(false);
    if (outcome === 'tamper_forfeit'){
      document.body.classList.add('tamper');
      board('Match void', 'bad', { cop: 0, thief: 0 });
      return;
    }
    if (reduce){ finish(); return; }                     // instant cut
    if (outcome === 'survival'){ ring.hidden = false; fireworks(ctx.pos); }
  }

  function update(dt){
    if (burst){
      const p = burst.geometry.attributes.position.array, vel = burst.userData.vel;
      for (let i = 0; i < vel.length; i++){
        vel[i].y -= dt * 2.2;
        p[i * 3] += vel[i].x * dt; p[i * 3 + 1] += vel[i].y * dt; p[i * 3 + 2] += vel[i].z * dt;
      }
      burst.geometry.attributes.position.needsUpdate = true;
      burst.material.opacity -= dt * 0.45;
      if (burst.material.opacity <= 0){ scene.remove(burst); burst = null; }
    }
    if (!mode || mode === 'tamper_forfeit' || shown || reduce) return;
    t += dt;
    if (mode === 'capture'){                             // dolly-in on the arrest cell
      const k = 1 - Math.exp(-dt * 2);
      controls.target.lerp(ctx.pos, k);
      const dir = camera.position.clone().sub(controls.target), d = dir.length();
      camera.position.copy(controls.target)
        .addScaledVector(dir.normalize(), d + (3.4 - d) * k);
      agents.flare(Math.min(1, t * 1.5));
      if (t > 2.0) finish();
    } else if (mode === 'survival'){
      const p = Math.min(1, t / 1.6);                    // clock ring completes
      ring.style.setProperty('--p', (p * 100).toFixed(1) + '%');
      if (t > 2.1) finish();
    }
  }

  function active(){ return !!mode; }
  function reset(){
    mode = null; t = 0; shown = false;
    sb.hidden = true; ring.hidden = true; ring.style.setProperty('--p', '0%');
    document.body.classList.remove('tamper');
    agents.flare(0);
    if (burst){ scene.remove(burst); burst = null; }
    rig.setEnabled(true);
  }

  return { trigger, update, reset, active };
}
