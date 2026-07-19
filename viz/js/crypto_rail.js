// crypto_rail.js — the sealed-evidence rail. Glyph chips (#xxxxxxxx) appear as
// their turn passes; at game end an audit wave sweeps them green (~40 ms stagger)
// or flips the forged chip red and shatters everything after it. Click = inspector.
export function createRail(railEl, bannerEl, popEl){
  let model = null, chips = [], timer = null;

  function chipEl(c){
    const d = document.createElement('button');
    d.type = 'button';
    d.className = 'glyph ' + c.side;
    d.textContent = c.short;
    d.setAttribute('aria-label', `${c.side} step ${c.step} commit ${c.short}`);
    d.addEventListener('click', e => { e.stopPropagation(); inspect(c, d); });
    return d;
  }

  function setGame(m){
    stop(); model = m; chips = []; railEl.innerHTML = '';
    for (const c of m.chips){
      const d = chipEl(c);
      railEl.appendChild(d); chips.push(d);
    }
    rearm();
  }

  function reveal(turn){
    if (!model) return;
    model.chips.forEach((c, i) => chips[i].classList.toggle('shown', c.step <= turn));
  }

  function startAudit(){
    if (!model) return;
    stop();
    let k = 0;
    timer = setInterval(() => {
      if (k >= chips.length){
        stop();
        if (model.firstBad < 0) banner('Verified OK', 'ok');
        return;
      }
      if (model.firstBad === k){
        chips[k].classList.add('bad');
        banner('TAMPERED — match void 0/0', 'bad');
      } else if (model.firstBad >= 0 && k > model.firstBad){
        chips[k].classList.add('shatter');
      } else chips[k].classList.add('ok');
      chips[k].scrollIntoView({ block: 'nearest' });
      k++;
    }, 40);
  }

  function banner(text, cls){ bannerEl.textContent = text; bannerEl.className = cls + ' show'; }
  function stop(){ if (timer){ clearInterval(timer); timer = null; } }

  function rearm(){                       // clear audit state, keep chips
    stop();
    bannerEl.textContent = ''; bannerEl.className = '';
    chips.forEach(d => d.classList.remove('ok', 'bad', 'shatter'));
    popEl.hidden = true;
  }

  function reset(){ rearm(); reveal(0); }

  function inspect(c, d){
    popEl.innerHTML = '';
    const h = document.createElement('div');
    h.className = 'pop-h ' + (c.status === 'Verified OK' ? 'ok' : 'bad');
    h.textContent = `${c.side} · step ${c.step} · ${c.status}`;
    const pre = document.createElement('pre');
    pre.textContent = 'payload ' + JSON.stringify(c.payload, null, 1) +
      '\nnonce  ' + c.nonce + '\ncommit ' + c.commit;
    popEl.append(h, pre);
    const r = d.getBoundingClientRect();
    popEl.style.top = Math.max(12, Math.min(innerHeight - 250, r.top - 20)) + 'px';
    popEl.hidden = false;
  }

  document.addEventListener('click', () => { popEl.hidden = true; });
  popEl.addEventListener('click', e => e.stopPropagation());

  return { setGame, reveal, startAudit, rearm, reset };
}
