/* ---------- Hungarian prompting: the prompt is written in Hungarian and translated to English on this computer ----------
   SPDX-License-Identifier: GPL-3.0-or-later
   - only offered when the interface is Hungarian; off by default, switched in card 1 or in Settings
   - the translator (ArtFlawless HU→EN, fine-tuned opus-mt-tc-big-hu-en, CC-BY 4.0) is downloaded once, then works offline
   - the translation can be corrected by hand; a hand-corrected text is kept until the user asks for a new translation
   - the content check sees BOTH the Hungarian original and the English translation */
const LS_HUP = 'artflow.studio.huprompt.v1';
let HUP = {on: false};
try { Object.assign(HUP, JSON.parse(localStorage.getItem(LS_HUP) || '{}')); } catch (_) {}
const TRS = {installed: null, size: 0, mb: 0, dl: null, poll: null, timers: {}};
const HU_KIND = {p: '46', n: '51'};
let HU_SRC = '';   // the Hungarian original while a translated generation is being sent (read by the content check)
const HUS = {
  sw: 'Magyar promptolás', tag: 'HU → EN',
  swHint: 'Bekapcsolva magyarul írhatod a promptot: generáláskor a Studio a saját gépeden lefordítja angolra, mert a képmodellek angolul értenek. Az angol szavakat és kifejezéseket (pl. golden hour, 85mm) változatlanul hagyja.',
  need: 'Ehhez egy fordítómodell kell (ArtFlawless HU→EN, kb. {0} MB). Csak egyszer kell letölteni, utána internet nélkül is működik.',
  dl: 'Letöltés ({0} MB)', cancel: 'Mégse', dling: 'Fordítómodell letöltése…', dlRun: '{0} / {1} MB · {2} MB/s', dlErr: 'A fordítómodell letöltése nem sikerült: {0}', dlDone: 'A fordítómodell letöltve, a magyar promptolás be van kapcsolva.',
  noSrv: 'A fordítás nem érhető el (a Studio háttérrésze nem válaszol).',
  label: 'Saját prompt – írhatsz magyarul, angol szavakkal vegyesen is',
  trP: 'Angol fordítás', trN: 'A negatív prompt angolul', trSub: ' – ez megy a képmodellhez',
  busy: 'fordítás…', ready: 'kész · {0} s', manual: 'kézzel javítva', err: 'hiba',
  empty: 'A fordítás itt jelenik meg, amint írsz valamit.',
  hintP: 'Gépelés közben, egy rövid szünet után frissül, és a végső prompt mezőben is ez jelenik meg. Ha valamit rosszul fordított, itt kézzel kijavíthatod. A tartalomszűrő a magyar és az angol szöveget is ellenőrzi.',
  hintN: 'Ezt is kijavíthatod kézzel.',
  stale: 'A magyar szöveg a kézi javítás óta megváltozott – a generálás továbbra is a javított angol szöveget használja.',
  again: 'Újrafordítás', trErr: 'Nem sikerült lefordítani a promptot: {0}',
  needFirst: 'A magyar promptoláshoz előbb töltsd le a fordítómodellt (1. kártya), vagy kapcsold ki a magyar promptolást.',
  loading: 'A fordítómodell betöltése… (csak az első fordításnál tart pár másodpercig)'
};
const hus = (k, ...a) => String(HUS[k]).replace(/\{(\d+)\}/g, (_, i) => a[i]);
const huOffered = () => LANG === 'hu';
const huWanted = () => huOffered() && !!HUP.on;
const huActive = () => huWanted() && TRS.installed === true;
function huSaveCfg() { try { localStorage.setItem(LS_HUP, JSON.stringify(HUP)); } catch (_) {} }
function hut(kind) { if (!S.hut || typeof S.hut !== 'object') S.hut = {}; if (!S.hut[kind]) S.hut[kind] = {src: '', en: '', man: false}; return S.hut[kind]; }
function huSrc(kind) { const id = HU_KIND[kind]; return T && T.prompt[id] ? String(val(id, 'value') || '').trim() : ''; }

async function trStatus() {
  try { const r = await fetch(API + '/artflow/translate/status', {cache: 'no-store'}); const j = await r.json();
    TRS.installed = !!j.installed; TRS.size = j.size || 0; TRS.mb = Math.round((j.size || 0) / 1e6); TRS.dl = j.dl || null; }
  catch (_) { TRS.installed = false; TRS.dl = {state: 'error', error: hus('noSrv')}; }
  return TRS;
}
function trPoll() {
  clearTimeout(TRS.poll);
  TRS.poll = setTimeout(async () => {
    const was = TRS.dl && TRS.dl.state; await trStatus(); const st = TRS.dl && TRS.dl.state;
    if (st === 'running') trPoll();
    else if (was === 'running' && st === 'done') { toast(hus('dlDone')); huBoxes(); huAll(); }
    else if (was === 'running' && st === 'error') toast(hus('dlErr', TRS.dl.error || '?'), 'err');
    huDraw();
  }, 700);
}
async function trDownload(cancel) {
  try { await fetch(API + '/artflow/translate/download', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({cancel: !!cancel})}); } catch (_) {}
  await trStatus(); huDraw(); if (!cancel) trPoll();
}
async function trCall(texts) {
  const r = await fetch(API + '/artflow/translate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({texts})});
  const j = await r.json().catch(() => ({})); if (!r.ok || !Array.isArray(j.texts)) throw new Error(j.error || ('HTTP ' + r.status)); return j;
}

/* translation of one field (p = prompt, n = negative prompt) */
async function huTranslate(kind, force) {
  if (!huActive()) return true; const st = hut(kind); const src = huSrc(kind);
  if (st.man && !force) { huDrawBox(kind); return true; }
  if (!src) { Object.assign(st, {src: '', en: '', man: false}); save(); huDrawBox(kind); return true; }
  if (!force && st.src === src && st.en) { huDrawBox(kind); return true; }
  st.busy = true; st.err = ''; huDrawBox(kind);
  try { const t0 = Date.now(); const slow = setTimeout(() => { st.slow = true; huDrawBox(kind); }, 1500); let j;
    try { j = await trCall([src]); } finally { clearTimeout(slow); st.slow = false; }
    if (huSrc(kind) !== src && !force) { st.busy = false; return huTranslate(kind); }   // typed on meanwhile
    Object.assign(st, {src, en: j.texts[0], man: false, busy: false, sec: ((j.ms != null ? j.ms : Date.now() - t0) / 1000).toFixed(1)}); save(); huDrawBox(kind); return true; }
  catch (e) { st.busy = false; st.err = e.message; huDrawBox(kind); toast(hus('trErr', e.message), 'err'); return false; }
}
function huSoon(kind) { clearTimeout(TRS.timers[kind]); if (!huActive()) return; huDrawBox(kind); TRS.timers[kind] = setTimeout(() => huTranslate(kind), 900); }
function huAll() { if (huActive()) { huTranslate('p'); huTranslate('n'); } }

/* card 1: the switch with the download panel, and the translation boxes under the prompt fields */
function huPrompt() {
  if (!huOffered()) return null;
  const box = h('div', {class: 'hub', id: 'huBox', 'data-help': 'hu:sw'}); huDraw(box); if (HUP.on && TRS.installed == null) trStatus().then(() => { huDraw(); huAll(); }); return box;
}
function huDraw(box) {
  box = box || $('#huBox'); if (!box) return;
  const kids = [h('div', {class: 'f inline'}, h('label', {class: 'lab'}, HUS.sw, h('span', {class: 'tag', text: HUS.tag})), sw(HUP.on, x => huSet(x))),
    h('div', {class: 'hint', text: HUS.swHint})];
  const d = TRS.dl || {};
  if (HUP.on && d.state === 'running') {
    const pc = d.total ? Math.min(100, d.done / d.total * 100) : 0;
    kids.push(h('div', {class: 'dl'}, h('div', {class: 'hint', text: HUS.dling}),
      h('div', {class: 'row'}, h('div', {class: 'pbar'}, h('i', {style: 'width:' + pc.toFixed(1) + '%'})),
        h('span', {class: 'hint', text: hus('dlRun', Math.round(d.done / 1e6), Math.round((d.total || TRS.size) / 1e6), ((d.speed || 0) / 1e6).toFixed(0))}),
        h('button', {class: 'btn sm', type: 'button', text: HUS.cancel, onclick: () => trDownload(true)}))));
  } else if (HUP.on && TRS.installed === false) {
    kids.push(h('div', {class: 'dl'}, h('div', {class: 'hint', text: hus('need', TRS.mb || 473)}),
      d.state === 'error' ? h('div', {class: 'hint', style: 'color:var(--err)', text: hus('dlErr', d.error || '?')}) : null,
      h('div', {class: 'row'}, h('button', {class: 'btn sm acc', type: 'button', text: hus('dl', TRS.mb || 473), onclick: () => trDownload(false)}),
        h('button', {class: 'btn sm', type: 'button', text: HUS.cancel, onclick: () => huSet(false)}))));
  }
  box.replaceChildren(...kids.filter(Boolean));
}
function huSet(on) {
  HUP.on = !!on; huSaveCfg(); const m = $('#huSw'); if (m) m.checked = HUP.on;
  const lab = document.querySelector('[data-help="46.value"] > .lab'); if (lab) lab.textContent = huActive() ? HUS.label : t('prompt');
  if (HUP.on) trStatus().then(() => { huDraw(); huLabel(); huBoxes(); huAll(); if (TRS.dl && TRS.dl.state === 'running') trPoll(); });
  huDraw(); huBoxes(); huDetectNote();
}
function huLabel() { const lab = document.querySelector('[data-help="46.value"] > .lab'); if (lab) lab.textContent = huActive() ? HUS.label : t('prompt'); }
function huDetect() { if (!huOffered()) return null; const el = h('div', {class: 'note', id: 'huDetect'},
  h('span', {text: 'Magyar szöveget látok a promptban – a képmodellek angolul értenek. '}), h('button', {class: 'btn sm acc', type: 'button', text: 'Magyar promptolás bekapcsolása', onclick: () => huSet(true)}));
  el.hidden = !(!HUP.on && looksHungarian(val('46', 'value'))); return el; }
function huTrans(kind) { if (!huOffered()) return null; const b = h('div', {class: 'tr', id: 'huTr' + kind, 'data-help': kind === 'p' ? 'hu:tr' : 'hu:trN'}); b.hidden = !huActive(); return b; }
function huBoxes() { for (const k of Object.keys(HU_KIND)) { const b = $('#huTr' + k); if (b) { b.hidden = !huActive(); if (!b.hidden) huDrawBox(k); } } huLabel(); }
function huDrawBox(kind) {
  const b = $('#huTr' + kind); if (!b || b.hidden) return; const st = hut(kind); const src = huSrc(kind);
  const status = st.busy ? (st.slow ? HUS.loading : HUS.busy) : st.err ? HUS.err : st.man ? HUS.manual : (st.en && st.sec ? hus('ready', String(st.sec).replace('.', ',')) : '');
  let ta = b.querySelector('textarea');
  if (!ta) {
    ta = h('textarea', {rows: kind === 'p' ? 4 : 2, spellcheck: false, placeholder: HUS.empty});
    ta.oninput = () => { const s = hut(kind); s.en = ta.value; s.man = true; if (!s.src) s.src = huSrc(kind); save(); huDrawBox(kind); };
    b.replaceChildren(h('div', {class: 'th'}, h('span', null, h('b', {text: kind === 'p' ? HUS.trP : HUS.trN}), HUS.trSub), h('span', {class: 'st'})), ta, h('div', {class: 'ft'}));
  }
  b.querySelector('.st').textContent = status; b.classList.toggle('busy', !!st.busy);
  if (document.activeElement !== ta && ta.value !== (st.en || '')) ta.value = st.en || '';
  const stale = st.man && src && st.src !== src;
  const ft = b.querySelector('.ft');
  ft.replaceChildren(...[stale ? h('div', {class: 'hint warn', text: HUS.stale}) : null,
    h('div', {class: 'row'}, h('div', {class: 'hint', text: kind === 'p' ? HUS.hintP : HUS.hintN}),
      st.man ? h('button', {class: 'btn sm', type: 'button', text: HUS.again, onclick: () => huTranslate(kind, true)}) : null)].filter(Boolean));
}

/* Hungarian text typed while Hungarian prompting is off: the image models read it badly (and may draw something
   unrelated), so the Studio offers to switch the translation on */
const HUW = new Set(['egy', 'és', 'az', 'nő', 'nők', 'férfi', 'lány', 'fiú', 'mellett', 'alatt', 'felett', 'fölött', 'között', 'előtt', 'mögött', 'fiatal', 'idős',
  'öreg', 'haj', 'hajú', 'hajjal', 'szem', 'kék', 'piros', 'vörös', 'zöld', 'fekete', 'fehér', 'sárga', 'háttér', 'háttérben', 'kezében', 'ül', 'áll', 'sétál', 'fekszik',
  'néz', 'mosolyog', 'nevet', 'tenger', 'erdő', 'erdőben', 'utca', 'utcán', 'város', 'ház', 'szoba', 'szobában', 'konyha', 'konyhában', 'este', 'reggel', 'éjszaka',
  'naplemente', 'napfény', 'fény', 'meleg', 'hideg', 'régi', 'nagy', 'kis', 'kicsi', 'szép', 'portré', 'portréja', 'stílus', 'stílusú', 'ruha', 'ruhában', 'kabát', 'kabátban']);
function looksHungarian(t) {
  const s = String(t || '').toLowerCase(); if (s.replace(/\s+/g, '').length < 8) return false;
  const words = s.split(/[^a-záéíóöőúüű]+/).filter(Boolean); if (!words.length) return false;
  const known = words.filter(w => HUW.has(w)).length, dbl = (s.match(/[őű]/g) || []).length, acc = (s.match(/[áéíóöú]/g) || []).length;
  const suff = words.filter(w => w.length > 4 && /(ban|ben|ból|ből|ban|nak|nek|val|vel|ról|ről|tól|től|hoz|hez|höz|ján|jén|ája|éje|ával|ével|ódik|ődik)$/.test(w)).length;
  return known >= 2 || (known >= 1 && (dbl + suff + acc) >= 1) || dbl >= 2 || (acc >= 4 && suff >= 2);
}
const HU_ASKED = new Set();
function huDetectNote() {
  const el = $('#huDetect'); if (!el) return;
  const show = huOffered() && !HUP.on && looksHungarian(val('46', 'value'));
  el.hidden = !show;
}
function huAskModal() {
  return new Promise(res => {
    MODAL_KIND = 'hudetect'; let done = false; const hu = LANG === 'hu';
    const fin = v => { if (done) return; done = true; obs.disconnect(); $('#modal').classList.remove('open'); res(v); };
    $('#modalTitle').textContent = hu ? 'Magyarul írtad a promptot' : 'Your prompt looks Hungarian';
    const body = $('#modalBody');
    body.replaceChildren(h('p', {text: hu ? 'A képmodellek angolul értenek: fordítás nélkül a magyar szövegből többnyire egészen más kép lesz, mint amit kértél. Bekapcsolod a magyar promptolást? A Studio a saját gépeden lefordítja a promptot angolra.'
        : 'Image models understand English: an untranslated Hungarian prompt usually gives a different picture than the one you asked for. Hungarian prompting (translation on this computer) is available in the Hungarian interface.'}),
      h('div', {class: 'row', style: 'justify-content:flex-end;gap:8px;flex-wrap:wrap'},
        h('button', {class: 'btn sm', type: 'button', text: hu ? 'Mégse' : 'Cancel', onclick: () => fin('cancel')}),
        h('button', {class: 'btn sm', type: 'button', text: hu ? 'Így küldöm el' : 'Send it as it is', onclick: () => fin('raw')}),
        h('button', {class: 'btn sm go2', type: 'button', text: hu ? 'Bekapcsolom' : 'Switch to Hungarian', onclick: () => fin('on')})));
    $('#modal').classList.add('open');
    const obs = new MutationObserver(() => { if (!$('#modal').classList.contains('open')) fin('cancel'); }); obs.observe($('#modal'), {attributes: true, attributeFilter: ['class']});
  });
}
/* Hungarian interface: the "default European look" of Z-Image Turbo starts switched on (switched off, Z-Image draws
   mostly East Asian faces); the user's own choice is kept */
function huLookDefault() { const id = T && T.ids && T.ids.look; if (!id || LANG !== 'hu' || !T.prompt[id]) return; const k = id + '.value'; if (!(k in S.vals)) { S.vals[k] = true; save(); } }

/* sending: the English text goes to the model, the content check sees both texts */
const _uptHu = userPromptText;
userPromptText = function () { return _uptHu() + (HU_SRC ? ' ' + HU_SRC : ''); };
const _runHu = run;
run = async function () {
  if (T && !huWanted() && !S.groups['1a'] && !S.groups['1d']) {
    const txt = String(val('46', 'value') || '').trim();
    if (looksHungarian(txt) && !HU_ASKED.has(txt)) {
      const a = await huAskModal();
      if (a === 'cancel') return;
      if (a === 'raw') { HU_ASKED.add(txt); return _runHu(); }
      if (LANG !== 'hu') { setLang('hu'); HUP.on = true; huSaveCfg(); huSet(true); return; }
      huSet(true); await trStatus(); huDraw(); huBoxes();
      if (TRS.installed !== true) { toast(hus('needFirst'), 'err'); return; }
      return run();
    }
  }
  if (!T || !huWanted() || S.groups['1a'] || S.groups['1d']) return _runHu();
  if (TRS.installed !== true) { await trStatus(); if (TRS.installed !== true) { toast(hus('needFirst'), 'err'); huDraw(); return; } }
  for (const k of Object.keys(HU_KIND)) if (T.prompt[HU_KIND[k]] && !(await huTranslate(k))) return;
  const keep = {}, srcs = [];
  for (const [k, id] of Object.entries(HU_KIND)) {
    if (!T.prompt[id]) continue; const key = id + '.value';
    keep[key] = {had: Object.prototype.hasOwnProperty.call(S.vals, key), v: S.vals[key]};
    srcs.push(huSrc(k)); S.vals[key] = hut(k).en || '';
  }
  HU_SRC = srcs.join(' ');
  try { return await _runHu(); }
  finally { HU_SRC = ''; for (const [key, o] of Object.entries(keep)) { if (o.had) S.vals[key] = o.v; else delete S.vals[key]; } save(); }
};
function initHuPrompt() {
  document.addEventListener('input', e => { const f = e.target.closest && e.target.closest('[data-help]'); if (!f || e.target.closest('.tr')) return;
    const k = f.getAttribute('data-help'); if (k === '46.value') { huSoon('p'); clearTimeout(TRS.timers.det); TRS.timers.det = setTimeout(huDetectNote, 600); } else if (k === '51.value') huSoon('n'); });
  const m = $('#huSw'); if (m) { m.checked = !!HUP.on; m.onchange = () => { huSet(m.checked); }; }
  const mi = $('#huMi'); if (mi) mi.hidden = !huOffered();
  if (HUP.on) trStatus().then(() => { huDraw(); huBoxes(); huAll(); if (TRS.dl && TRS.dl.state === 'running') trPoll(); });
}
