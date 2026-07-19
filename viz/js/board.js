// board.js — instanced tiles + grid; belief-floor coloring (source picked by views.js)
import * as THREE from 'three';

export function cellPos(r, c, N, y = 0){
  return new THREE.Vector3(c - (N - 1) / 2, y, r - (N - 1) / 2);
}

// Calm ramp: deep indigo -> ember -> warm white (same palette as the v1 arena).
export function ramp(t){
  t = Math.max(0, Math.min(1, t));
  const a = [0x24, 0x22, 0x54], b = [0xff, 0x7a, 0x1a], w = [0xff, 0xcf, 0x8a];
  let p, q, f;
  if (t < 0.5){ p = a; q = b; f = t / 0.5; } else { p = b; q = w; f = (t - 0.5) / 0.5; }
  return new THREE.Color((p[0] + (q[0] - p[0]) * f) / 255,
    (p[1] + (q[1] - p[1]) * f) / 255, (p[2] + (q[2] - p[2]) * f) / 255);
}

export function createBoard(scene){
  let N = 7, mesh = null, grid = null;
  const geo = new THREE.PlaneGeometry(0.92, 0.92); geo.rotateX(-Math.PI / 2);
  const base = new THREE.Color(0x0b101e), tmp = new THREE.Color();
  const m4 = new THREE.Matrix4();

  function rebuild(n){
    N = n;
    if (mesh){ scene.remove(mesh); mesh.dispose(); }
    if (grid) scene.remove(grid);
    mesh = new THREE.InstancedMesh(geo, new THREE.MeshBasicMaterial(), N * N);
    for (let r = 0; r < N; r++) for (let c = 0; c < N; c++){
      m4.setPosition(cellPos(r, c, N, 0.001));
      mesh.setMatrixAt(r * N + c, m4);
      mesh.setColorAt(r * N + c, base);
    }
    grid = new THREE.GridHelper(N, N, 0x2a3f66, 0x18263f);
    grid.position.y = 0.012;
    scene.add(mesh, grid);
  }

  function setBelief(vals){            // 2-D float grid, or null for a dark floor
    const peak = vals ? Math.max(...vals.flat(), 1e-6) : 1;
    for (let r = 0; r < N; r++) for (let c = 0; c < N; c++){
      const v = vals ? vals[r][c] / peak : 0;
      tmp.copy(base);
      if (v >= 0.14) tmp.add(ramp(v).multiplyScalar(0.16 + v * 0.6));
      mesh.setColorAt(r * N + c, tmp);
    }
    mesh.instanceColor.needsUpdate = true;
  }

  rebuild(7);
  return { rebuild, setBelief, size: () => N };
}
