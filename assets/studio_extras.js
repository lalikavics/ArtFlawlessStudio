/* ---------- model / LoRA family check and time estimate ----------
   - the backend reads only the safetensors header of a model or LoRA file (/artflow/model-kind) and tells its family
     (sd15 / sdxl / flux / zimage). The CUSTOM tab can only run SD 1.5 / SDXL / Pony style checkpoints (model, text encoder
     and VAE in one file); a Z-Image or Flux file there stops with a clear message instead of a ComfyUI error.
     A LoRA made for another family has no effect (ComfyUI only logs "lora key not loaded"), so the Studio asks first.
   - the status bar shows the elapsed time and an estimate from earlier runs with the same model, size and steps */
const MK = new Map();
async function modelKind(folder, name) {
  if (!name) return {kind: 'missing'}; const key = folder + '|' + name;
  if (!MK.has(key)) MK.set(key, fetch(API + '/artflow/model-kind?folder=' + encodeURIComponent(folder) + '&name=' + encodeURIComponent(name)).then(r => r.json()).catch(() => ({kind: 'unknown'})));
  return MK.get(key);
}
const KIND_NAME = {sd15: 'SD 1.5', sdxl: 'SDXL / Pony', flux: 'Flux', zimage: 'Z-Image', unknown: '?', missing: '?'};
const FAM_KIND = {zimage: 'zimage', sdxl: 'sdxl', flux: 'flux'};
const xs = (k, ...a) => {
  const hu = LANG === 'hu';
  const M = {
    ckT: hu ? 'Ez a modell nem a CUSTOM fülre való' : 'This model does not belong on the CUSTOM tab',
    ckZ: hu ? '„%1” egy Z-Image modell. Csak a képalkotó rész van benne, szövegkódoló és VAE nélkül, és más mintavételezés kell neki, ezért a CUSTOM fülön nem fut le (ComfyUI ilyenkor hibával áll le, a beállítások átírása ezen nem segít).'
            : '"%1" is a Z-Image model. It has only the image model, without text encoder and VAE, and needs a different sampler, so it cannot run on the CUSTOM tab (ComfyUI stops with an error, changing the settings does not help).',
    ckZ2: hu ? 'A Z-Image fülön saját modellként működik: tedd a fájlt a models\\diffusion_models mappába, és a Z-Image fül modellválasztójában megjelenik.'
             : 'It works as your own model on the Z-Image tab: put the file into the models\\diffusion_models folder and it appears in the model list of the Z-Image tab.',
    ckF: hu ? '„%1” egy Flux modell. A CUSTOM fül SD 1.5, SDXL és Pony checkpointokhoz való; Flux modellt a Flux fülön használj.'
            : '"%1" is a Flux model. The CUSTOM tab is for SD 1.5, SDXL and Pony checkpoints; use Flux models on the Flux tab.',
    ckN: hu ? '„%1”-ben nincs szövegkódoló vagy VAE, a CUSTOM fül pedig egyben várja a teljes checkpointot (modell + szövegkódoló + VAE).'
            : '"%1" has no text encoder or VAE, and the CUSTOM tab needs a complete checkpoint (model + text encoder + VAE) in one file.',
    ok: hu ? 'Rendben' : 'OK',
    loT: hu ? 'Ez a LoRA másik modellcsaládhoz készült' : 'This LoRA is made for another model family',
    loB: hu ? 'A kiválasztott modell: %1. Ezek a LoRA-k nem hozzá valók, ezért nem lesz hatásuk a képre:' : 'The selected model is %1. These LoRAs do not belong to it, so they will have no effect on the image:',
    loR: hu ? 'Kikapcsolom őket és indítom' : 'Switch them off and start',
    loK: hu ? 'Így indítom' : 'Start anyway', cancel: hu ? 'Mégse' : 'Cancel',
    el: hu ? 'Eltelt: %1' : 'Elapsed: %1', est: hu ? 'várható: ~%1' : 'expected: ~%1', estN: hu ? '%1 korábbi futás alapján' : 'from %1 earlier runs',
  };
  let s = M[k] || k; a.forEach((v, i) => { s = s.split('%' + (i + 1)).join(v); }); return s;
};
function xModal(title, kids, buttons) {
  return new Promise(res => {
    MODAL_KIND = 'xcheck'; let done = false;
    const fin = v => { if (done) return; done = true; obs.disconnect(); $('#modal').classList.remove('open'); res(v); };
    $('#modalTitle').textContent = title;
    $('#modalBody').replaceChildren(...kids, h('div', {class: 'row', style: 'justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:6px'},
      ...buttons.map(([txt, v, go]) => h('button', {class: 'btn sm' + (go ? ' go2' : ''), type: 'button', text: txt, onclick: () => fin(v)}))));
    $('#modal').classList.add('open');
    const obs = new MutationObserver(() => { if (!$('#modal').classList.contains('open')) fin('cancel'); }); obs.observe($('#modal'), {attributes: true, attributeFilter: ['class']});
  });
}
async function checkModels() {
  // safety net before a run: a switched-on LoRA of another model family has no effect (the LoRA rows already mark it)
  if (!T || typeof curModelRef !== 'function') return true;
  const m = curModelRef(); if (!m.name) return true; const mk = await modelKind(m.folder, m.name);
  if (!mk || mk.kind === 'unknown' || mk.kind === 'missing') return true;
  const bad = [];
  for (const L of (S.loras || [])) {
    if (!L.on || !L.lora) continue; const lk = await modelKind('loras', L.lora);
    if (lk.kind !== 'unknown' && lk.kind !== 'missing' && lk.kind !== mk.kind) bad.push([L, lk.kind]);
  }
  if (!bad.length) return true;
  const a = await xModal(xs('loT'), [h('p', {text: xs('loB', KIND_NAME[mk.kind] || mk.kind)}),
    h('ul', {}, ...bad.map(([L, k]) => h('li', {text: pretty(L.lora) + ' – ' + (KIND_NAME[k] || k)})))],
    [[xs('cancel'), 'cancel'], [xs('loK'), 'keep'], [xs('loR'), 'off', true]]);
  if (a === 'cancel') return false;
  if (a === 'off') { bad.forEach(([L]) => { L.on = false; }); save(); renderControls(); }
  return true;
}
const _runX = run;
run = async function () { if (!(await checkModels())) return; const before = new Set(R.jobs.keys()); const r = await _runX(); for (const id of R.jobs.keys()) if (!before.has(id)) JOB_SIG.set(id, runSig()); return r; };

/* time estimate: durations of finished runs, per model + size + steps + switched-on steps (groups) */
const LS_TIMES = 'artflow.studio.times.v1';
let TIMES = {}; try { TIMES = JSON.parse(localStorage.getItem(LS_TIMES) || '{}') || {}; } catch (_) { TIMES = {}; }
const JOB_SIG = new Map();
function runSig() {
  try {
    const g = Object.keys(T.groups).filter(k => S.groups[k]).sort().join(',');
    return [T.family, val('2', modelField()) || '', val('87', 'choice') || '', T.prompt['127'] ? val('127', 'value') : '', T.prompt['123'] ? val('123', 'value') : '', g].join('|');
  } catch (_) { return ''; }
}
function estimate(sig) {
  const a = TIMES[sig]; if (!a || !a.length) return null;
  const s = a.slice().sort((x, y) => x - y); return {sec: s[Math.floor(s.length / 2)], n: a.length};
}
const fmtT = s => { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
const _finishX = finish;
finish = async function (id, ok) {
  const sig = JOB_SIG.get(id); const started = R.job === id ? R.t0 : null;
  await _finishX(id, ok);
  if (ok && sig && started) {
    const sec = (Date.now() - started) / 1000; const a = TIMES[sig] = (TIMES[sig] || []).concat([Math.round(sec * 10) / 10]).slice(-8);
    const keys = Object.keys(TIMES); if (keys.length > 200) keys.slice(0, keys.length - 200).forEach(k => delete TIMES[k]);
    try { localStorage.setItem(LS_TIMES, JSON.stringify(TIMES)); } catch (_) {}
  }
  JOB_SIG.delete(id); etaTick();
};
function etaTick() {
  const el = $('#eta'); if (!el) return;
  if (!R.job || !R.t0) { el.textContent = ''; el.hidden = true; return; }
  const el2 = (Date.now() - R.t0) / 1000; const e = estimate(JOB_SIG.get(R.job) || '');
  el.hidden = false;
  el.textContent = xs('el', fmtT(el2)) + (e ? ' · ' + xs('est', fmtT(Math.max(e.sec, el2))) : '');
  el.title = e ? xs('estN', e.n) : '';
}
function initExtras() {
  const st = $('#seedInfo'); if (st && !$('#eta')) st.before(h('span', {id: 'eta', class: 'muted', hidden: true}));
  setInterval(etaTick, 1000); initLoad();
}

/* header: live GPU and CPU load (polled every 1.5 s from /artflow/sysload) */
function loadMeter(id, label) {
  return h('div', {class: 'lm', id}, h('span', {class: 'lml', text: label}), h('span', {class: 'lmb'}, h('i')), h('span', {class: 'lmv', text: '–'}));
}
function setMeter(id, v, tip) {
  const m = $('#' + id); if (!m) return; const ok = v != null && isFinite(v);
  m.querySelector('i').style.width = (ok ? Math.max(0, Math.min(100, v)) : 0) + '%';
  m.querySelector('i').className = ok && v >= 90 ? 'hi' : ok && v >= 60 ? 'mid' : '';
  m.querySelector('.lmv').textContent = ok ? Math.round(v) + '%' : '–'; m.title = tip || '';
}
async function pollLoad() {
  try {
    const j = await (await fetch(API + '/artflow/sysload')).json(); const hu = LANG === 'hu';
    setMeter('lmGpu', j.gpu, j.vram_total ? (hu ? 'Videókártya: ' : 'GPU: ') + j.gpu + '% · VRAM ' + (j.vram_used / 1024).toFixed(1) + ' / ' + (j.vram_total / 1024).toFixed(1) + ' GB' : '');
    setMeter('lmCpu', j.cpu, j.ram != null ? (hu ? 'Processzor: ' : 'CPU: ') + j.cpu + '% · RAM ' + j.ram + '%' : '');
  } catch (_) { setMeter('lmGpu', null); setMeter('lmCpu', null); }
}
function initLoad() {
  const cw = document.querySelector('.conn .cw'); if (!cw || $('#lmGpu')) return;
  cw.append(h('div', {class: 'lms'}, loadMeter('lmGpu', 'GPU'), loadMeter('lmCpu', 'CPU')));
  pollLoad(); setInterval(() => { if (!document.hidden) pollLoad(); }, 1500);
}
