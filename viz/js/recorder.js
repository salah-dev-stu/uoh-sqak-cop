// recorder.js — optional WebM capture of the guided tour (idea #17). Browser-only
// (MediaRecorder + canvas.captureStream); degrades to a no-op where unsupported,
// so it never blocks the arena. The saved clip becomes the README hero media.
export function createRecorder(canvas){
  let rec = null, chunks = [];
  const supported = typeof MediaRecorder !== 'undefined' && !!canvas?.captureStream;

  function start(){
    if (!supported || rec) return;
    chunks = [];
    rec = new MediaRecorder(canvas.captureStream(30), { mimeType: 'video/webm' });
    rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    rec.start();
  }

  function save(){
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(chunks, { type: 'video/webm' }));
    a.download = 'tour.webm'; a.click();
    URL.revokeObjectURL(a.href);
  }

  function stop(keep){
    if (!rec) return;
    rec.onstop = () => { if (keep && chunks.length) save(); rec = null; };
    if (rec.state !== 'inactive') rec.stop();
  }

  function toggle(){ rec ? stop(true) : start(); }
  return { start, stop, toggle, supported };
}
