// agents.js — cop/thief tokens with beams, ghost markers, micro hop pulses, beam flare
import * as THREE from 'three';
import { COLORS } from './scene.js';
import { cellPos } from './board.js';

function token(scene, color){
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.IcosahedronGeometry(0.38, 0),
    new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 1.6,
      metalness: 0.3, roughness: 0.2 }));
  body.position.y = 0.6; g.add(body);
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 3.4, 10),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.32,
      blending: THREE.AdditiveBlending, depthWrite: false }));
  beam.position.y = 1.7; g.add(beam);
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.5, 28),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.6,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.04; g.add(ring);
  const light = new THREE.PointLight(color, 6, 4); light.position.y = 0.7; g.add(light);
  g.userData = { body, beam };
  scene.add(g); return g;
}

// Wireframe stand-in for "where the opponent believes this agent is".
function ghost(scene, color){
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.IcosahedronGeometry(0.34, 0),
    new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.35 }));
  body.position.y = 0.55; g.add(body);
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.4, 0.46, 24),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.25,
      side: THREE.DoubleSide }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.04; g.add(ring);
  g.visible = false; scene.add(g); return g;
}

export function createAgents(scene, reduce){
  const cop = token(scene, COLORS.cop), thief = token(scene, COLORS.thief);
  const gCop = ghost(scene, COLORS.cop), gThief = ghost(scene, COLORS.thief);
  let hop = 0;

  function update({ a, b, f, N, dt }){
    cop.position.lerpVectors(cellPos(...a.cop, N), cellPos(...b.cop, N), f);
    thief.position.lerpVectors(cellPos(...a.thief, N), cellPos(...b.thief, N), f);
    hop = Math.max(0, hop - dt * 3);
    const bob = reduce ? 0 : Math.sin(performance.now() * 0.004) * 0.05;
    const lift = reduce ? 0 : Math.sin(hop * Math.PI) * 0.18;
    cop.userData.body.position.y = 0.55 + bob + lift;
    thief.userData.body.position.y = 0.55 - bob + lift;
  }

  function pulse(){ if (!reduce) hop = 1; }

  function setVis({ copVis, thiefVis, ghostCopAt, ghostThiefAt, N }){
    cop.visible = copVis; thief.visible = thiefVis;
    gCop.visible = !!ghostCopAt; gThief.visible = !!ghostThiefAt;
    if (ghostCopAt) gCop.position.copy(cellPos(...ghostCopAt, N));
    if (ghostThiefAt) gThief.position.copy(cellPos(...ghostThiefAt, N));
  }

  function flare(v){                      // capture-finale cop beam flare
    cop.userData.beam.material.opacity = 0.32 + v * 0.5;
    cop.userData.beam.scale.set(1 + v * 1.6, 1, 1 + v * 1.6);
  }

  return { update, pulse, setVis, flare,
    copPos: () => cop.position, thiefPos: () => thief.position };
}
