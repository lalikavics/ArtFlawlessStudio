/* ---------- CUSTOM tab: universal model loader ----------
   The Studio reads the header of the chosen file (/artflow/model-kind) and builds the run for its model type:
   SD 1.5, SDXL (Pony, Illustrious), Z-Image, Flux schnell / dev; checkpoints, diffusion-only models and GGUF files.
   Missing parts (text encoder, VAE) come from separate loaders; Flux text encoders can be downloaded (asks first).
   The settings panel follows the model type; the values are remembered per model file.
   LoRA rows on every tab show whether the LoRA fits the loaded model, how much of it matches, its trigger words and
   a separate text-encoder strength. */
const CU_LS = 'artflow.studio.custom.v1';
let CU_SAVED = {}; try { CU_SAVED = JSON.parse(localStorage.getItem(CU_LS) || '{}') || {}; } catch (_) { CU_SAVED = {}; }
let CU = {info: null, key: '', load: null};
let SYS = null;     // last /artflow/sysload answer (VRAM / RAM totals)
const cus = (k, ...a) => {
  const hu = LANG === 'hu';
  const M = {
    pick: hu ? 'Modellfájl' : 'Model file', gCk: hu ? 'Checkpointok (models\\checkpoints)' : 'Checkpoints (models\\checkpoints)',
    gDm: hu ? 'Csak képalkotó modellek (models\\diffusion_models)' : 'Diffusion models (models\\diffusion_models)', gGg: 'GGUF (models\\unet)',
    none: hu ? '– válassz modellt –' : '– choose a model –', reading: hu ? 'A modell típusának felismerése…' : 'Reading the model type…',
    full: hu ? 'teljes checkpoint (modell + szövegkódoló + VAE)' : 'complete checkpoint (model + text encoder + VAE)',
    only: hu ? 'csak képalkotó rész – a szövegkódoló és a VAE külön töltődik' : 'image model only – text encoder and VAE are loaded separately',
    unsup: hu ? 'Ezt a modelltípust (%1) a Studio még nem tudja futtatni.' : 'The Studio cannot run this model type (%1) yet.',
    unk: hu ? 'A modell típusa nem ismerhető fel. SD 1.5 / SDXL checkpointként próbálom futtatni.' : 'The model type could not be recognised. It is run as an SD 1.5 / SDXL checkpoint.',
    vOk: hu ? 'Gépigény: elfér a videókártyán (%1 / %2 GB)' : 'Hardware: fits the graphics card (%1 / %2 GB)',
    vSlow: hu ? 'Gépigény: nem fér el egészben a videókártyán (%1 GB, a kártyán %2 GB) – részben a memóriából fut, lassabb lesz' : 'Hardware: does not fit the graphics card completely (%1 GB, card %2 GB) – part of it runs from RAM, slower',
    vBad: hu ? 'Gépigény: jóval nagyobb, mint a videókártya (%1 GB, a kártyán %2 GB) – nagyon lassú lehet vagy el sem indul. Kisebb változat (fp8 vagy GGUF Q4–Q5) ajánlott.' : 'Hardware: much larger than the graphics card (%1 GB, card %2 GB) – it can be very slow or fail. A smaller version (fp8 or GGUF Q4–Q5) is recommended.',
    vRam: hu ? 'Gépigény: a modell és a szövegkódoló együtt (%1 GB) nem fér el a memóriában (%2 GB) – nem fog működni.' : 'Hardware: model and text encoder together (%1 GB) do not fit into RAM (%2 GB) – it will not work.',
    set: hu ? 'Beállítások ehhez a modellhez' : 'Settings for this model', saved: hu ? 'A beállítások ehhez a modellfájlhoz megjegyezve.' : 'Settings are remembered for this model file.',
    reset: hu ? 'Alapértékek' : 'Defaults', sampler: 'Sampler', scheduler: 'Scheduler', steps: hu ? 'Lépésszám' : 'Steps', cfg: 'CFG',
    guid: hu ? 'Flux guidance' : 'Flux guidance', shift: hu ? 'Shift (mintavételi eltolás)' : 'Shift', clip: 'CLIP skip', base: hu ? 'Alapméret (px)' : 'Base size (px)',
    dtype: hu ? 'Súlyok pontossága' : 'Weight precision', te: hu ? 'Szövegkódoló' : 'Text encoder', te2: hu ? 'Szövegkódoló 2 (T5)' : 'Text encoder 2 (T5)',
    vae: 'VAE', vaeCk: hu ? '(a checkpointban lévő)' : '(the one in the checkpoint)', pfx: hu ? 'Prompt eleje (pl. Pony score tagek)' : 'Prompt prefix (e.g. Pony score tags)',
    npfx: hu ? 'Negatív prompt eleje' : 'Negative prefix',
    hCfg1: hu ? 'Ez a modell CFG 1-gyel fut: a negatív prompt itt alig hat.' : 'This model runs at CFG 1: the negative prompt has little effect.',
    teMiss: hu ? 'Hiányzik a szövegkódoló ehhez a modellhez' : 'The text encoder for this model is missing',
    teMissB: hu ? 'A(z) %1 modellhez ezek a fájlok kellenek, de nincsenek meg: %2. Letöltsem őket most (%3)?' : 'The %1 model needs these files, which are not on this computer: %2. Download them now (%3)?',
    dl: hu ? 'Letöltés' : 'Download', cancel: hu ? 'Mégse' : 'Cancel', ok: hu ? 'Rendben' : 'OK', anyway: hu ? 'Mégis indítom' : 'Start anyway',
    hwT: hu ? 'Ez a modell túl nagy ehhez a géphez' : 'This model is too large for this computer',
    unsT: hu ? 'Nem támogatott modelltípus' : 'Unsupported model type',
    lOk: hu ? '✓ illik a betöltött modellhez' : '✓ fits the loaded model', lPart: hu ? '◐ részben illik' : '◐ partly fits',
    lBad: hu ? '✕ Nem működik együtt a betöltött checkpointtal' : '✕ Does not work with the loaded checkpoint',
    lMatch: hu ? 'illeszkedés %1%' : 'match %1%', lConv: hu ? 'más elnevezésű, a ComfyUI betöltéskor átalakítja' : 'other naming, converted by ComfyUI',
    lKind: hu ? 'LoRA: %1 · modell: %2' : 'LoRA: %1 · model: %2', lTe: hu ? 'Szövegkódoló erőssége' : 'Text encoder strength',
    trig: hu ? 'Trigger szavak:' : 'Trigger words:', trigAll: hu ? 'Mind a promptba' : 'All into the prompt', trigAdd: hu ? 'Kattints: a promptba kerül' : 'Click: add to the prompt',
    trigDone: hu ? 'A trigger szó bekerült a promptba.' : 'The trigger word was added to the prompt.',
    tags: hu ? 'Gyakori tanítási címkék (nem kötelezők)' : 'Frequent training tags (optional)',
    nlCk: hu ? '✕ Ez nem LoRA, hanem egy teljes checkpoint – a models\\checkpoints mappába való.' : '✕ This is not a LoRA but a complete checkpoint – it belongs in the models\\checkpoints folder.',
    nlEm: hu ? '✕ Ez nem LoRA, hanem embedding (textual inversion) – a models\\embeddings mappába tedd, és a promptban így használd: embedding:%1' : '✕ This is not a LoRA but an embedding (textual inversion) – put it into models\\embeddings and use it in the prompt as embedding:%1',
    iiApply: hu ? 'Beállítások átvétele (CUSTOM)' : 'Use the settings (CUSTOM)', iiApplied: hu ? 'A kép beállításai átvéve: %1' : 'Settings taken from the image: %1',
  };
  let s = M[k] || k; a.forEach((v, i) => { s = s.split('%' + (i + 1)).join(v); }); return s;
};
const KN = {sd15: 'SD 1.5', sdxl: 'SDXL', pony: 'SDXL – Pony', illustrious: 'SDXL – Illustrious', zimage: 'Z-Image', flux: 'Flux', 'flux-dev': 'Flux dev', 'flux-schnell': 'Flux schnell',
  sd3: 'SD 3 / 3.5', chroma: 'Chroma', qwen_image: 'Qwen-Image', unknown: '?', missing: '?'};
const kindLabel = i => !i ? '?' : (i.kind === 'flux' && i.sub ? KN['flux-' + i.sub] : i.kind === 'sdxl' && i.sub ? KN[i.sub] : KN[i.kind] || i.kind);
/* model type profiles: how to build the run, defaults and the fields of the settings panel */
const CU_PROF = {
  sd15: {base: 512, sampler: 'dpmpp_2m', scheduler: 'karras', steps: 25, cfg: 7, clip: -1, sd: true},
  sdxl: {base: 1024, sampler: 'dpmpp_2m', scheduler: 'karras', steps: 25, cfg: 6, clip: -1, sd: true},
  pony: {base: 1024, sampler: 'euler_ancestral', scheduler: 'normal', steps: 25, cfg: 7, clip: -2, sd: true,
         prefix: 'score_9, score_8_up, score_7_up, ', nprefix: 'score_4, score_5, score_6, '},
  illustrious: {base: 1024, sampler: 'euler_ancestral', scheduler: 'normal', steps: 28, cfg: 5.5, clip: -2, sd: true},
  zimage: {base: 1024, sampler: 'res_multistep', scheduler: 'simple', steps: 8, cfg: 1, shift: 3, latent: 'EmptySD3LatentImage', shiftNode: 'ModelSamplingAuraFlow',
           te: [['CLIPLoader', 'qwen_3_4b.safetensors', 'lumina2']], vae: 'ae.safetensors', cfg1: true},
  'flux-schnell': {base: 1024, sampler: 'euler', scheduler: 'simple', steps: 4, cfg: 1, latent: 'EmptySD3LatentImage',
                   te: [['DualCLIPLoader', 'clip_l.safetensors', 't5xxl_fp8_e4m3fn.safetensors', 'flux']], vae: 'ae.safetensors', cfg1: true},
  'flux-dev': {base: 1024, sampler: 'euler', scheduler: 'simple', steps: 20, cfg: 1, guidance: 3.5, latent: 'EmptySD3LatentImage',
               te: [['DualCLIPLoader', 'clip_l.safetensors', 't5xxl_fp8_e4m3fn.safetensors', 'flux']], vae: 'ae.safetensors', cfg1: true},
};
function cuProfKey(i) {
  if (!i) return null; if (i.kind === 'flux') return 'flux-' + (i.sub || 'schnell');
  if (i.kind === 'sdxl') return i.sub || 'sdxl'; if (i.kind === 'sd15' || i.kind === 'zimage') return i.kind;
  if (i.kind === 'unknown') return 'sdxl'; return null;
}
const oiOpts = (cls, inp) => { const o = OI[cls]; const s = o && o.input && ((o.input.required && o.input.required[inp]) || (o.input.optional && o.input.optional[inp])); return s ? (Array.isArray(s[0]) ? s[0] : (s[1] && s[1].options) || []) : []; };
function cuLists() { return {ckpt: oiOpts('CheckpointLoaderSimple', 'ckpt_name'), unet: oiOpts('UNETLoader', 'unet_name'), gguf: oiOpts('UnetLoaderGGUF', 'unet_name')}; }
const CU_FOLDER = {ckpt: 'checkpoints', unet: 'diffusion_models', gguf: 'unet_gguf'};
function cuCur() {
  const c = S.cm || {}; const src = c.src || 'ckpt'; return {src, name: src === 'ckpt' ? (val('2', 'ckpt_name') || '') : (c.name || ''), folder: CU_FOLDER[src]};
}
async function cuInfo(force) {
  const c = cuCur(); const key = c.folder + '|' + c.name;
  if (!c.name) { CU = {info: null, key: '', load: null}; return null; }
  if (CU.key === key && CU.info && !force) return CU.info;
  if (CU.key !== key || !CU.load) { CU.key = key; CU.info = null; CU.load = modelKind(c.folder, c.name).then(i => { if (CU.key === key) CU.info = i; return i; }); }
  return CU.load;
}
function cuSet(name) { const st = CU_SAVED[name] || {}; return st; }
function cuStore() {
  const c = cuCur(); if (!c.name) return;
  CU_SAVED[c.name] = {sampler: val('6', 'sampler_name'), scheduler: val('6', 'scheduler'), steps: Number(val('123', 'value')) || 0, cfg: Number(val('124', 'value')) || 0,
    clip: T.prompt['120'] ? Number(val('120', 'stop_at_clip_layer')) : -1, base: Number(val('127', 'value')) || 1024,
    prefix: val('121', 'string_a') || '', nprefix: val('122', 'string_a') || '', shift: S.cm && S.cm.shift, guidance: S.cm && S.cm.guidance,
    dtype: S.cm && S.cm.dtype, te1: S.cm && S.cm.te1, te2: S.cm && S.cm.te2, vae: S.cm && S.cm.vae};
  const keys = Object.keys(CU_SAVED); if (keys.length > 150) keys.slice(0, keys.length - 150).forEach(k => delete CU_SAVED[k]);
  try { localStorage.setItem(CU_LS, JSON.stringify(CU_SAVED)); } catch (_) {}
}
function cuApply(prof, saved) {
  const v = Object.assign({}, prof, saved || {});
  for (const id of ['6', '17', '25', '30', '62', '33']) if (T.prompt[id]) { setVal(id, 'sampler_name', v.sampler); setVal(id, 'scheduler', v.scheduler); }
  setVal('123', 'value', v.steps || 0); setVal('124', 'value', v.cfg || 0);
  if (T.prompt['120']) setVal('120', 'stop_at_clip_layer', prof.sd ? (v.clip || -1) : -1);
  if (T.prompt['127']) setVal('127', 'value', v.base || prof.base || 1024);
  if (T.prompt['121']) setVal('121', 'string_a', v.prefix || ''); if (T.prompt['122']) setVal('122', 'string_a', v.nprefix || '');
  const sv = saved || {};   // text encoder and VAE choices only from the saved settings: the profile defaults are used when the file has none of its own
  S.cm = Object.assign(S.cm || {}, {shift: v.shift, guidance: v.guidance, dtype: v.dtype || 'default', te1: sv.te1 || '', te2: sv.te2 || '', vae: sv.vae || ''});
  if (T.groups.v) S.groups.v = false;   // the VAE choice is in the settings panel
  S.cm.applied = cuCur().name; save();
}
async function cuChoose(src, name) {
  S.cm = Object.assign(S.cm || {}, {src, name, applied: ''});
  setVal('2', 'ckpt_name', name); save();
  const i = await cuInfo(true); const pk = cuProfKey(i);
  if (pk && CU_PROF[pk]) cuApply(CU_PROF[pk], CU_SAVED[name]);
  renderControls();
}
/* hardware check from the file size, the graphics card and the RAM */
function cuHw(info, prof) {
  if (!info || !info.size || !SYS || !SYS.vram_total) return null;
  const gb = x => (x / 1024 ** 3).toFixed(1); const vram = SYS.vram_total * 2 ** 20; const ram = (SYS.ram_total || 0) * 2 ** 20;
  const teSize = cuCur().src !== 'ckpt' || info.clip === false ? (prof && prof.te && prof.te[0][0] === 'DualCLIPLoader' ? 5.1e9 : prof && prof.te ? 8.0e9 : 0) : 0;
  if (ram && info.size + teSize > ram * 0.85) return {lvl: 'bad', text: cus('vRam', gb(info.size + teSize), gb(ram))};
  const r = info.size / vram;
  if (r <= 0.85) return {lvl: 'ok', text: cus('vOk', gb(info.size), gb(vram))};
  if (r <= 2.2) return {lvl: 'mid', text: cus('vSlow', gb(info.size), gb(vram))};
  return {lvl: 'bad', text: cus('vBad', gb(info.size), gb(vram))};
}
async function cuSys() { if (SYS) return SYS; try { SYS = await (await fetch(API + '/artflow/sysload')).json(); } catch (_) { SYS = null; } return SYS; }
/* the model card of the CUSTOM tab */
function cuSelect() {
  const L = cuLists(); const c = cuCur(); const s = h('select', {id: 'cuSel'});
  s.append(h('option', {value: '', text: cus('none')}));
  const grp = (label, src, arr) => { if (!arr.length) return; const g = h('optgroup', {label}); arr.forEach(n => g.append(h('option', {value: src + '|' + n, text: pretty(n)}))); s.append(g); };
  grp(cus('gCk'), 'ckpt', L.ckpt); grp(cus('gDm'), 'unet', L.unet); grp(cus('gGg'), 'gguf', L.gguf);
  s.value = c.name ? c.src + '|' + c.name : '';
  s.onchange = () => { const v = s.value; if (!v) return; const i = v.indexOf('|'); cuChoose(v.slice(0, i), v.slice(i + 1)); };
  return h('div', {class: 'f', 'data-help': 'cu:model'}, h('label', {class: 'lab', text: cus('pick')}), s);
}
function cuSelBox(label, cur, opts, cb, first) {
  const s = h('select'); if (first) s.append(h('option', {value: '', text: first}));
  const list = cur && !opts.includes(cur) ? [cur, ...opts] : opts; list.forEach(x => s.append(h('option', {value: x, text: pretty(x)}))); s.value = cur || '';
  s.onchange = () => cb(s.value); return h('div', {class: 'f'}, h('label', {class: 'lab', text: label}), s);
}
function cuNum(label, v, c, cb) { return h('div', {class: 'f'}, h('label', {class: 'lab', text: label}), num(v, c, x => { cb(x); cuStore(); })); }
function cuPanel(info, prof) {
  if (!S.cm) S.cm = {}; const c = cuCur(); const box = h('div', {class: 'cuset'});
  const onSV = (id, k) => x => { setVal(id, k, x); cuStore(); };
  const samplers = oiOpts('KSampler', 'sampler_name'), scheds = oiOpts('KSampler', 'scheduler');
  const two = (...a) => h('div', {class: 'two'}, ...a);
  box.append(h('div', {class: 'row', style: 'justify-content:space-between;align-items:center'}, h('b', {text: cus('set')}),
    h('button', {class: 'btn sm', type: 'button', text: cus('reset'), onclick: () => { delete CU_SAVED[c.name]; try { localStorage.setItem(CU_LS, JSON.stringify(CU_SAVED)); } catch (_) {} cuApply(prof, null); renderControls(); }})));
  box.append(two(cuSelBox(cus('sampler'), val('6', 'sampler_name'), samplers, x => { for (const id of ['6', '17', '25', '30', '62', '33']) if (T.prompt[id]) setVal(id, 'sampler_name', x); cuStore(); }),
                 cuSelBox(cus('scheduler'), val('6', 'scheduler'), scheds, x => { for (const id of ['6', '17', '25', '30', '62', '33']) if (T.prompt[id]) setVal(id, 'scheduler', x); cuStore(); })));
  box.append(two(cuNum(cus('steps'), Number(val('123', 'value')) || prof.steps, {min: 1, max: 150, int: true}, onSV('123', 'value')),
                 cuNum(cus('cfg'), Number(val('124', 'value')) || prof.cfg, {min: 1, max: 30, step: 0.1, arrow: 0.5}, onSV('124', 'value'))));
  const row3 = [cuNum(cus('base'), Number(val('127', 'value')) || prof.base, {min: 256, max: 2048, step: 64, int: true}, onSV('127', 'value'))];
  if (prof.sd && T.prompt['120']) row3.push(cuNum(cus('clip'), Number(val('120', 'stop_at_clip_layer')) || -1, {min: -4, max: -1, int: true}, onSV('120', 'stop_at_clip_layer')));
  if (prof.shift != null) row3.push(cuNum(cus('shift'), S.cm.shift != null ? S.cm.shift : prof.shift, {min: 0, max: 12, step: 0.1, arrow: 0.5}, x => { S.cm.shift = x; save(); }));
  if (prof.guidance != null) row3.push(cuNum(cus('guid'), S.cm.guidance != null ? S.cm.guidance : prof.guidance, {min: 0, max: 10, step: 0.1, arrow: 0.5}, x => { S.cm.guidance = x; save(); }));
  for (let i = 0; i < row3.length; i += 2) box.append(two(row3[i], row3[i + 1] || h('div')));
  if (prof.sd) box.append(two(h('div', {class: 'f'}, h('label', {class: 'lab', text: cus('pfx')}), cuText('121', 'string_a')), h('div', {class: 'f'}, h('label', {class: 'lab', text: cus('npfx')}), cuText('122', 'string_a'))));
  const sep = c.src !== 'ckpt' || info.clip === false || info.vae === false;
  if (sep && prof.te) {
    const teOpts = oiOpts(prof.te[0][0], prof.te[0][0] === 'DualCLIPLoader' ? 'clip_name1' : 'clip_name');
    const r = [cuSelBox(cus('te'), S.cm.te1 || prof.te[0][1], teOpts, x => { S.cm.te1 = x; save(); cuStore(); })];
    if (prof.te[0][0] === 'DualCLIPLoader') r.push(cuSelBox(cus('te2'), S.cm.te2 || prof.te[0][2], teOpts, x => { S.cm.te2 = x; save(); cuStore(); }));
    box.append(two(r[0], r[1] || h('div')));
  }
  const vr = [cuSelBox(cus('vae'), S.cm.vae || (sep ? prof.vae || '' : ''), oiOpts('VAELoader', 'vae_name'), x => { S.cm.vae = x; save(); cuStore(); }, sep ? null : cus('vaeCk'))];
  if (c.src === 'unet') vr.push(cuSelBox(cus('dtype'), S.cm.dtype || 'default', oiOpts('UNETLoader', 'weight_dtype'), x => { S.cm.dtype = x; save(); cuStore(); }));
  box.append(two(vr[0], vr[1] || h('div')));
  if (prof.cfg1) box.append(h('div', {class: 'muted', text: cus('hCfg1')}));
  box.append(h('div', {class: 'muted', text: cus('saved')}));
  return box;
}
function cuText(id, k) { const i = h('input', {type: 'text', value: val(id, k) || ''}); i.onchange = () => { setVal(id, k, i.value); cuStore(); }; return i; }
function drawCustom(box) {
  box.replaceChildren(cuSelect());
  const c = cuCur(); if (!c.name) return;
  const line = h('div', {class: 'cuinfo muted', text: cus('reading')}); const hw = h('div', {class: 'cuhw'}); const panel = h('div');
  box.append(line, hw, panel);
  Promise.all([cuInfo(), cuSys()]).then(([info]) => {
    if (!box.isConnected || !info) return;
    const pk = cuProfKey(info); const prof = pk && CU_PROF[pk];
    if (!prof) { line.className = 'cuinfo bad'; line.textContent = kindLabel(info) + ' – ' + cus('unsup', kindLabel(info)); return; }
    if (!S.cm || S.cm.applied !== c.name) cuApply(prof, CU_SAVED[c.name]);
    const parts = [kindLabel(info), info.kind === 'unknown' ? null : (c.src === 'ckpt' && info.clip && info.vae ? cus('full') : cus('only')),
      info.dtype ? ({F8_E4M3: 'fp8', F8_E5M2: 'fp8 (e5m2)', BF16: 'bf16', F16: 'fp16', F32: 'fp32', I8: 'int8', GGUF: 'GGUF'}[info.dtype] || info.dtype) : null, info.size ? (info.size / 1024 ** 3).toFixed(1) + ' GB' : null].filter(Boolean);
    line.textContent = parts.join(' · '); if (info.kind === 'unknown') line.textContent += ' – ' + cus('unk');
    const hv = cuHw(info, prof); if (hv) { hw.className = 'cuhw ' + hv.lvl; hw.textContent = hv.text; }
    panel.replaceChildren(cuPanel(info, prof));
  });
}
const _drawModelsCU = drawModels;
drawModels = function (box) { if (FAMILY === 'custom') return drawCustom(box); return _drawModelsCU(box); };
const _findMissingCU = findMissing;
findMissing = function () {
  let m = _findMissingCU(); if (FAMILY !== 'custom') return m;
  const c = cuCur(); if (c.src !== 'ckpt') m = m.filter(x => x.what !== c.name);
  return m;
};
/* building the run for the detected model type */
function cuRefs(P, from, to, skip) {
  for (const [id, n] of Object.entries(P)) { if (skip && skip.includes(id)) continue; for (const [k, v] of Object.entries(n.inputs || {})) if (Array.isArray(v) && v.length === 2 && String(v[0]) === from[0] && v[1] === from[1]) n.inputs[k] = [to[0], to[1]]; }
}
function cuTransform(P) {
  if (!S.cm) S.cm = {};
  const c = cuCur(); const info = CU.info; if (!c.name || !info) return; const pk = cuProfKey(info); const prof = pk && CU_PROF[pk]; if (!prof) return;
  const meta = P['2'] && P['2']._meta;
  if (c.src === 'unet') P['2'] = {class_type: 'UNETLoader', inputs: {unet_name: c.name, weight_dtype: (S.cm && S.cm.dtype) || 'default'}, _meta: meta};
  if (c.src === 'gguf') P['2'] = {class_type: 'UnetLoaderGGUF', inputs: {unet_name: c.name}, _meta: meta};
  const needTE = c.src !== 'ckpt' || info.clip === false, needVAE = c.src !== 'ckpt' || info.vae === false;
  if (needTE && prof.te) {
    const d = prof.te[0];
    if (d[0] === 'CLIPLoader') P['901'] = {class_type: 'CLIPLoader', inputs: {clip_name: S.cm.te1 || d[1], type: d[2], device: 'default'}, _meta: {title: 'Text encoder (CUSTOM)'}};
    else P['901'] = {class_type: 'DualCLIPLoader', inputs: {clip_name1: S.cm.te1 || d[1], clip_name2: S.cm.te2 || d[2], type: d[3]}, _meta: {title: 'Text encoders (CUSTOM)'}};
    cuRefs(P, ['2', 1], ['901', 0]);
  }
  if (!prof.sd && P['120']) { const src = P['120'].inputs.clip; cuRefs(P, ['120', 0], src); delete P['120']; }
  const vae = S.cm.vae || (needVAE ? prof.vae : '');
  if (vae) { P['902'] = {class_type: 'VAELoader', inputs: {vae_name: vae}, _meta: {title: 'VAE (CUSTOM)'}}; cuRefs(P, ['2', 2], ['902', 0]); if (P['126']) P['126'].inputs.any_01 = ['902', 0]; }
  if (prof.latent && P['70']) P['70'].class_type = prof.latent;
  if (prof.shiftNode) { P['903'] = {class_type: prof.shiftNode, inputs: {model: ['68', 0], shift: S.cm.shift != null ? S.cm.shift : prof.shift}, _meta: {title: 'Sampling shift (CUSTOM)'}}; cuRefs(P, ['68', 0], ['903', 0], ['903']); }
  if (prof.guidance != null && P['3']) { P['904'] = {class_type: 'FluxGuidance', inputs: {conditioning: ['3', 0], guidance: S.cm.guidance != null ? S.cm.guidance : prof.guidance}, _meta: {title: 'Flux guidance (CUSTOM)'}}; cuRefs(P, ['3', 0], ['904', 0], ['904']); }
  if (P['35'] && P['35'].inputs) P['35'].inputs.modelname = c.name;
}
const _bpCU = buildPrompt;
buildPrompt = function (seed, cnt) { const wf = _bpCU(seed, cnt); if (T && T.family === 'custom') { try { cuTransform(wf); } catch (e) { console.error(e); } } return wf; };
/* before a run on the CUSTOM tab: supported type, text encoders on disk, hardware */
async function cuPreRun() {
  if (!T || T.family !== 'custom') return true; if (!S.cm) S.cm = {};
  const c = cuCur(); if (!c.name) return true; const info = await cuInfo(); await cuSys();
  const pk = cuProfKey(info); const prof = pk && CU_PROF[pk];
  if (!prof) { await xModal(cus('unsT'), [h('p', {text: cus('unsup', kindLabel(info))})], [[cus('ok'), 'ok', true]]); return false; }
  const needTE = c.src !== 'ckpt' || info.clip === false;
  if (needTE && prof.te) {
    const d = prof.te[0]; const want = d[0] === 'CLIPLoader' ? [S.cm.te1 || d[1]] : [S.cm.te1 || d[1], S.cm.te2 || d[2]];
    const have = oiOpts(d[0], d[0] === 'DualCLIPLoader' ? 'clip_name1' : 'clip_name'); const miss = want.filter(x => !have.includes(x));
    if (miss.length) {
      const comps = miss.map(f => CAT && CAT.models.find(m => m.kind === 'component' && m.file === f)).filter(Boolean);
      const size = comps.reduce((a, m) => a + (m.size || 0), 0);
      if (comps.length === miss.length) {
        const a = await xModal(cus('teMiss'), [h('p', {text: cus('teMissB', kindLabel(info), miss.join(', '), fmtB(size))})], [[cus('cancel'), 'cancel'], [cus('dl'), 'dl', true]]);
        if (a === 'dl') comps.forEach(m => startDl(m));
      } else await xModal(cus('teMiss'), [h('p', {text: cus('teMissB', kindLabel(info), miss.join(', '), '?')})], [[cus('ok'), 'ok', true]]);
      return false;
    }
  }
  const hv = cuHw(info, prof);
  if (hv && hv.lvl === 'bad') { const a = await xModal(cus('hwT'), [h('p', {text: hv.text})], [[cus('cancel'), 'cancel'], [cus('anyway'), 'go', true]]); if (a !== 'go') return false; }
  return true;
}
const _runCU = run;
run = async function () { if (!(await cuPreRun())) return; return _runCU(); };

/* LoRA rows on every tab: fit, match, trigger words, separate text-encoder strength */
function curModelRef() {
  if (T && T.family === 'custom') { const c = cuCur(); return {folder: c.folder, name: c.name}; }
  const mf = modelField(); return {folder: mf === 'unet_name' ? 'diffusion_models' : 'checkpoints', name: val('2', mf) || ''};
}
const LM = new Map();
function loraMatch(L) {
  const m = curModelRef(); if (!m.name || !L.lora) return Promise.resolve(null); const key = m.folder + '|' + m.name + '|' + L.lora;
  if (!LM.has(key)) LM.set(key, fetch(API + '/artflow/lora-match?folder=' + encodeURIComponent(m.folder) + '&model=' + encodeURIComponent(m.name) + '&lora=' + encodeURIComponent(L.lora)).then(r => r.json()).catch(() => null));
  return LM.get(key);
}
function loraFit(r) {
  if (!r || !r.model || !r.lora) return null; const mk = r.model.kind, lk = r.lora.kind;
  if (r.lora.notlora) return 'bad';
  if (lk === 'unknown' || mk === 'unknown' || lk === 'missing' || mk === 'missing') return null;
  if (lk !== mk) return 'bad';
  if (r.match != null && !r.converted && r.match < 30) return 'bad';
  if ((r.lora.sub || '') !== (r.model.sub || '') && mk === 'sdxl') return 'part';
  if (r.match != null && !r.converted && r.match < 80) return 'part';
  return 'ok';
}
function addTrigger(w) {
  const cur = String(val('46', 'value') || ''); if (cur.toLowerCase().includes(w.toLowerCase())) return;
  setVal('46', 'value', cur.trim() ? cur.replace(/\s*,?\s*$/, '') + ', ' + w : w); renderControls();
}
const _loraListCU = loraList;
loraList = function (arr) {
  const box = _loraListCU(arr);
  const deco = () => {
    const rows = box.querySelectorAll(':scope > .lora');
    rows.forEach((row, i) => {
      const L = arr[i]; if (!L || row.nextElementSibling && row.nextElementSibling.classList.contains('lorax')) return;
      const x = h('div', {class: 'lorax'}); row.after(x);
      loraMatch(L).then(r => {
        if (!r || !x.isConnected) return; const fit = loraFit(r); const kinds = cus('lKind', kindLabel(r.lora), kindLabel(r.model));
        const nl = r.lora.notlora; const stem = String(L.lora).split(/[\\/]/).pop().replace(/\.[^.]+$/, '');
        const badge = h('span', {class: 'lfit ' + (fit || 'na'), text: nl === 'checkpoint' ? cus('nlCk') : nl === 'embedding' ? cus('nlEm', stem) : fit === 'ok' ? cus('lOk') : fit === 'part' ? cus('lPart') : fit === 'bad' ? cus('lBad') : kinds});
        const det = nl ? '' : [fit ? kinds : null, r.match != null ? (r.converted ? cus('lConv') : cus('lMatch', r.match)) : null].filter(Boolean).join(' · ');
        x.append(h('div', {class: 'lrow'}, badge, det ? h('span', {class: 'muted', text: det}) : null));
        if (fit === 'bad') { if (L.on) { L.on = false; save(); } row.classList.add('off', 'lbad'); const cb = row.querySelector('input[type=checkbox]'); if (cb) { cb.checked = false; cb.disabled = true; } }
        const sd = r.model.kind === 'sd15' || r.model.kind === 'sdxl';
        if (sd && r.lora.te && fit !== 'bad') x.append(h('div', {class: 'lrow'}, h('span', {class: 'muted', text: cus('lTe')}),
          num(L.strength2 != null ? L.strength2 : L.strength, {min: 0, max: 2, step: 0.01, arrow: 0.05, slider: true}, v => { L.strength2 = v; save(); })));
        const tr = (r.lora.triggers || []);
        if (tr.length && fit !== 'bad') x.append(h('div', {class: 'ltrig'}, h('span', {class: 'muted', text: cus('trig')}),
          ...tr.map(w => h('button', {class: 'tchip', type: 'button', text: w, title: cus('trigAdd'), onclick: () => { addTrigger(w); toast(cus('trigDone')); }})),
          h('button', {class: 'btn sm', type: 'button', text: cus('trigAll'), onclick: () => { tr.forEach(addTrigger); toast(cus('trigDone')); }})));
        const tg = (r.lora.tags || []).slice(0, 10);
        if (tg.length && fit !== 'bad') x.append(h('details', {class: 'ltags'}, h('summary', {class: 'muted', text: cus('tags')}),
          h('div', {class: 'ltrig'}, ...tg.map(w => h('button', {class: 'tchip sub', type: 'button', text: w, title: cus('trigAdd'), onclick: () => { addTrigger(w); toast(cus('trigDone')); }})))));
      });
    });
  };
  new MutationObserver(deco).observe(box, {childList: true}); deco();
  return box;
};
const _setLorasCU = setLoras;
setLoras = function (node, arr) {
  _setLorasCU(node, arr); if (!node) return;
  arr.forEach((L, i) => { const k = 'lora_' + (i + 1); if (node.inputs[k] && L.strength2 != null && isFinite(L.strength2)) node.inputs[k].strengthTwo = Number(L.strength2); });
};
/* image info: take the steps, CFG, sampler, size, CLIP skip and seed of an image for the CUSTOM tab */
const A1_SAMPLER = {'euler a': ['euler_ancestral'], 'euler': ['euler'], 'heun': ['heun'], 'lms': ['lms'], 'ddim': ['ddim'], 'uni_pc': ['uni_pc'], 'unipc': ['uni_pc'], 'lcm': ['lcm'],
  'dpm++ 2m': ['dpmpp_2m'], 'dpm++ 2m karras': ['dpmpp_2m', 'karras'], 'dpm++ sde': ['dpmpp_sde'], 'dpm++ sde karras': ['dpmpp_sde', 'karras'], 'dpm++ 2m sde': ['dpmpp_2m_sde'],
  'dpm++ 2m sde karras': ['dpmpp_2m_sde', 'karras'], 'dpm++ 3m sde': ['dpmpp_3m_sde'], 'dpm++ 3m sde karras': ['dpmpp_3m_sde', 'karras'], 'dpm++ 2s a': ['dpmpp_2s_ancestral'],
  'dpm++ 2s a karras': ['dpmpp_2s_ancestral', 'karras'], 'dpm2': ['dpm_2'], 'dpm2 a': ['dpm_2_ancestral'], 'dpm2 karras': ['dpm_2', 'karras'], 'dpm2 a karras': ['dpm_2_ancestral', 'karras'], 'restart': ['res_multistep']};
const _showInfoCU = showInfo;
showInfo = function (meta, url) {
  _showInfoCU(meta, url);
  if (FAMILY !== 'custom' || !meta) return; let p = null;
  if (meta.parameters) p = parseA1111(meta.parameters).params; else if (meta.prompt) { const r = parseComfy(meta.prompt); p = r && r.params; }
  if (!p || !p.Steps) return;
  const btns = document.querySelector('#iiOut > p'); if (!btns) return;
  btns.append(' ', h('button', {class: 'btn sm', type: 'button', text: cus('iiApply'), onclick: () => {
    const got = []; const sOpts = oiOpts('KSampler', 'sampler_name'), schOpts = oiOpts('KSampler', 'scheduler');
    let smp = String(p.Sampler || '').trim(), sch = String(p['Schedule type'] || p.Scheduler || '').trim().toLowerCase();
    const mp = A1_SAMPLER[smp.toLowerCase()]; if (mp) { smp = mp[0]; if (mp[1] && !sch) sch = mp[1]; }
    if (sOpts.includes(smp)) { for (const id of ['6', '17', '25', '30', '62', '33']) if (T.prompt[id]) setVal(id, 'sampler_name', smp); got.push('sampler ' + smp); }
    if (schOpts.includes(sch)) { for (const id of ['6', '17', '25', '30', '62', '33']) if (T.prompt[id]) setVal(id, 'scheduler', sch); got.push('scheduler ' + sch); }
    if (Number(p.Steps) > 0) { setVal('123', 'value', Number(p.Steps)); got.push('steps ' + p.Steps); }
    const cf = Number(p['CFG scale'] || p.CFG); if (cf > 0) { setVal('124', 'value', cf); got.push('CFG ' + cf); }
    const sz = String(p.Size || '').match(/(\d+)\s*x\s*(\d+)/); if (sz && T.prompt['127']) { const b = Math.round(Math.sqrt(sz[1] * sz[2]) / 64) * 64; setVal('127', 'value', b); got.push(sz[1] + '×' + sz[2]); }
    const cs = Number(p['Clip skip']); if (cs > 0 && T.prompt['120']) { setVal('120', 'stop_at_clip_layer', -cs); got.push('clip skip ' + cs); }
    const sd = Number(p.Seed); if (sd > 0) { S.seed = sd; S.seedRandom = false; got.push('seed ' + sd); }
    cuStore(); save(); renderControls(); toast(cus('iiApplied', got.join(', ')));
  }}));
};
