// scene.js — renderer, camera, lights, bloom composer, quality toggle (Low/High)
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

export const COLORS = {
  cop: 0x25e0ff, thief: 0xff3b6b, scent: 0x39ffa0, barrier: 0xffab2e, bg: 0x06070d,
};

export function createScene(){
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  document.body.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(COLORS.bg, 0.045);
  const camera = new THREE.PerspectiveCamera(46, innerWidth / innerHeight, 0.1, 100);
  camera.position.set(6.5, 7.5, 9.5);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.target.set(0, 0.2, 0); controls.maxPolarAngle = Math.PI * 0.49;

  scene.add(new THREE.AmbientLight(0x334466, 0.6));
  const key = new THREE.DirectionalLight(0x89b4ff, 0.5);
  key.position.set(5, 10, 4); scene.add(key);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(new UnrealBloomPass(
    new THREE.Vector2(innerWidth, innerHeight), 0.55, 0.7, 0.42));

  let high = true;
  function resize(){
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
  }
  addEventListener('resize', resize);
  function toggleQuality(){          // Low = no bloom + DPR 1
    high = !high;
    renderer.setPixelRatio(high ? Math.min(devicePixelRatio, 2) : 1);
    resize();
    return high;
  }
  function render(){ high ? composer.render() : renderer.render(scene, camera); }
  return { renderer, scene, camera, controls, render, toggleQuality, isHigh: () => high };
}
