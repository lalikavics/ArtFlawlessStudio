/* ---------- model files that changed their name, and the base LoRA of card 2 ----------
   SPDX-License-Identifier: GPL-3.0-or-later
   - a model file the settings ask for but that is not there is matched to a file of the same name with another version
     number ("... v1" -> "... v1.1"); the newest one is taken, so a newer download is found by itself
   - the base LoRA (card 2) is matched loosely: any LoRA with "Hands" and "Feet" in its name
   - when the base LoRA is not there, card 2 says so and offers its download page, the LoRA folder and a new check
   - "Check again" (missing components, notifications) reloads the model lists and says what it found */
const BASE_LORA_URL = 'https://civitai.red/api/download/models/2577477?fileId=2464717';
const BL_TX = {
  en: {miss: 'The base LoRA (Hands + Feet + skin) is not downloaded yet. It needs a free Civitai login: open its page, download the file and put it into the LoRA folder, then press Check again. Any version is accepted.',
       page: 'Download page', folder: 'LoRA folder', again: 'Check again', checking: 'Checking…', allOk: 'Everything is in place.',
       stillMiss: 'Still missing: {0}', found: 'Found: {0}'},
  hu: {miss: 'Az alap LoRA (Hands + Feet + skin) még nincs letöltve. Ingyenes Civitai-belépés kell hozzá: nyisd meg az oldalát, töltsd le a fájlt, és tedd a LoRA-mappába, majd nyomd meg az Újraellenőrzést. Bármelyik verzió jó.',
       page: 'Letöltési oldal', folder: 'LoRA-mappa', again: 'Újraellenőrzés', checking: 'Ellenőrzés…', allOk: 'Minden a helyén van.',
       stillMiss: 'Még hiányzik: {0}', found: 'Megtalálva: {0}'}
};
const blt = (k, ...a) => { let s = (BL_TX[LANG] || BL_TX.en)[k] || BL_TX.en[k]; a.forEach((v, i) => { s = s.replace('{' + i + '}', v); }); return s; };

const MDL_EXT = /\.(safetensors|ckpt|pt|pth|bin|gguf|sft)$/i;
function mdlSplit(f) { const s = String(f).replace(/\\/g, '/'); const i = s.lastIndexOf('/'); return [i < 0 ? '' : s.slice(0, i + 1).toLowerCase(), i < 0 ? s : s.slice(i + 1)]; }
// the name without its extension and its version number at the end: "Hands + Feet + skin perfection style zib v1.1" -> "handsfeetskinperfectionstylezib"
function mdlKey(f) { return mdlSplit(f)[1].replace(MDL_EXT, '').toLowerCase().replace(/[\s_\-.(]*v?\d+(\.\d+)*\)?$/, '').replace(/[^a-z0-9]/g, ''); }
function mdlVer(f) { const m = /v?(\d+(?:\.\d+)*)\)?$/i.exec(mdlSplit(f)[1].replace(MDL_EXT, '')); return m ? m[1].split('.').map(Number) : []; }
function verCmp(a, b) { for (let i = 0; i < Math.max(a.length, b.length); i++) { const d = (a[i] || 0) - (b[i] || 0); if (d) return d; } return 0; }
const newest = list => list.slice().sort((a, b) => verCmp(mdlVer(b), mdlVer(a)) || String(b).localeCompare(String(a)))[0];
const isBaseLora = f => { const n = mdlSplit(f)[1]; return /hands/i.test(n) && /feet/i.test(n) && MDL_EXT.test(n); };

// another version of a missing file among the options (same folder, same name without the version)
function otherVersion(want, opts, loose) {
  if (!want || !opts || opts.includes(want)) return null;
  const [dir] = mdlSplit(want); const key = mdlKey(want);
  let c = key.length >= 3 ? opts.filter(o => mdlSplit(o)[0] === dir && mdlKey(o) === key) : [];
  if (!c.length && loose) c = opts.filter(loose);
  return c.length ? newest(c) : null;
}
function baseLoraState() {
  const sp = spec('89', 'lora_name'); const opts = (sp && sp.options) || null; const cur = val('89', 'lora_name');
  if (!opts) return {ok: true};
  return {ok: !!cur && opts.includes(cur), cur, opts};
}
// sets the found versions in the settings; returns the names that were swapped in
function fixModelVersions() {
  const swapped = [];
  if (!T || !T.prompt) return swapped;
  for (const [id, n] of Object.entries(T.prompt)) {
    for (const k of Object.keys(n.inputs || {})) {
      const v = val(id, k); if (typeof v !== 'string' || !MDL_EXT.test(v)) continue;
      const sp = spec(id, k); if (!sp || sp.type !== 'COMBO' || !sp.options || sp.options.includes(v)) continue;
      const alt = otherVersion(v, sp.options, id === '89' && k === 'lora_name' && isBaseLora(v) ? isBaseLora : null);
      if (alt) { setVal(id, k, alt); swapped.push(alt); }
    }
  }
  const lsp = spec('89', 'lora_name'); const lopts = (lsp && lsp.options) || null;
  if (lopts) [S.loras, S.footLoras].forEach(arr => (arr || []).forEach(L => {
    if (L && L.lora && !lopts.includes(L.lora)) { const alt = otherVersion(L.lora, lopts, isBaseLora(L.lora) ? isBaseLora : null); if (alt) { L.lora = alt; swapped.push(alt); } }
  }));
  if (swapped.length) save();
  return swapped;
}
const _loadOI_bl = loadOI;
loadOI = async function () { await _loadOI_bl.apply(this, arguments); try { fixModelVersions(); } catch (_) {} };

// "Check again": reloads the lists of ComfyUI and tells what it found
async function recheckMissing(btn) {
  const txt = btn ? btn.textContent : ''; if (btn) { btn.disabled = true; btn.textContent = blt('checking'); }
  const before = new Set((T ? findMissing() : []).map(x => x.what));
  try { await loadOI(); if (typeof loadCatalog === 'function') await loadCatalog(); } catch (_) {}
  renderControls(); renderMissing();
  const m = T ? findMissing() : [];
  const gone = [...before].filter(w => !m.some(x => x.what === w));
  if (!m.length) toast(blt('allOk')); else toast(blt('stillMiss', m.map(x => x.what).join(', ')), 'err');
  if (gone.length && m.length) toast(blt('found', gone.join(', ')));
  if ($('#modal').classList.contains('open') && MODAL_KIND === 'notif') openNotif();
  if (btn && btn.isConnected) { btn.disabled = false; btn.textContent = txt; }
}

// card 2: what to do when the base LoRA is not there
const _baseLora_bl = baseLora;
baseLora = function () {
  const el = _baseLora_bl.apply(this, arguments); if (!el) return el;
  const st = baseLoraState(); if (st.ok) return el;
  const page = h('button', {class: 'btn sm', type: 'button', text: blt('page'), onclick: () => window.open(BASE_LORA_URL, '_blank')});
  const folder = h('button', {class: 'btn sm', type: 'button', text: blt('folder'), onclick: () => fetch(API + '/artflow/open-models', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({kind: 'loras'})}).catch(() => {})});
  const again = h('button', {class: 'btn sm', type: 'button', text: blt('again')}); again.onclick = () => recheckMissing(again);
  const note = h('div', {class: 'note blMiss'}, h('div', {text: blt('miss')}), h('div', {class: 'row', style: 'gap:6px;margin-top:7px;flex-wrap:wrap'}, page, folder, again));
  const head = el.querySelector('.subhead'); if (head) head.after(note); else el.prepend(note);
  return el;
};
// the saved settings are read after the first model lists, so the versions are matched again before card building
const _renderControls_bl = renderControls;
renderControls = function () { try { fixModelVersions(); } catch (_) {} return _renderControls_bl.apply(this, arguments); };
