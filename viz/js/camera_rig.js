// camera_rig.js — follow-cam framing both agents + action centroid, auto-zoom on
// gap close. User orbit overrides; follow resumes after 4 s idle. Reduced motion
// disables auto-rotate (follow damping itself stays gentle).
import * as THREE from 'three';

const IDLE_MS = 4000;

export function createRig(camera, controls, reduce){
  let userAt = -1e9, enabled = true;
  controls.autoRotate = !reduce;
  controls.autoRotateSpeed = 0.32;
  controls.addEventListener('start', () => { userAt = performance.now(); });
  const want = new THREE.Vector3(), dir = new THREE.Vector3();

  function update(dt, copP, thiefP, gap){
    const idle = performance.now() - userAt > IDLE_MS;
    controls.autoRotate = !reduce && idle && enabled;
    if (!enabled || !idle) return;
    want.addVectors(copP, thiefP).multiplyScalar(0.5); want.y = 0.3;
    controls.target.lerp(want, 1 - Math.exp(-dt * 1.8));
    const wantDist = 9 + (gap ?? 8) * 0.55;             // zoom in as the gap closes
    dir.subVectors(camera.position, controls.target);
    const d = dir.length();
    const nd = d + (wantDist - d) * (1 - Math.exp(-dt * 1.2));
    camera.position.copy(controls.target).addScaledVector(dir.normalize(), nd);
  }

  function setEnabled(v){ enabled = v; if (!v) controls.autoRotate = false; }
  return { update, setEnabled };
}
