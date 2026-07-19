// split.js — key `4` (replay only): the cop's belief world (left) beside the
// thief's (right), one scene double-rendered into two scissor viewports with the
// shared camera. Bloom is skipped in split (the composer ignores scissor); the
// side-by-side analytical read is the point, not the glow. `1/2/3` exits.
export function halfRects(w, h){
  const lw = Math.ceil(w / 2);
  return [{ x: 0, y: 0, w: lw, h }, { x: lw, y: 0, w: w - lw, h }];
}

export function createSplit({ renderer, scene, camera, views, board, agents, scent }){
  let on = false;
  const setOn = v => { on = v; document.body.classList.toggle('split', on); };
  addEventListener('keydown', e => {
    if (e.key === '4') setOn(!on);
    else if (e.key === '1' || e.key === '2' || e.key === '3') setOn(false);
  });

  function apply(frame, view, N){
    views.set(view);
    views.apply(frame, { board, agents, scent, N });
  }

  function paint(frame, N){
    if (!on || !frame) return false;
    const [left, right] = halfRects(innerWidth, innerHeight);
    const prev = views.view;
    renderer.setScissorTest(true);
    for (const [rect, view] of [[left, 1], [right, 2]]){
      apply(frame, view, N);
      camera.aspect = rect.w / rect.h; camera.updateProjectionMatrix();
      renderer.setViewport(rect.x, rect.y, rect.w, rect.h);
      renderer.setScissor(rect.x, rect.y, rect.w, rect.h);
      renderer.render(scene, camera);
    }
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, innerWidth, innerHeight);
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    apply(frame, prev, N);          // leave the scene in the real view for toggle-off
    return true;
  }

  return { paint, active: () => on };
}
