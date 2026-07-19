// capture.js — S key: render, then grab the WebGL canvas as a PNG download.
// Rendering immediately before toDataURL avoids needing preserveDrawingBuffer
// (the drawing buffer is still intact within the same task).
export function initCapture(sc){
  return function shoot(){
    sc.render();
    const a = document.createElement('a');
    a.download = 'cipherchase-' + new Date().toISOString().replace(/[:.]/g, '-') + '.png';
    a.href = sc.renderer.domElement.toDataURL('image/png');
    a.click();
  };
}
