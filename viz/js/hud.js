// hud.js — chips, hint ticker with intent badge, sparkline, scrub markers,
// and transport-bar event binding.
import { markers } from './timeline.js';

const $ = id => document.getElementById(id);

export function createHud(){
  const canvas = $('spark'), ctx = canvas.getContext('2d');

  function setMarkers(events, nFrames){
    const box = $('marks'); box.innerHTML = '';
    for (const m of markers(events, nFrames)){
      const d = document.createElement('span');
      d.className = 'mk ' + m.type;
      d.style.left = (m.frac * 100).toFixed(2) + '%';
      d.title = m.type + ' · turn ' + m.turn;
      box.appendChild(d);
    }
  }

  function update({ gap, barriers, score, turn, nTurns }){
    $('gap').textContent = gap;
    $('nbar').textContent = barriers;
    $('score').textContent = score.cop + ' : ' + score.thief;
    $('turn').textContent = `turn ${turn}/${nTurns}`;
  }

  function setHint(hint, intent, showBadge){
    $('hint-text').textContent = hint || '···';
    const b = $('badge');
    b.hidden = !(showBadge && hint);          // intent badge only in Truth view
    b.textContent = intent;
    b.className = intent;
  }

  function line(series, upTo, color, w, h, max){
    ctx.strokeStyle = color; ctx.beginPath();
    for (let i = 0; i <= upTo; i++){
      const x = series.length > 1 ? i / (series.length - 1) * w : 0;
      const y = h - 4 - (series[i] / max) * (h - 8);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
  }

  function drawSpark(dist, err, upTo){        // cyan = gap, magenta = belief error
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const max = Math.max(...dist, ...err, 1);
    ctx.globalAlpha = 0.22; ctx.lineWidth = 1;
    line(dist, dist.length - 1, '#25e0ff', w, h, max);
    line(err, err.length - 1, '#ff3b6b', w, h, max);
    ctx.globalAlpha = 1; ctx.lineWidth = 1.5;
    line(dist, upTo, '#25e0ff', w, h, max);
    line(err, upTo, '#ff3b6b', w, h, max);
  }

  return { setMarkers, update, setHint, drawSpark };
}

export function bindTransport(cb){
  $('play').addEventListener('click', () => cb.onPlay());
  const scrub = $('scrub');
  scrub.addEventListener('input', () => cb.onScrub(parseFloat(scrub.value)));
  scrub.addEventListener('change', () => cb.onScrubEnd());
  const seg = (sel, fn) => document.querySelectorAll(sel).forEach(b =>
    b.addEventListener('click', () => {
      document.querySelectorAll(sel).forEach(x => x.classList.remove('on'));
      b.classList.add('on'); fn(b);
    }));
  seg('#speeds button', b => cb.onSpeed(parseFloat(b.dataset.s)));
  seg('#viewseg button', b => cb.onView(parseInt(b.dataset.v, 10)));
  $('new').addEventListener('click', () => cb.onNew());
  $('fixture').addEventListener('click', () => {
    const el = $('fixture'), tampered = el.textContent === 'Honest';
    el.textContent = tampered ? 'Tampered' : 'Honest';
    el.setAttribute('aria-pressed', String(tampered));
    el.classList.toggle('warn', tampered);
    cb.onFixture(!tampered);
  });
  $('quality').addEventListener('click', () => {
    $('quality').textContent = cb.onQuality() ? 'HQ' : 'LQ';
  });
}

export function pressView(v){
  document.querySelector(`#viewseg button[data-v="${v}"]`)?.click();
}
