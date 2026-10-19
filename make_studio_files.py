# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
"""Build-time patcher: adapts the user's Studio files to the official, downloadable model files.
Run:  python make_studio_files.py   (then python make_families.py)
Reads  studio/ (originals), writes studio_out/ (patched)."""
import json, os, re, shutil

REPO_URL = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REPO_URL'), encoding='utf-8').read().strip().rstrip('/')   # GitHub page: contact, issues, releases
APP_VERSION = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION'), encoding='utf-8').read().strip()   # single source of the version

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studio')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studio_out')
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(os.path.join(OUT, 'web'))
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'studio_init.py'), os.path.join(OUT, '__init__.py'))
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'catalog.json'), os.path.join(OUT, 'catalog.json'))
# setup pages (information, terms of use) in English and Hungarian, with the version and the project address filled in
def _reflow(text):
    # the setup's text boxes wrap by themselves: join the lines of a paragraph / list item, keep headings, blank lines and list starts
    out = []
    head = True  # the first block (name, version, credits, links) keeps its lines
    for ln in text.split('\n'):
        st = ln.strip()
        if not st: head = False
        cont = not head and out and out[-1].strip() and st and not st.startswith(('- ', '* ')) and not (st.isupper() and len(st) > 3) \
            and not (out[-1].strip().isupper() and len(out[-1].strip()) > 3) and not re.match(r'^\d+\.\s', st)
        if cont and not out[-1].rstrip().endswith(':'):
            out[-1] = out[-1].rstrip() + ' ' + st
        else:
            out.append(ln.rstrip())
    return '\n'.join(out)


for _name in ('info.txt', 'info_hu.txt', 'terms_en.txt', 'terms_hu.txt'):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', _name), encoding='utf-8-sig') as _f:
        _info = _reflow(_f.read().replace('{VERSION}', APP_VERSION).replace('{REPO}', REPO_URL))
    with open(os.path.join(OUT, _name), 'w', encoding='utf-8-sig', newline='\r\n') as _f:
        _f.write(_info)

UNET, CLIP, VAE = 'z_image_turbo_bf16.safetensors', 'qwen_3_4b.safetensors', 'ae.safetensors'

# ---- template.json ---------------------------------------------------------
t = json.load(open(os.path.join(SRC, 'web', 'template.json'), encoding='utf-8'))
assert t['prompt']['2']['class_type'] == 'CheckpointLoaderSimple'
t['prompt']['2'] = {'inputs': {'unet_name': UNET, 'weight_dtype': 'default'}, 'class_type': 'UNETLoader',
                    '_meta': {'title': 'Load diffusion model – Z-Image Turbo'}}
t['prompt']['65']['inputs']['clip_name'] = CLIP
t['prompt']['66']['inputs']['vae_name'] = VAE
# skin-noise tuning (tested on RTX 3060 Ti, same seed): the "cinematic / incredibly lifelike / skin pore" wording
# produced over-textured, blotchy skin and very tight crops; a plain wording plus a lighter base LoRA looks natural.
c = t['prompt']['88']['inputs']['code']
for a, b in [
    ('"pre": "detailed photorealistic cinematic style, incredibly lifelike portrait photograph. "', '"pre": "photorealistic portrait photograph. "'),
    ('soft natural light, detailed skin pore, natural skin texture, sharp focus', 'soft natural light, natural skin texture, sharp focus'),
    ('"Portrait": {"people": 1, "w": 832, "h": 1216, "shift": 3.0, "lora": 0.9,', '"Portrait": {"people": 1, "w": 832, "h": 1216, "shift": 3.0, "lora": 0.5,'),
    ('"pre": "detailed photorealistic cinematic style, realism style, candid photograph. "', '"pre": "photorealistic candid photograph. "'),
    ('"People – full body": {"people": 1, "w": 832, "h": 1216, "shift": 3.25, "lora": 1.0,', '"People – full body": {"people": 1, "w": 832, "h": 1216, "shift": 3.25, "lora": 0.6,'),
]:
    assert c.count(a) == 1, a
    c = c.replace(a, b)
t['prompt']['88']['inputs']['code'] = c
with open(os.path.join(OUT, 'web', 'template.json'), 'w', encoding='utf-8') as f:
    json.dump(t, f, ensure_ascii=False, separators=(',', ':'))

# ---- index.html ------------------------------------------------------------
h = open(os.path.join(SRC, 'web', 'index.html'), encoding='utf-8').read()
a = "field('2', 'ckpt_name', t('ckpt')"
b = "field('2', 'unet_name', t('ckpt')"
assert h.count(a) == 1
h = h.replace(a, b)
a = "CheckpointLoaderSimple: 'models\\\\checkpoints',"
b = "CheckpointLoaderSimple: 'models\\\\checkpoints', UNETLoader: 'models\\\\diffusion_models',"
assert h.count(a) == 1, h.count(a)
h = h.replace(a, b)
a, b = "ckpt: 'Model (checkpoint)'", "ckpt: 'Diffusion model'"
assert h.count(a) == 1; h = h.replace(a, b)
a, b = "ckpt: 'Modell (checkpoint)'", "ckpt: 'Diffúziós modell'"
assert h.count(a) == 1; h = h.replace(a, b)
open(os.path.join(OUT, 'web', 'index.html'), 'w', encoding='utf-8', newline='').write(h)

# ---- workflow (for ComfyUI's own editor) ----------------------------------
w = json.load(open(os.path.join(SRC, 'ArtFlawless-Studio-ZImageTurbo-EN.json'), encoding='utf-8'))
for l in w['links']:
    if l[1] == 2: assert l[2] == 0, l          # only MODEL output of node 2 is used
nodes = {n['id']: n for n in w['nodes']}
n2 = nodes[2]; assert n2['type'] == 'CheckpointLoaderSimple'
n2['type'] = 'UNETLoader'
n2['title'] = 'Load diffusion model – Z-Image Turbo'
n2['inputs'] = [{'localized_name': 'unet_name', 'name': 'unet_name', 'type': 'COMBO', 'widget': {'name': 'unet_name'}, 'link': None},
                {'localized_name': 'weight_dtype', 'name': 'weight_dtype', 'type': 'COMBO', 'widget': {'name': 'weight_dtype'}, 'link': None}]
n2['outputs'] = [{'localized_name': 'MODEL', 'name': 'MODEL', 'type': 'MODEL', 'links': [159]}]
n2['properties'] = {'Node name for S&R': 'UNETLoader'}
n2['widgets_values'] = [UNET, 'default']
n2['widgets_values_named'] = {'unet_name': UNET, 'weight_dtype': 'default'}
nodes[65]['widgets_values'][0] = CLIP; nodes[65]['widgets_values_named']['clip_name'] = CLIP
nodes[66]['widgets_values'][0] = VAE;  nodes[66]['widgets_values_named']['vae_name'] = VAE
# remove private leftovers (local path + an old test prompt) from the Prompt Extractor node
for k in ('_browsePath', '_browseSelectedAbsPath', 'pe_extracted_data'):
    nodes[48]['properties'].pop(k, None)
with open(os.path.join(OUT, 'ArtFlawless-Studio-ZImageTurbo-EN.json'), 'w', encoding='utf-8') as f:
    json.dump(w, f, ensure_ascii=False, separators=(',', ':'))

print('ok')

# ---- notification centre (header button with a "!" badge) -------------------
p = os.path.join(OUT, 'web', 'index.html')
h = open(p, encoding='utf-8').read()
def rep(a, b, n=1):
    global h
    assert h.count(a) == n, (a, h.count(a))
    h = h.replace(a, b)
rep("#modal a{color:var(--acc)}",
    "#modal a{color:var(--acc)}\n#notifBtn{position:relative}\n#notifBadge{display:inline-block;margin-left:6px;min-width:17px;height:17px;line-height:17px;border-radius:9px;background:var(--err);color:#1a0505;font-size:12px;font-weight:800;text-align:center}\n#notifBadge[hidden]{display:none}\n.nt{border-top:1px solid var(--line);padding:6px 0;font-size:13px;white-space:pre-wrap}.nt small{color:var(--muted);margin-right:8px}.nt.err{color:#ffb4b4}\n.nh{margin:12px 0 4px;font-weight:700}")
rep('<button class="btn sm" id="aboutBtn"',
    '<button class="btn sm" id="notifBtn" type="button"><span data-t="notif"></span><b id="notifBadge" hidden>!</b></button>\n  <button class="btn sm" id="aboutBtn"')
rep("hide: 'Hide'", "hide: 'Hide', notif: 'Notifications', notifMissing: 'Missing components', notifRecent: 'Recent messages', notifNone: 'Everything is fine – nothing to report.', notifClear: 'Clear messages'")
rep("hide: 'Elrejtés'", "hide: 'Elrejtés', notif: 'Értesítések', notifMissing: 'Hiányzó összetevők', notifRecent: 'Legutóbbi üzenetek', notifNone: 'Minden rendben – nincs jelenteni való.', notifClear: 'Üzenetek törlése'")
# remember every toast
rep("function toast(msg, kind) { const el",
    "let NOTES = [], NOTES_UNREAD = 0, MODAL_KIND = 'about';\n"
    "function updateNotif() { let miss = 0; try { miss = T ? findMissing().length : 0; } catch (_) {} const b = $('#notifBadge'); if (b) b.hidden = !(miss || NOTES_UNREAD); }\n"
    "function toast(msg, kind) { NOTES.unshift({t: new Date(), msg: String(msg), err: kind === 'err'}); if (NOTES.length > 60) NOTES.pop(); if (kind === 'err') NOTES_UNREAD++; updateNotif(); const el")
rep("function renderMissing() {\n  const box = $('#miss'); const m = findMissing();",
    "function renderMissing() {\n  const box = $('#miss'); const m = findMissing(); updateNotif();")
rep("function openAbout() { $('#modalTitle')", "function openAbout() { MODAL_KIND = 'about'; $('#modalTitle')")
rep("if ($('#modal').classList.contains('open')) openAbout(); }",
    "if ($('#modal').classList.contains('open')) { if (MODAL_KIND === 'notif') openNotif(); else openAbout(); } }\n  updateNotif();")
rep("function applyLang() {",
    "function openNotif() {\n"
    "  MODAL_KIND = 'notif'; NOTES_UNREAD = 0; updateNotif();\n"
    "  const m = T ? findMissing() : []; const body = $('#modalBody'); body.replaceChildren();\n"
    "  if (!m.length && !NOTES.length) body.append(h('p', {text: t('notifNone')}));\n"
    "  if (m.length) {\n"
    "    body.append(h('div', {class: 'nh', text: '! ' + t('missTitle')}));\n"
    "    m.forEach(x => body.append(h('div', {class: 'nt err', text: (x.kind === 'node' ? t('missNode', x.what) : t('missModel', x.what, x.folder)) + (x.step ? t('missFor', t(STEP_NAME[x.step] || x.step)) : t('missAlways'))})));\n"
    "    body.append(h('p', null, h('button', {class: 'btn sm', type: 'button', text: t('recheck'), onclick: async () => { await loadOI(); renderControls(); renderMissing(); openNotif(); }})));\n"
    "  }\n"
    "  if (NOTES.length) {\n"
    "    body.append(h('div', {class: 'nh', text: t('notifRecent')}));\n"
    "    NOTES.forEach(n => body.append(h('div', {class: 'nt' + (n.err ? ' err' : '')}, h('small', {text: n.t.toLocaleTimeString()}), n.msg)));\n"
    "    body.append(h('p', null, h('button', {class: 'btn sm', type: 'button', text: t('notifClear'), onclick: () => { NOTES = []; openNotif(); }})));\n"
    "  }\n"
    "  $('#modalTitle').textContent = t('notif'); $('#modal').classList.add('open');\n"
    "}\n"
    "function applyLang() {")
rep("$('#aboutBtn').onclick = openAbout;", "$('#aboutBtn').onclick = openAbout; $('#notifBtn').onclick = openNotif;")
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- model families (Z-Image Turbo / SDXL / Flux) + model downloader -------
h = open(p, encoding='utf-8').read()
rep("#notifBtn{position:relative}",
    "#notifBtn{position:relative}\n"
    ".fam{display:flex;flex:0 0 auto;border:1px solid var(--line2);border-radius:8px;overflow:hidden}\n"
    "header>button,header>label,header>.lang{flex:0 0 auto}\n"
    "@media (max-width:1700px){#connText{display:none}header .brand small{display:none}header{gap:8px;padding:0 12px}}\n"
    "@media (max-width:1250px){header .btn.sm{padding:5px 7px;font-size:12px}#byline{display:none}}\n"
    ".fam button{background:none;border:0;padding:7px 12px;cursor:pointer;font-size:13px;color:var(--muted);white-space:nowrap}\n"
    ".fam button.act{background:var(--acc);color:var(--accText);font-weight:700}\n"
    ".mdl{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 10px;align-items:center;border:1px solid var(--line);border-radius:9px;padding:9px 10px;background:var(--panel2)}\n"
    ".mdl.sel{border-color:var(--acc)}\n.mdl b{font-size:13.5px}\n.mdl .meta{grid-column:1/-1;font-size:12px;color:var(--muted)}\n"
    ".tagr{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:9px;background:var(--acc);color:var(--accText);font-size:11px;font-weight:700;vertical-align:1px}\n"
    ".pbar{grid-column:1/-1;height:6px;background:var(--line);border-radius:4px;overflow:hidden}.pbar i{display:block;height:100%;background:var(--acc)}")
rep('<div class="conn">', '<div class="fam" id="famTabs"></div>\n  <div class="conn">')
EN_ADD = ("famTitle: 'Base model', famHint: 'Best for', recommended: 'recommended', installedL: 'installed', selectM: 'Use', selectedM: 'in use', "
          "dlM: 'Download ({0})', dlCancel: 'Cancel', dlErr: 'Download failed: {0}', dlDone: 'Downloaded: {0}', dlRun: '{0} of {1} · {2}/s', "
          "ownModel: 'Model file in the folder', refreshM: 'Refresh', refreshedM: 'Model and LoRA lists refreshed.', famLoadErr: 'Could not load the {0} workflow: {1}', "
          "licenseL: 'Licence', manSteps: 'Steps (0 = by theme)', manCfg: 'CFG (0 = by theme)', clipSkip: 'CLIP skip', negHintX: 'Words the image should avoid', "
          "noModel: 'No base model for this family yet – download the recommended one above.', ")
HU_ADD = ("famTitle: 'Alapmodell', famHint: 'Mire a legjobb', recommended: 'ajánlott', installedL: 'telepítve', selectM: 'Használom', selectedM: 'használatban', "
          "dlM: 'Letöltés ({0})', dlCancel: 'Mégse', dlErr: 'A letöltés nem sikerült: {0}', dlDone: 'Letöltve: {0}', dlRun: '{0} / {1} · {2}/s', "
          "ownModel: 'Modellfájl a mappában', refreshM: 'Frissítés', refreshedM: 'A modell- és LoRA-lista frissítve.', famLoadErr: 'Nem sikerült betölteni a(z) {0} workflow-t: {1}', "
          "licenseL: 'Licenc', manSteps: 'Lépésszám (0 = a téma szerint)', manCfg: 'CFG (0 = a téma szerint)', clipSkip: 'CLIP skip', negHintX: 'Amit a kép kerüljön', "
          "noModel: 'Ehhez a családhoz még nincs alapmodell – töltsd le fent az ajánlottat.', ")
rep("hide: 'Hide', notif:", EN_ADD + "hide: 'Hide', notif:")
rep("hide: 'Elrejtés', notif:", HU_ADD + "hide: 'Elrejtés', notif:")
# generic LoRA list source (node 89 exists only in the Z-Image workflow)
rep("  const lsp = spec('89', 'lora_name'); const lopts = (lsp && lsp.options) || null;",
    "  const lopts = loraOpts();")
rep("  const sp = spec('89', 'lora_name'); const opts = (sp && sp.options) || []; const box = h('div', {class: 'loras'});",
    "  const opts = loraOpts() || []; const box = h('div', {class: 'loras'});")
rep("async function loadOI() {\n  const classes = [...new Set(Object.values(T.prompt).map(n => n.class_type))];",
    "function loraOpts() { const o = OI.LoraLoaderModelOnly; const s = o && o.input && o.input.required && o.input.required.lora_name; return s ? (Array.isArray(s[0]) ? s[0] : (s[1] && s[1].options) || []) : null; }\n"
    "async function loadOI() {\n  const classes = [...new Set([...Object.values(T.prompt).map(n => n.class_type), 'LoraLoaderModelOnly'])];")
# templates per family
rep("async function loadTemplate() {\n  const urls = [API + '/api/userdata/' + encodeURIComponent('artflow/template.json'), API + '/artflow/template.json'];",
    "const LS_FAM = 'artflow.studio.family'; let FAMILY = 'zimage', CAT = null, DLS = {}, DLTIMER = null;\n"
    "try { const f = localStorage.getItem(LS_FAM); if (f) FAMILY = f; } catch (_) {}\n"
    "const famInfo = f => (CAT && CAT.families && CAT.families[f]) || null;\n"
    "async function loadCatalog() { try { const r = await fetch(API + '/artflow/catalog', {cache: 'no-store'}); if (r.ok) { CAT = await r.json(); DLS = {}; CAT.models.forEach(m => { if (m.download) DLS[m.id] = m.download; }); } } catch (_) {} }\n"
    "async function loadTemplate() {\n  const fi = famInfo(FAMILY); const file = fi ? fi.template : 'template.json';\n"
    "  const urls = file === 'template.json' ? [API + '/api/userdata/' + encodeURIComponent('artflow/template.json'), API + '/artflow/template.json'] : [API + '/artflow/template/' + file];")
# model-name field of node 2 depends on the loader
rep("      field('2', 'unet_name', t('ckpt'), {pretty: true, onchange: again}), field('65', 'clip_name', t('clip'), {pretty: true, onchange: again}), field('66', 'vae_name', t('vae'), {pretty: true, onchange: again}),\n"
    "      h('div', {class: 'two'}, field('6', 'steps', t('steps')), field('6', 'cfg', t('cfg'))),",
    "      T.prompt['66'] ? field('65', 'clip_name', t('clip'), {pretty: true, onchange: again}) : null, field('66', 'vae_name', t('vae'), {pretty: true, onchange: again}),\n"
    "      T.prompt['123'] ? h('div', {class: 'two'}, field('123', 'value', t('manSteps'), {min: 0, max: 100, step: 1}), field('124', 'value', t('manCfg'), {min: 0, max: 20, step: 0.1, arrow: 0.5}))\n"
    "        : h('div', {class: 'two'}, field('6', 'steps', t('steps')), field('6', 'cfg', t('cfg'))),\n"
    "      field('120', 'stop_at_clip_layer', t('clipSkip'), {min: -4, max: -1, step: 1}),")
rep("      mini(t('neg'), field('51', 'value', t('negHint'), {rows: 3})),",
    "      mini(t('neg'), field('51', 'value', T.family === 'sdxl' ? t('negHintX') : t('negHint'), {rows: 3})),")
rep("    card('2', t('c2'), [baseLora(), h('div', {class: 'lab', text: t('moreLoras')}), loraList(S.loras)]),",
    "    card('2', t('c2'), [h('div', {class: 'row', style: 'justify-content:flex-end'}, refreshBtn()), baseLora(), h('div', {class: 'lab', text: t('moreLoras')}), loraList(S.loras)]),")
rep("  $('#colL').replaceChildren(\n    card('1', t('c1'), [",
    "  $('#colL').replaceChildren(\n    modelCard(),\n    card('1', t('c1'), [")
rep("    t('sumSize') + ': ' + (d.i2i === '1' ? t('sizeStart') : d.w + '×' + d.h) + '  ·  Shift: ' + d.shift,",
    "    t('sumSize') + ': ' + (d.i2i === '1' ? t('sizeStart') : d.w + '×' + d.h) + (d.cfg != null ? '  ·  ' + t('steps') + ': ' + d.base_steps + '  ·  CFG: ' + d.cfg : '  ·  Shift: ' + d.shift),")
# model card, downloads, family switch
rep("function renderControls() {",
    r"""const fmtB = n => { n = Number(n) || 0; return n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : (n / 1e6).toFixed(0) + ' MB'; };
function modelField() { const n = T.prompt['2']; return n && n.class_type === 'UNETLoader' ? 'unet_name' : 'ckpt_name'; }
function refreshBtn() { return h('button', {class: 'btn sm', type: 'button', text: '⟳ ' + t('refreshM'), onclick: async () => { await loadOI(); await loadCatalog(); renderControls(); toast(t('refreshedM')); }}); }
function applyModel(m) {
  setVal('2', modelField(), m.file); const s = m.settings || {};
  for (const id of ['6', '17', '25', '30', '62', '33']) if (T.prompt[id]) { if (s.sampler) setVal(id, 'sampler_name', s.sampler); if (s.scheduler) setVal(id, 'scheduler', s.scheduler); }
  if (T.prompt['120']) setVal('120', 'stop_at_clip_layer', s.clip_skip || -1);
  if (T.prompt['121']) setVal('121', 'string_a', s.prefix || ''); if (T.prompt['122']) setVal('122', 'string_a', s.neg_prefix || '');
  if (T.prompt['123']) setVal('123', 'value', s.steps || 0); if (T.prompt['124']) setVal('124', 'value', s.cfg || 0);
  if (s.theme && T.prompt['86']) setVal('86', 'choice', s.theme);
}
async function startDl(m) {
  try { await fetch(API + '/artflow/download', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: m.id})}); } catch (e) { toast(t('dlErr', e.message), 'err'); return; }
  DLS[m.id] = {state: 'running', done: 0, total: m.size}; pollDl(); renderControls();
}
async function cancelDl(m) { try { await fetch(API + '/artflow/download', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: m.id, cancel: true})}); } catch (_) {} }
function pollDl() {
  if (DLTIMER) return;
  DLTIMER = setInterval(async () => {
    let j = {}; try { j = await (await fetch(API + '/artflow/downloads', {cache: 'no-store'})).json(); } catch (_) { return; }
    let running = false, finished = [];
    for (const [id, st] of Object.entries(j)) { const old = DLS[id]; DLS[id] = st; if (st.state === 'running') running = true; if (old && old.state === 'running' && st.state !== 'running') finished.push([id, st]); }
    for (const [id, st] of finished) { const m = CAT.models.find(x => x.id === id); if (st.state === 'done') { toast(t('dlDone', m ? m.label : id)); } else if (st.state === 'error') toast(t('dlErr', st.error), 'err'); }
    if (finished.length) { await loadCatalog(); await loadOI(); renderControls(); }
    else { const box = $('#mdlList'); if (box) drawModels(box); }
    if (!running) { clearInterval(DLTIMER); DLTIMER = null; }
  }, 1500);
}
function drawModels(box) {
  box.replaceChildren(); if (!CAT) return;
  const cur = val('2', modelField()); const sp = spec('2', modelField()); const onDisk = (sp && sp.options) || [];
  const list = CAT.models.filter(m => m.family === FAMILY && m.kind === 'base');
  for (const m of list) {
    const st = DLS[m.id]; const running = st && st.state === 'running'; const have = onDisk.includes(m.file) || m.installed;
    const row = h('div', {class: 'mdl' + (cur === m.file ? ' sel' : '')});
    row.append(h('div', null, h('b', {text: m.label}), m.recommended ? h('span', {class: 'tagr', text: t('recommended')}) : null));
    if (running) row.append(h('button', {class: 'btn sm', type: 'button', text: t('dlCancel'), onclick: () => cancelDl(m)}));
    else if (have) row.append(cur === m.file ? h('span', {class: 'muted', text: '✓ ' + t('selectedM')}) : h('button', {class: 'btn sm', type: 'button', text: t('selectM'), onclick: () => { applyModel(m); renderControls(); }}));
    else row.append(h('button', {class: 'btn sm', type: 'button', text: '⤓ ' + t('dlM', fmtB(m.size)), onclick: () => startDl(m)}));
    row.append(h('div', {class: 'meta', text: (m['note_' + LANG] || m.note_en || '') + '  ·  ' + t('licenseL') + ': ' + (m.license || '?')}));
    if (running) { const f = st.total ? st.done / st.total : 0; row.append(h('div', {class: 'pbar'}, h('i', {style: 'width:' + (f * 100).toFixed(1) + '%'})), h('div', {class: 'meta', text: t('dlRun', fmtB(st.done), fmtB(st.total), fmtB(st.speed || 0))})); }
    else if (st && st.state === 'error') row.append(h('div', {class: 'meta', style: 'color:var(--err)', text: t('dlErr', st.error)}));
    box.append(row);
  }
  const known = new Set(CAT.models.map(m => m.file)); const own = onDisk.filter(x => !known.has(x));
  if (own.length || (cur && !known.has(cur))) box.append(field('2', modelField(), t('ownModel'), {pretty: true, onchange: () => renderControls()}));
  if (!onDisk.length) box.append(h('div', {class: 'note', text: t('noModel')}));
}
function modelCard() {
  const fi = famInfo(FAMILY); const box = h('div', {id: 'mdlList', style: 'display:flex;flex-direction:column;gap:8px'}); drawModels(box);
  return card('0', t('famTitle') + (fi ? ' – ' + fi.label : ''), [
    fi ? h('div', {class: 'muted', text: t('famHint') + ': ' + (fi['best_' + LANG] || fi.best_en || '')}) : null, box,
    h('div', {class: 'row', style: 'justify-content:flex-end'}, refreshBtn())]);
}
function renderFamTabs() {
  const box = $('#famTabs'); if (!box) return; box.replaceChildren();
  const fams = CAT && CAT.families ? Object.entries(CAT.families) : [['zimage', {label: 'Z-Image Turbo'}]];
  box.hidden = fams.length < 2;
  for (const [k, f] of fams) box.append(h('button', {type: 'button', class: k === FAMILY ? 'act' : '', text: f.label, title: f['best_' + LANG] || f.best_en || '', onclick: () => switchFamily(k)}));
}
async function initTemplate() {
  T = await loadTemplate(); NODEGROUP = {}; for (const [k, g] of Object.entries(T.groups)) for (const id of g.nodes) NODEGROUP[String(id)] = k;
  await loadOI(); S = {groups: {}, vals: {}, loras: null, footLoras: null, seedRandom: true, seed: 1, runs: 1}; loadState();
  // first use of a family: select its recommended model if it is on disk
  const fi = famInfo(FAMILY); if (fi && CAT && !Object.keys(S.vals).some(k => k.startsWith('2.'))) { const m = CAT.models.find(x => x.id === fi.default); if (m) applyModel(m); }
}
async function switchFamily(f) {
  if (f === FAMILY) return; const prev = FAMILY; FAMILY = f;
  try { await initTemplate(); } catch (e) { toast(t('famLoadErr', (famInfo(f) || {}).label || f, e.message), 'err'); FAMILY = prev; await initTemplate(); }
  try { localStorage.setItem(LS_FAM, FAMILY); } catch (_) {}
  renderFamTabs(); renderControls(); renderTexts(); if ($('#drawer').classList.contains('open')) renderAdvanced();
}
function renderControls() {""")
rep("  if (T) { renderControls(); renderSteps();", "  renderFamTabs();\n  if (T) { renderControls(); renderSteps();")
rep("    T = await loadTemplate(); NODEGROUP = {}; for (const [k, g] of Object.entries(T.groups)) for (const id of g.nodes) NODEGROUP[String(id)] = k;\n    await loadOI(); loadState();",
    "    await loadCatalog(); if (!famInfo(FAMILY)) FAMILY = 'zimage';\n"
    "    try { await initTemplate(); } catch (e) { if (FAMILY === 'zimage') throw e; FAMILY = 'zimage'; await initTemplate(); }\n"
    "    if (Object.values(DLS).some(d => d.state === 'running')) pollDl();")
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- saved workflows (new / save / open) + version 1.1.0 ---------------------
h = open(p, encoding='utf-8').read()
rep("const VERSION = '1.0.0';", "const VERSION = '1.1.0';")
rep('<button class="btn sm" id="notifBtn"', '<button class="btn sm" id="wfBtn" type="button" data-t="wf"></button>\n  <button class="btn sm" id="notifBtn"')
rep(".nh{margin:12px 0 4px;font-weight:700}",
    ".nh{margin:12px 0 4px;font-weight:700}\n.wfrow{display:flex;gap:8px;align-items:center;border-top:1px solid var(--line);padding:7px 0}.wfrow span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}\n.wfsave{display:flex;gap:8px}.wfsave input{flex:1}")
rep("famTitle: 'Base model',",
    "wf: 'Workflows', wfNew: 'New workflow (empty settings)', wfNewHint: 'Keeps the base model and the language, everything else goes back to the defaults.', wfSave: 'Save', wfName: 'Name of this setup', "
    "wfSaved: 'Saved: {0}', wfOpen: 'Open', wfDel: 'Delete', wfDelSure: 'Sure?', wfList: 'Saved setups', wfNone: 'Nothing saved yet.', wfOpened: 'Opened: {0}', wfErr: 'Could not do it: {0}', wfNewDone: 'New, empty workflow.', "
    "famTitle: 'Base model',")
rep("famTitle: 'Alapmodell',",
    "wf: 'Munkafolyamatok', wfNew: 'Új munkafolyamat (üres beállítások)', wfNewHint: 'Az alapmodell és a nyelv marad, minden más visszaáll alapállapotba.', wfSave: 'Mentés', wfName: 'A beállítás neve', "
    "wfSaved: 'Elmentve: {0}', wfOpen: 'Megnyitás', wfDel: 'Törlés', wfDelSure: 'Biztos?', wfList: 'Elmentett beállítások', wfNone: 'Még nincs elmentett beállítás.', wfOpened: 'Megnyitva: {0}', wfErr: 'Nem sikerült: {0}', wfNewDone: 'Új, üres munkafolyamat.', "
    "famTitle: 'Alapmodell',")
rep("function openNotif() {",
    r"""const WF_DIR = 'artflow/presets';
const ufile = n => API + '/api/userdata/' + encodeURIComponent(WF_DIR + '/' + n);
async function wfList() { try { const r = await fetch(API + '/api/userdata?dir=' + encodeURIComponent(WF_DIR), {cache: 'no-store'}); if (!r.ok) return []; const j = await r.json(); return (Array.isArray(j) ? j : []).filter(x => typeof x === 'string' && /\.json$/i.test(x)).sort(); } catch (_) { return []; } }
async function wfSave(name) {
  name = String(name || '').trim().replace(/[\\/:*?"<>|]+/g, '_').slice(0, 80); if (!name) return;
  const data = {app: 'ArtFlow Studio', version: VERSION, family: FAMILY, template: T.id, saved: new Date().toISOString(), state: S};
  const r = await fetch(ufile(name + '.json') + '?overwrite=true', {method: 'POST', body: JSON.stringify(data, null, 1)});
  if (!r.ok) throw new Error('HTTP ' + r.status); toast(t('wfSaved', name));
}
async function wfOpen(file) {
  const r = await fetch(ufile(file), {cache: 'no-store'}); if (!r.ok) throw new Error('HTTP ' + r.status); const d = await r.json();
  if (d.family && d.family !== FAMILY && famInfo(d.family)) { FAMILY = d.family; try { localStorage.setItem(LS_FAM, FAMILY); } catch (_) {} await initTemplate(); renderFamTabs(); }
  const st = d.state || {}; S = Object.assign({groups: {}, vals: {}, loras: [], footLoras: [], seedRandom: true, seed: 1, runs: 1}, st);
  for (const k of Object.keys(S.vals)) { const i = k.indexOf('.'); if (!T.prompt[k.slice(0, i)]) delete S.vals[k]; }
  for (const k of Object.keys(T.groups)) if (typeof S.groups[k] !== 'boolean') S.groups[k] = !!T.groups[k].on;
  save(); renderControls(); toast(t('wfOpened', file.replace(/\.json$/i, '')));
}
async function wfNew() {
  const mf = modelField(); const keep = val('2', mf); const m = CAT && CAT.models.find(x => x.file === keep);
  S = {groups: {}, vals: {}, loras: null, footLoras: null, seedRandom: true, seed: 1, runs: 1};
  try { localStorage.removeItem(LS_KEY); } catch (_) {} loadState();
  if (m) applyModel(m); else if (keep) setVal('2', mf, keep);
  save(); renderControls(); toast(t('wfNewDone'));
}
async function openWf() {
  MODAL_KIND = 'wf'; const body = $('#modalBody'); body.replaceChildren(); $('#modalTitle').textContent = t('wf'); $('#modal').classList.add('open');
  const name = h('input', {type: 'text', placeholder: t('wfName')});
  const err = e => toast(t('wfErr', e.message), 'err');
  body.append(
    h('p', null, h('button', {class: 'btn sm', type: 'button', text: t('wfNew'), onclick: () => { wfNew().then(() => $('#modal').classList.remove('open'), err); }}), ' ', h('span', {class: 'muted', text: t('wfNewHint')})),
    h('div', {class: 'nh', text: t('wfSave')}),
    h('div', {class: 'wfsave'}, name, h('button', {class: 'btn sm', type: 'button', text: t('wfSave'), onclick: () => { wfSave(name.value).then(openWf, err); }})),
    h('div', {class: 'nh', text: t('wfList')}));
  const files = await wfList(); if (!files.length) body.append(h('p', {class: 'muted', text: t('wfNone')}));
  for (const f of files) {
    let armed = false; const del = h('button', {class: 'btn sm', type: 'button', text: t('wfDel')});
    del.onclick = async () => { if (!armed) { armed = true; del.textContent = t('wfDelSure'); return; } try { await fetch(ufile(f), {method: 'DELETE'}); } catch (_) {} openWf(); };
    body.append(h('div', {class: 'wfrow'}, h('span', {text: f.replace(/\.json$/i, '')}),
      h('button', {class: 'btn sm', type: 'button', text: t('wfOpen'), onclick: () => { wfOpen(f).then(() => $('#modal').classList.remove('open'), err); }}), del));
  }
}
function openNotif() {""")
rep("$('#notifBtn').onclick = openNotif;", "$('#notifBtn').onclick = openNotif; $('#wfBtn').onclick = openWf;")
rep("{ if (MODAL_KIND === 'notif') openNotif(); else openAbout(); }", "{ if (MODAL_KIND === 'notif') openNotif(); else if (MODAL_KIND === 'wf') openWf(); else openAbout(); }")
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- About: models of the new families ---------------------------------------
h = open(p, encoding='utf-8').read()
rep("<li><b>Z-Image Turbo</b> model – Tongyi-MAI (Alibaba)</li>",
    "<li><b>Z-Image Turbo</b> model – Tongyi-MAI (Alibaba)</li>\n"
    "<li><b>Juggernaut XL v9</b> (SDXL family, downloaded when you choose it) – RunDiffusion / KandooAI, CreativeML Open RAIL-M</li>\n"
    "<li><b>RealVisXL V5.0</b> (optional) – SG161222, OpenRAIL++</li>\n"
    "<li><b>Pony Diffusion V6 XL</b> (optional) – PurpleSmartAI; its licence does not allow monetised inference</li>\n"
    "<li><b>FLUX.1 [schnell]</b> (Flux family, downloaded when you choose it) – Black Forest Labs, Apache-2.0; fp8 package by Comfy-Org</li>")
rep("<li><b>Z-Image Turbo</b> modell – Tongyi-MAI (Alibaba)</li>",
    "<li><b>Z-Image Turbo</b> modell – Tongyi-MAI (Alibaba)</li>\n"
    "<li><b>Juggernaut XL v9</b> (SDXL család, kiválasztáskor töltődik le) – RunDiffusion / KandooAI, CreativeML Open RAIL-M</li>\n"
    "<li><b>RealVisXL V5.0</b> (opcionális) – SG161222, OpenRAIL++</li>\n"
    "<li><b>Pony Diffusion V6 XL</b> (opcionális) – PurpleSmartAI; a licence nem engedi a pénzért nyújtott (monetizált) futtatást</li>\n"
    "<li><b>FLUX.1 [schnell]</b> (Flux család, kiválasztáskor töltődik le) – Black Forest Labs, Apache-2.0; fp8 csomag: Comfy-Org</li>")
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- Civitai/A1111-compatible metadata via Image Saver + image info window ---
h = open(p, encoding='utf-8').read()
rep("  return out;\n}\nconst rndSeed", "  saverNode(out, seed);\n  return out;\n}\nconst rndSeed")
rep("function buildPrompt(seed) {",
    r"""function shortName() {
  const f = val('2', modelField()); const m = CAT && CAT.models.find(x => x.file === f); if (m && m.short) return m.short;
  const fi = famInfo(FAMILY); return (fi && fi.short) || FAMILY.toUpperCase();
}
function themeLora() {
  if (!T.prompt['89'] || !val('100', 'value')) return null;
  if (val('92', 'value')) return Number(val('94', 'float')) || 0;
  const code = String(val('88', 'code') || ''); const th = String(val('86', 'choice') || '');
  const i = code.indexOf(JSON.stringify(th) + ':'); if (i < 0) return null; const mm = /"lora":\s*([0-9.]+)/.exec(code.slice(i, i + 400)); return mm ? Number(mm[1]) : null;
}
function saverNode(out, seed) {
  // swap the plain SaveImage for Image Saver: writes A1111/Civitai "parameters" (prompt, model + hash, LoRAs, sampler…) into the PNG
  const sv = out['35']; if (!sv || sv.class_type !== 'SaveImage') return;
  const user = String(sv.inputs.filename_prefix || 'ArtFlow').replace(/[\\/:*?"<>|]+/g, '_');
  if (!OI['Image Saver']) { sv.inputs.filename_prefix = user + '_' + shortName(); return; }
  const k = out['6'] && out['6'].inputs; if (!k) { sv.inputs.filename_prefix = user + '_' + shortName(); return; }
  const lat = out['70'] && out['70'].inputs; const ld = out['2'] && out['2'].inputs || {};
  const strip = n => String(n).replace(/\.(safetensors|ckpt|pt|pth|sft|gguf)$/i, '');
  const tags = []; const bl = themeLora(); if (bl && out['89']) tags.push('<lora:' + strip(out['89'].inputs.lora_name) + ':' + bl + '>');
  (S.loras || []).forEach(L => { if (L.on && L.lora) tags.push('<lora:' + strip(L.lora) + ':' + (Number(L.strength) || 0) + '>'); });
  const pos = out['3'] && out['3'].inputs.text; const neg = out['4'] && out['4'].inputs.text;
  out['130'] = {class_type: 'StringConcatenate', inputs: {string_a: pos || '', string_b: tags.join(' '), delimiter: tags.length ? ' ' : ''}, _meta: {title: 'Metadata prompt (+ LoRA tags)'}};
  const cs = out['120'] ? Number(out['120'].inputs.stop_at_clip_layer) : -1;
  out['35'] = {class_type: 'Image Saver', _meta: sv._meta, inputs: {
    images: sv.inputs.images, filename: user + '_' + shortName() + '_%time_%seed', path: '', extension: 'png',
    steps: k.steps, cfg: k.cfg, modelname: ld.ckpt_name || ld.unet_name || '', sampler_name: k.sampler_name, scheduler_name: k.scheduler,
    positive: ['130', 0], negative: neg || '', seed_value: k.seed, width: lat ? lat.width : 1024, height: lat ? lat.height : 1024,
    lossless_webp: true, quality_jpeg_or_webp: 100, optimize_png: false, counter: 0, denoise: k.denoise, clip_skip: cs <= -2 ? -cs : 0,
    time_format: '%Y-%m-%d-%H%M%S', save_workflow_as_json: false, embed_workflow: true, additional_hashes: '', download_civitai_data: false,
    easy_remix: true, show_preview: true, custom: ('Studio: ArtFlow Studio ' + VERSION + ', Family: ' + ((famInfo(FAMILY) || {}).label || FAMILY) + ', Theme: ' + String(val('86', 'choice') || '')).replace(/[\u2013\u2014]/g, '-').replace(/[^\x20-\x7e]/g, '')}};
}
function buildPrompt(seed) {""")
rep("async function loadOI() {\n  const classes = [...new Set([...Object.values(T.prompt).map(n => n.class_type), 'LoraLoaderModelOnly'])];",
    "async function loadOI() {\n  const classes = [...new Set([...Object.values(T.prompt).map(n => n.class_type), 'LoraLoaderModelOnly', 'Image Saver', 'Image Saver Simple'])];")
# ---------- image info window ----------
rep('<div class="fam" id="famTabs"></div>', '<div class="fam" id="famTabs"></div>\n  <button class="btn sm" id="infoBtn" type="button" data-t="imgInfo"></button>')
rep("wf: 'Workflows',",
    "imgInfo: 'ⓘ Image info', iiDrop: 'Drop an image here (PNG from ComfyUI, A1111, Civitai…) or click to choose one', iiHist: 'or pick one of your recent images:', iiNone: 'No generation data was found in this image (many sites strip it on upload).', "
    "iiFam: 'Model family', iiModel: 'Model', iiHash: 'Model hash', iiPos: 'Prompt', iiNeg: 'Negative prompt', iiLoras: 'LoRAs', iiParams: 'Parameters', iiFormat: 'Format', iiUsePrompt: 'Use the prompt', iiUseSeed: 'Use the seed', iiUsed: 'Taken over into the Studio.', iiRaw: 'Raw data', iiErr: 'Could not read the image: {0}', "
    "wf: 'Workflows',")
rep("wf: 'Munkafolyamatok',",
    "imgInfo: 'ⓘ Képinfó', iiDrop: 'Húzz ide egy képet (ComfyUI, A1111, Civitai PNG…), vagy kattints a kiválasztáshoz', iiHist: 'vagy válassz a legutóbbi képeid közül:', iiNone: 'Ebben a képben nincs generálási adat (sok oldal feltöltéskor törli).', "
    "iiFam: 'Modellcsalád', iiModel: 'Modell', iiHash: 'Modell hash', iiPos: 'Prompt', iiNeg: 'Negatív prompt', iiLoras: 'LoRA-k', iiParams: 'Paraméterek', iiFormat: 'Formátum', iiUsePrompt: 'Prompt átvétele', iiUseSeed: 'Seed átvétele', iiUsed: 'Átvéve a Studióba.', iiRaw: 'Nyers adat', iiErr: 'Nem sikerült beolvasni a képet: {0}', "
    "wf: 'Munkafolyamatok',")
rep(".wfsave{display:flex;gap:8px}.wfsave input{flex:1}",
    ".wfsave{display:flex;gap:8px}.wfsave input{flex:1}\n.iidrop{border:2px dashed var(--line2);border-radius:10px;padding:22px;text-align:center;color:var(--muted);cursor:pointer}.iidrop.over{border-color:var(--acc)}\n"
    ".iih{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.iih img{width:58px;height:58px;object-fit:cover;border-radius:6px;cursor:pointer;border:1px solid var(--line2)}\n"
    ".iit{width:100%;border-collapse:collapse;font-size:13px}.iit td{border-top:1px solid var(--line);padding:5px 6px;vertical-align:top}.iit td:first-child{color:var(--muted);white-space:nowrap;width:1%}.iit pre{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.45 ui-monospace,Consolas,monospace}\n"
    ".iiprev{display:flex;gap:12px;align-items:flex-start}.iiprev img{max-width:160px;max-height:200px;border-radius:8px}")
rep("function openNotif() {",
    r"""/* ---------- image info: reads PNG text chunks (A1111/Civitai "parameters", ComfyUI "prompt"/"workflow") ---------- */
async function inflate(u8) { const ds = new DecompressionStream('deflate'); const s = new Blob([u8]).stream().pipeThrough(ds); return new Uint8Array(await new Response(s).arrayBuffer()); }
async function readMeta(buf) {
  const u8 = new Uint8Array(buf); const out = {}; const lat = b => { let s = ''; for (const c of b) s += String.fromCharCode(c); return s; }; const utf = b => new TextDecoder('utf-8').decode(b);
  if (u8[0] === 0x89 && u8[1] === 0x50) {
    const dv = new DataView(buf); let p = 8;
    while (p + 8 <= u8.length) {
      const len = dv.getUint32(p); const type = lat(u8.subarray(p + 4, p + 8)); const d = u8.subarray(p + 8, p + 8 + len); p += 12 + len;
      if (type === 'tEXt') { const z = d.indexOf(0); out[lat(d.subarray(0, z))] = utf(d.subarray(z + 1)); }
      else if (type === 'zTXt') { const z = d.indexOf(0); try { out[lat(d.subarray(0, z))] = utf(await inflate(d.subarray(z + 2))); } catch (_) {} }
      else if (type === 'iTXt') { const z = d.indexOf(0); const key = lat(d.subarray(0, z)); const comp = d[z + 1]; let q = z + 3; q = d.indexOf(0, q) + 1; q = d.indexOf(0, q) + 1; const body = d.subarray(q); try { out[key] = utf(comp ? await inflate(body) : body); } catch (_) {} }
      if (type === 'IEND') break;
    }
  } else {
    // JPEG / WebP: A1111-style text is usually in EXIF UserComment (often UTF-16) – search for it
    const t8 = lat(u8); let i = t8.indexOf('Steps: ');
    if (i >= 0) { let s = t8.lastIndexOf('\u0000', i); out.parameters = utf(u8.subarray(s + 1, t8.indexOf('\u0000', i) > 0 ? t8.indexOf('\u0000', i) : u8.length)); }
    else { const t16 = new TextDecoder('utf-16be').decode(u8.subarray(0, Math.min(u8.length, 400000))); const t16l = new TextDecoder('utf-16le').decode(u8.subarray(0, Math.min(u8.length, 400000)));
      for (const tt of [t16, t16l]) { const j = tt.indexOf('Steps: '); if (j >= 0) { const a = tt.lastIndexOf('\u0000', j) + 1; const b = tt.indexOf('\u0000', j); out.parameters = tt.slice(a, b > 0 ? b : undefined).replace(/^UNICODE/, ''); break; } } }
  }
  return out;
}
function parseA1111(txt) {
  const r = {pos: '', neg: '', params: {}, loras: []}; let s = String(txt).replace(/\r/g, '');
  const li = s.lastIndexOf('\nSteps: '); let tail = ''; if (li >= 0) { tail = s.slice(li + 1); s = s.slice(0, li); } else if (s.startsWith('Steps: ')) { tail = s; s = ''; }
  const ni = s.indexOf('\nNegative prompt:'); if (ni >= 0) { r.pos = s.slice(0, ni).trim(); r.neg = s.slice(ni + 17).trim(); } else r.pos = s.trim();
  const re = /\s*([^:,]+):\s*("(?:[^"\\]|\\.)*"|[^,]*)(?:,|$)/g; let m; while ((m = re.exec(tail)) && m[0]) { let v = m[2].trim(); if (v.startsWith('"')) { try { v = JSON.parse(v); } catch (_) {} } r.params[m[1].trim()] = v; }
  const lr = /<lora:([^:>]+):?([0-9.\-]*)[^>]*>/g; while ((m = lr.exec(r.pos))) r.loras.push(m[1] + (m[2] ? ' · ' + m[2] : ''));
  if (r.params['Lora hashes']) String(r.params['Lora hashes']).split(',').forEach(x => { const n = x.split(':')[0].trim(); if (n && !r.loras.some(y => y.startsWith(n))) r.loras.push(n); });
  return r;
}
function parseComfy(js) {
  let P; try { P = typeof js === 'string' ? JSON.parse(js) : js; } catch (_) { return null; } if (!P || typeof P !== 'object') return null;
  const r = {pos: '', neg: '', params: {}, loras: [], model: ''}; const txt = (ref, d) => { if (typeof ref === 'string') return ref; if (!Array.isArray(ref) || (d || 0) > 12) return ''; const n = P[ref[0]]; if (!n) return ''; const I = n.inputs || {};
    for (const k of ['text', 'value', 'string', 'text_g', 'prompt', 'string_a']) if (k in I) { const v = txt(I[k], (d || 0) + 1); if (v) return v + (k === 'string_a' && I.string_b && typeof I.string_b === 'string' ? (I.delimiter || '') + I.string_b : ''); } return ''; };
  for (const n of Object.values(P)) { const I = n.inputs || {}; const c = n.class_type || '';
    if (/CheckpointLoader|UNETLoader|UnetLoader/i.test(c)) r.model = r.model || I.ckpt_name || I.unet_name || '';
    if (/^KSampler/.test(c) && !r.params.Steps) { Object.assign(r.params, {Steps: I.steps, Sampler: I.sampler_name, Scheduler: I.scheduler, 'CFG scale': I.cfg, Seed: Array.isArray(I.seed) ? '(linked)' : I.seed, Denoise: I.denoise}); r.pos = txt(I.positive && P[I.positive[0]] ? P[I.positive[0]].inputs.text : ''); r.neg = txt(I.negative && P[I.negative[0]] ? P[I.negative[0]].inputs.text : ''); }
    if (/Lora/i.test(c)) { if (I.lora_name) r.loras.push(I.lora_name + ' · ' + (typeof I.strength_model === 'number' ? I.strength_model : '')); for (const [k, v] of Object.entries(I)) if (/^lora_\d+$/.test(k) && v && v.lora && v.on) r.loras.push(v.lora + ' · ' + v.strength); }
    if (/^Empty.*Latent/.test(c) && typeof I.width === 'number') r.params.Size = I.width + 'x' + I.height; }
  for (const k of Object.keys(r.params)) if (r.params[k] == null || Array.isArray(r.params[k])) delete r.params[k];
  return r;
}
function guessFamily(model) {
  const m = String(model || '').toLowerCase(); const c = CAT && CAT.models.find(x => x.file.toLowerCase().startsWith(m.replace(/\.(safetensors|ckpt)$/, '')) || m.startsWith(x.file.toLowerCase().replace(/\.safetensors$/, '')));
  if (c) return famInfo(c.family) ? famInfo(c.family).label + ' – ' + c.label : c.label;
  if (/pony/.test(m)) return 'SDXL – Pony'; if (/flux/.test(m)) return 'Flux'; if (/z[_-]?image|zimage|zit/.test(m)) return 'Z-Image'; if (/xl|sdxl|illustrious|noob/.test(m)) return 'SDXL'; if (/sd15|1\.5|v1-5/.test(m)) return 'SD 1.5'; return '?';
}
function showInfo(meta, url) {
  const box = $('#iiOut'); box.replaceChildren(); let r = null, fmt = '';
  if (meta.parameters) { r = parseA1111(meta.parameters); fmt = 'A1111 / Civitai (parameters)'; r.model = r.params.Model || ''; }
  const cf = meta.prompt ? parseComfy(meta.prompt) : null;
  if (cf) { if (!r) { r = cf; fmt = 'ComfyUI (prompt)'; } else { fmt += ' + ComfyUI'; if (!r.model) r.model = cf.model; } }
  if (!r) { box.append(h('p', {class: 'muted', text: t('iiNone')})); return; }
  const rows = [[t('iiFormat'), fmt], [t('iiFam'), guessFamily(r.model)], [t('iiModel'), r.model], [t('iiHash'), r.params['Model hash'] || ''], [t('iiPos'), r.pos], [t('iiNeg'), r.neg], [t('iiLoras'), r.loras.join('\n')],
    [t('iiParams'), Object.entries(r.params).filter(([k]) => !['Model', 'Model hash', 'Lora hashes', 'Hashes', 'Version'].includes(k)).map(([k, v]) => k + ': ' + v).join('\n')]].filter(x => x[1]);
  const tb = h('table', {class: 'iit'}); rows.forEach(([k, v]) => tb.append(h('tr', null, h('td', {text: k}), h('td', null, h('pre', {text: String(v)})))));
  const seed = Number(r.params.Seed);
  box.append(h('div', {class: 'iiprev'}, url ? h('img', {src: url, alt: ''}) : null, h('div', {style: 'flex:1;min-width:0'}, tb)),
    h('p', null, r.pos ? h('button', {class: 'btn sm', type: 'button', text: t('iiUsePrompt'), onclick: () => { setVal('46', 'value', r.pos.replace(/<lora:[^>]+>/g, '').trim()); if (r.neg != null) setVal('51', 'value', r.neg); renderControls(); toast(t('iiUsed')); }}) : null, ' ',
      isFinite(seed) && seed > 0 ? h('button', {class: 'btn sm', type: 'button', text: t('iiUseSeed'), onclick: () => { S.seed = seed; S.seedRandom = false; save(); renderControls(); toast(t('iiUsed')); }}) : null),
    mini(t('iiRaw'), h('pre', {style: 'white-space:pre-wrap;word-break:break-word;font-size:11px;max-height:240px;overflow:auto', text: Object.entries(meta).map(([k, v]) => k + ':\n' + String(v).slice(0, 6000)).join('\n\n')})));
}
async function infoFrom(blob) { try { const url = URL.createObjectURL(blob); showInfo(await readMeta(await blob.arrayBuffer()), url); } catch (e) { toast(t('iiErr', e.message), 'err'); } }
function openInfo() {
  MODAL_KIND = 'info'; const body = $('#modalBody'); body.replaceChildren(); $('#modalTitle').textContent = t('imgInfo'); $('#modal').classList.add('open');
  const file = h('input', {type: 'file', accept: 'image/*', hidden: true}); file.onchange = () => { if (file.files[0]) infoFrom(file.files[0]); file.value = ''; };
  const drop = h('div', {class: 'iidrop', text: t('iiDrop')}); drop.onclick = () => file.click();
  drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); }; drop.ondragleave = () => drop.classList.remove('over');
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over'); const f = e.dataTransfer.files[0]; if (f) infoFrom(f); };
  const hist = h('div', {class: 'iih'}); H.slice(0, 16).forEach(x => { const i = h('img', {src: x.url, alt: ''}); i.onclick = async () => { try { infoFrom(await (await fetch(x.url)).blob()); } catch (e) { toast(t('iiErr', e.message), 'err'); } }; hist.append(i); });
  body.append(...[drop, file, H.length ? h('div', {class: 'muted', style: 'margin-top:8px', text: t('iiHist')}) : null, hist, h('div', {id: 'iiOut'})].filter(Boolean));
}
function openNotif() {""")
rep("$('#notifBtn').onclick = openNotif; $('#wfBtn').onclick = openWf;", "$('#notifBtn').onclick = openNotif; $('#wfBtn').onclick = openWf; $('#infoBtn').onclick = openInfo;")
rep("else if (MODAL_KIND === 'wf') openWf(); else openAbout(); }", "else if (MODAL_KIND === 'wf') openWf(); else if (MODAL_KIND === 'info') openInfo(); else openAbout(); }")
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- shorter file names with a persistent counter -----------------------------
h = open(p, encoding='utf-8').read()
rep("function buildPrompt(seed) {\n  const full", "function buildPrompt(seed, cnt) {\n  const full")
rep("  saverNode(out, seed);\n  return out;", "  saverNode(out, seed, cnt);\n  return out;")
rep("function saverNode(out, seed) {", r"""const CNT_URL = () => API + '/api/userdata/' + encodeURIComponent('artflow/counter.json');
async function nextCounter() {
  // kept in ComfyUI's user folder, so deleting images never restarts the numbering; a fresh install starts at 1
  let n = 0; try { const r = await fetch(CNT_URL(), {cache: 'no-store'}); if (r.ok) n = Number((await r.json()).n) || 0; } catch (_) {}
  n += 1; try { await fetch(CNT_URL() + '?overwrite=true', {method: 'POST', body: JSON.stringify({n})}); } catch (_) {} return n;
}
function saverNode(out, seed, cnt) {""")
rep(r"""  const user = String(sv.inputs.filename_prefix || 'ArtFlow').replace(/[\\/:*?"<>|]+/g, '_');""",
    r"""  const up = String(sv.inputs.filename_prefix || '').replace(/[\\/:*?"<>|]+/g, '_').trim(); const user = (!up || /^artflow$/i.test(up)) ? '' : up + '_';""" + "\n"
    "  const num = cnt ? String(cnt).padStart(5, '0') : '%seed';")
rep("if (!OI['Image Saver']) { sv.inputs.filename_prefix = user + '_' + shortName(); return; }", "if (!OI['Image Saver']) { sv.inputs.filename_prefix = user + shortName(); return; }")
rep("if (!k) { sv.inputs.filename_prefix = user + '_' + shortName(); return; }", "if (!k) { sv.inputs.filename_prefix = user + shortName(); return; }")
rep("images: sv.inputs.images, filename: user + '_' + shortName() + '_%time_%seed', path: '', extension: 'png',",
    "images: sv.inputs.images, filename: user + shortName() + '_%time_' + num, path: '', extension: 'png',")
rep("time_format: '%Y-%m-%d-%H%M%S',", "time_format: '%Y-%m-%d',")
rep("    try { prompt = buildPrompt(seed); }", "    const cnt = await nextCounter();\n    try { prompt = buildPrompt(seed, cnt); }")
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- separate Save card: file-name tags + metadata switch ---------------------
h = open(p, encoding='utf-8').read()
rep("        h('div', {class: 'two'}, field('33', 'upscale_by', t('upBy'), {min: 1, max: 4, step: 0.05, arrow: 0.25}), field('33', 'steps', t('steps')))]),\n"
    "      groupCard('5', [field('35', 'filename_prefix', t('prefix'))])\n    ])\n  );",
    "        h('div', {class: 'two'}, field('33', 'upscale_by', t('upBy'), {min: 1, max: 4, step: 0.05, arrow: 0.25}), field('33', 'steps', t('steps')))])\n    ]),\n"
    "    saveCard()\n  );")
rep("function renderControls() {",
    r"""const SAVE_TAGS = ['prefix', 'model', 'theme', 'date', 'time', 'seed', 'counter'];
function saveCfg() {
  if (!S.save || typeof S.save !== 'object') S.save = {};
  const d = {meta: true, prefix: '', tags: {prefix: true, model: true, theme: false, date: true, time: false, seed: false, counter: true}};
  if (typeof S.save.meta !== 'boolean') S.save.meta = d.meta; if (typeof S.save.prefix !== 'string') S.save.prefix = d.prefix;
  S.save.tags = Object.assign({}, d.tags, S.save.tags || {}); return S.save;
}
const slug = x => String(x || '').normalize('NFKD').replace(/[^\x20-\x7e]/g, '').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
function fileName(seed, cnt) {
  const c = saveCfg(), tg = c.tags, now = new Date(), p2 = n => String(n).padStart(2, '0'); const parts = [];
  if (tg.prefix && c.prefix.trim()) parts.push(slug(c.prefix));
  if (tg.model) parts.push(shortName());
  if (tg.theme) { const th = String(val('86', 'choice') || ''); if (th && !/^None/.test(th)) parts.push(slug(th.split(/\s+[–-]\s+/)[0])); }
  if (tg.date) parts.push(now.getFullYear() + '-' + p2(now.getMonth() + 1) + '-' + p2(now.getDate()));
  if (tg.time) parts.push(p2(now.getHours()) + p2(now.getMinutes()) + p2(now.getSeconds()));
  if (tg.seed && seed != null) parts.push(String(seed));
  if (tg.counter || !parts.length) parts.push(cnt ? String(cnt).padStart(5, '0') : '%counter');
  return parts.join('_');
}
function saveCard() {
  if (!T.groups['5']) return null; const c = saveCfg();
  const ex = h('div', {class: 'muted'}); const upd = () => { ex.textContent = t('fnExample') + ': ' + fileName(S.seedRandom ? 123456789 : S.seed, 42) + '.png'; };
  const pre = h('input', {type: 'text', placeholder: t('fnPrefixPh')}); pre.value = c.prefix; pre.oninput = () => { c.prefix = pre.value; save(); upd(); };
  const chips = h('div', {class: 'row', style: 'flex-wrap:wrap;gap:6px 14px'});
  SAVE_TAGS.forEach(k => { const cb = h('input', {type: 'checkbox'}); cb.checked = !!c.tags[k]; cb.onchange = () => { c.tags[k] = cb.checked; save(); upd(); }; chips.append(h('label', {class: 'chk'}, cb, t('tag_' + k))); });
  const meta = h('div', {class: 'f inline'}, h('label', {class: 'lab', text: t('metaOn')}), sw(c.meta, x => { c.meta = x; save(); }));
  upd();
  return card('6', t('c6'), [groupCard('5', [
    h('div', {class: 'f'}, h('label', {class: 'lab', text: t('fnPrefix')}), pre),
    h('div', {class: 'lab', text: t('fnTags')}), chips, ex,
    meta, h('div', {class: 'hint', text: t('metaHint')})])]);
}
function renderControls() {""")
# file name + metadata switch inside saverNode
rep("  const num = cnt ? String(cnt).padStart(5, '0') : '%seed';", "  const fname = fileName(seed, cnt); const cfgS = saveCfg();")
rep("if (!OI['Image Saver']) { sv.inputs.filename_prefix = user + shortName(); return; }",
    "if (!OI['Image Saver']) { sv.inputs.filename_prefix = fname; return; }\n"
    "  if (!cfgS.meta && OI['Image Saver Simple']) { out['35'] = {class_type: 'Image Saver Simple', _meta: sv._meta, inputs: {images: sv.inputs.images, filename: fname, path: '', extension: 'png', lossless_webp: true, quality_jpeg_or_webp: 100, optimize_png: false, embed_workflow: false, save_workflow_as_json: false, counter: 0, time_format: '%Y-%m-%d', show_preview: true}}; return; }")
rep("if (!k) { sv.inputs.filename_prefix = user + shortName(); return; }", "if (!k) { sv.inputs.filename_prefix = fname; return; }")
rep("images: sv.inputs.images, filename: user + shortName() + '_%time_' + num, path: '', extension: 'png',", "images: sv.inputs.images, filename: fname, path: '', extension: 'png',")
rep("easy_remix: true, show_preview: true, custom: ('Studio:", "easy_remix: true, show_preview: true, custom: ('Studio:")
rep("prefix: 'File name prefix',", "prefix: 'File name prefix', c6: 'Save', fnPrefix: 'Own text at the start of the name', fnPrefixPh: 'e.g. myproject', fnTags: 'Put into the file name', fnExample: 'Example', "
    "tag_prefix: 'own text', tag_model: 'model', tag_theme: 'theme', tag_date: 'date', tag_time: 'time', tag_seed: 'seed', tag_counter: 'running number', "
    "metaOn: 'Save the generation data in the image', metaHint: 'ON: prompt, model, LoRAs and settings are stored in the PNG (Civitai/A1111 format, readable with Image info). OFF: the image is saved without them.',")
rep("prefix: 'Fájlnév előtag',", "prefix: 'Fájlnév előtag', c6: 'Mentés', fnPrefix: 'Saját szöveg a név elején', fnPrefixPh: 'pl. projektem', fnTags: 'Mi kerüljön a fájlnévbe', fnExample: 'Példa', "
    "tag_prefix: 'saját szöveg', tag_model: 'modell', tag_theme: 'téma', tag_date: 'dátum', tag_time: 'időpont', tag_seed: 'seed', tag_counter: 'sorszám', "
    "metaOn: 'Generálási adatok mentése a képbe', metaHint: 'BE: a prompt, a modell, a LoRA-k és a beállítások a PNG-be kerülnek (Civitai/A1111 formátum, a Képinfó olvassa). KI: a kép ezek nélkül mentődik.',")
open(p, 'w', encoding='utf-8', newline='').write(h)

# =============================== 1.2.0 ========================================
import re as _re, sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from help_texts import HELP as _HELP
h = open(p, encoding='utf-8').read()
rep("const VERSION = '1.1.0';", "const VERSION = '" + APP_VERSION + "';")
rep("<title>ArtFlow Studio</title>", '<title>ArtFlawless Studio</title>\n<meta name="theme-color" content="#15181f">')
# ---- header ----
SV = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
ICON = {
 'folder': f'<svg {SV}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
 'info': f'<svg {SV}><rect x="2" y="3" width="14" height="12" rx="2"/><circle cx="6.5" cy="7.5" r="1.3"/><path d="M2 13l4-4 4.5 4.5"/><circle cx="17" cy="16.5" r="5.5" fill="var(--panel2)" stroke-width="1.8"/><path d="M17 15.6v3.6" stroke-width="2"/><circle cx="17" cy="13.4" r=".8" fill="currentColor" stroke="none"/></svg>',
 'bell': f'<svg {SV}><path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>',
 'gear': f'<svg {SV}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/></svg>',
 'help': f'<svg {SV}><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 4.9.8c0 1.7-2.4 2.2-2.4 3.7"/><circle cx="12" cy="17" r=".6" fill="currentColor"/></svg>',
}
NEW_HEADER = f'''<header>
  <div class="hbox hbrand"><img id="logo" alt=""><div class="bt"><div class="n">ArtFlawless Studio <span class="pill" id="ver"></span></div><div class="l2">Built on ComfyUI node graphs</div><div class="l3">Created by Lalikavics</div></div></div>
  <div class="hbox conn" data-help="h:conn"><div class="cw"><div class="ct"><span class="dot" id="dot"></span><span id="connText"></span></div><div class="ip" id="connIp"></div></div></div>
  <div class="hbox hmid" data-help="h:fam"><div class="fam" id="famTabs"></div></div>
  <div class="hbox icons">
    <button class="ib" id="wfBtn" type="button" data-tt="wf" data-help="h:wf">{ICON['folder']}</button>
    <button class="ib" id="infoBtn" type="button" data-tt="ttInfo" data-help="h:info">{ICON['info']}</button>
    <button class="ib" id="notifBtn" type="button" data-tt="notif" data-help="h:notif">{ICON['bell']}<b id="notifBadge" hidden>!</b></button>
    <span class="gw"><button class="ib" id="gearBtn" type="button" data-tt="settings" data-help="h:gear">{ICON['gear']}</button>
      <div class="gmenu" id="gmenu" hidden>
        <div class="mh" data-t="settings"></div>
        <div class="mi"><span data-t="mLang"></span><div class="lang"><button type="button" data-lang="en">EN</button><button type="button" data-lang="hu">HU</button></div></div>
        <label class="mi"><span data-t="mLearn"></span><span class="sw"><input type="checkbox" id="learnSw"><span></span></span></label>
        <button class="mi" type="button" id="advBtn" data-t="mAdv"></button>
        <button class="mi" type="button" id="comfyBtn" data-t="mCopy"></button>
      </div></span>
    <button class="ib" id="aboutBtn" type="button" data-tt="about" data-help="h:about">{ICON['help']}</button>
  </div>
  <div class="hbox genb">
    <label class="runs" data-help="h:runs"><span data-t="runs"></span><input type="number" id="runs" min="1" max="50" step="1" value="1"></label>
    <button class="btn stop" id="stopBtn" type="button" disabled data-t="stop" data-help="h:stop"></button>
    <button class="btn go" id="goBtn" type="button" title="Ctrl+Enter" data-help="h:go"></button>
  </div>
</header>'''
i = h.index('<header>'); j = h.index('</header>') + len('</header>')
h = h[:i] + NEW_HEADER + h[j:]
h = _re.sub(r'@media \(max-width:1700px\)\{[^\n]*\n', '', h)
h = _re.sub(r'@media \(max-width:1250px\)\{[^\n]*\n', '', h)
CSS = r'''
/* ---- 1.2.0 header ---- */
header{flex:0 0 74px;display:flex;align-items:center;gap:10px;padding:0 10px;background:var(--panel);border-bottom:1px solid var(--line)}
.hbox{border:1px dashed #2a303d;border-radius:10px;height:56px;box-sizing:border-box;display:flex;align-items:center;gap:8px;padding:0 10px;flex:0 0 auto}
.hbox.hbrand{gap:11px;padding:0 14px 0 7px}.hbox.hbrand img{width:42px;height:42px;border-radius:9px;object-fit:cover}
.bt .n{font-weight:650;font-size:16px;letter-spacing:.2px;display:flex;align-items:center;gap:8px;white-space:nowrap}
.bt .l2{font-size:10.5px;color:#7d8597;margin-top:1px;white-space:nowrap}.bt .l3{font-size:10.5px;color:#5d6475;white-space:nowrap}
.pill{font-size:10.5px;font-weight:600;color:var(--acc);border:1px solid #5c4a18;border-radius:9px;padding:0 6px}
.hbox.conn{padding:0 14px}.conn .cw{display:inline-grid;gap:3px}.conn .ct{display:flex;align-items:center;justify-content:center;gap:6px;font-size:12px;color:#aab1c2;white-space:nowrap}
.conn .ip{font:10.5px ui-monospace,Consolas,monospace;color:#5d6475;text-align:center}
.hbox.hmid{flex:1 1 auto;justify-content:center;min-width:0}
.fam button{padding:8px 15px}
.icons{gap:6px}
.ib{width:36px;height:32px;border-radius:8px;background:var(--panel2);border:1px solid var(--line2);color:#c9ceda;position:relative;display:flex;align-items:center;justify-content:center;padding:0;cursor:pointer}
.ib:hover{border-color:#4a5266}.ib svg{width:20px;height:20px}.ib.act{border-color:var(--acc);color:var(--acc)}
.ib b{position:absolute;top:-5px;right:-5px;background:var(--err);color:#1a0505;border-radius:9px;font-size:10px;width:15px;height:15px;line-height:15px;text-align:center;margin:0}
#notifBadge[hidden]{display:none}
.gw{position:relative;display:flex}
.gmenu{position:absolute;right:-60px;top:46px;width:270px;background:var(--panel2);border:1px solid var(--line2);border-radius:10px;padding:6px;z-index:60;box-shadow:0 10px 30px rgba(0,0,0,.55)}
.gmenu[hidden]{display:none}.gmenu .mh{font-size:11px;color:#6f7789;padding:4px 8px}
.gmenu .mi{width:100%;box-sizing:border-box;font-size:13px;padding:8px;border-radius:6px;display:flex;justify-content:space-between;align-items:center;background:none;border:0;color:var(--text);text-align:left;cursor:pointer}
.gmenu .mi:hover{background:#232835}
.genb .runs{display:flex;align-items:center;gap:6px;white-space:nowrap}.genb .runs input{width:46px}
.btn.go{min-width:170px;display:inline-flex;align-items:center;justify-content:center;gap:8px}
.btn.go.busy{background:#8a6a2a;border-color:#8a6a2a;color:#fff3d6}
.spin{width:14px;height:14px;border:2px solid rgba(255,243,214,.35);border-top-color:#fff3d6;border-radius:50%;display:inline-block;animation:afspin .8s linear infinite}
@keyframes afspin{to{transform:rotate(360deg)}}
/* ---- viewer: zoom + spinner ---- */
#stage{overflow:hidden;user-select:none}
#stage #view{position:absolute;left:0;top:0;max-width:none;max-height:none;object-fit:fill;transform-origin:0 0;will-change:transform}
#stage.zoomed{cursor:grab}#stage.drag{cursor:grabbing}
#zoomPct{position:absolute;top:8px;right:10px;font-size:11px;color:#c9ceda;background:rgba(0,0,0,.5);border-radius:6px;padding:2px 7px;pointer-events:none;z-index:3}
#zoomPct[hidden]{display:none}
#stageSpin{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;gap:10px;padding:14px 18px;border-radius:12px;background:rgba(10,12,16,.55);z-index:4;pointer-events:none}
#stageSpin[hidden]{display:none}
#stageSpin i{width:44px;height:44px;border:3px solid rgba(242,184,75,.22);border-top-color:var(--acc);border-radius:50%;animation:afspin .9s linear infinite}
#spinText{font-size:12.5px;color:#c9ceda;max-width:420px;text-align:center}
/* ---- learning mode ---- */
#helpPop{position:fixed;z-index:90;max-width:380px;background:#1f2430;border:1px solid #5c4a18;border-radius:10px;padding:10px 12px;font-size:12.5px;line-height:1.5;color:#d6dae4;box-shadow:0 10px 30px rgba(0,0,0,.55);pointer-events:none}
#helpPop[hidden]{display:none}#helpPop b{color:var(--acc);display:block;margin-bottom:2px}
body.learn .f>.lab::after,body.learn .gt>b::after,body.learn details.card>summary .n::after{content:"?";display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:6px;border-radius:50%;border:1px solid #5c4a18;color:var(--acc);font-size:9.5px;font-weight:700;vertical-align:1px}
.welcome p{line-height:1.55}
'''
rep("</style>", CSS + "</style>")
rep('<div id="stage"><div id="empty" data-t="empty"></div><img id="view" alt="" hidden><div id="badge" hidden></div></div>',
    '<div id="stage" data-help="h:viewer"><div id="empty" data-t="empty"></div><img id="view" alt="" hidden draggable="false"><div id="badge" hidden></div><div id="zoomPct" hidden></div><div id="stageSpin" hidden><i></i><span id="spinText"></span></div></div>')
rep('<div id="toasts"></div>', '<div id="toasts"></div>\n<div id="helpPop" hidden></div>')
# ---- i18n ----
EN = ("settings: 'Settings', mLang: 'Language', mLearn: 'Learning mode (hints)', mAdv: 'Advanced settings…', mCopy: 'Open a copy in ComfyUI…', ttInfo: 'Image info', "
      "generating: 'Generating…', offlineS: 'offline', baseSize: 'Base size', noModelSel: 'Choose a model file first (Base model panel).', gV: 'Own VAE', gVD: 'A separate VAE file instead of the one inside the checkpoint.', "
      "welT: 'Welcome to ArtFlawless Studio', welP: 'Would you like to turn on learning mode? When it is on, pointing at any panel, switch or value shows a short explanation of what it does and which values work well. You can switch it on or off at any time under Settings (gear icon).', welNo: 'No, thanks', welYes: 'Yes, turn it on', "
      "copyErr: 'ComfyUI did not take the copy automatically, so it was downloaded as a JSON file – drag it into the ComfyUI window.', copyOk: 'The copy is open in ComfyUI. Changes there do not affect the Studio.', folderErr: 'Could not open the folder: {0}', ")
HU = ("settings: 'Beállítások', mLang: 'Nyelv', mLearn: 'Tanuló mód (súgó)', mAdv: 'Haladó beállítások…', mCopy: 'Másolat megnyitása a ComfyUI-ban…', ttInfo: 'Képinfó', "
      "generating: 'Generálás…', offlineS: 'nincs kapcsolat', baseSize: 'Alapméret', noModelSel: 'Előbb válassz modellfájlt (Alapmodell panel).', gV: 'Saját VAE', gVD: 'Külön VAE-fájl a checkpointban lévő helyett.', "
      "welT: 'Üdv az ArtFlawless Studióban!', welP: 'Bekapcsolod a tanuló módot? Ilyenkor ha bármelyik panelre, kapcsolóra vagy értékre mutatsz, egy rövid magyarázat elmondja, mire való, és milyen értékek működnek jól. A Beállításokban (fogaskerék) bármikor ki- és bekapcsolhatod.', welNo: 'Nem, köszönöm', welYes: 'Igen, kapcsold be', "
      "copyErr: 'A ComfyUI nem vette át automatikusan a másolatot, ezért JSON-fájlként letöltődött – húzd be a ComfyUI ablakába.', copyOk: 'A másolat megnyílt a ComfyUI-ban. Az ott végzett módosítások nem hatnak a Studióra.', folderErr: 'Nem sikerült megnyitni a mappát: {0}', ")
rep("wf: 'Workflows',", EN + "wf: 'Workflows',")
rep("wf: 'Munkafolyamatok',", HU + "wf: 'Munkafolyamatok',")
rep("open: 'Open'", "open: 'Open folder'"); rep("open: 'Megnyitás'", "open: 'Mappa megnyitása'")
rep("const STEP_NAME = {'1a': 'g1a',", "const STEP_NAME = {'v': 'gV', '1a': 'g1a',")
rep("  document.querySelectorAll('[data-t]').forEach(e => { e.textContent = t(e.getAttribute('data-t')); });",
    "  document.querySelectorAll('[data-t]').forEach(e => { e.textContent = t(e.getAttribute('data-t')); });\n"
    "  document.querySelectorAll('[data-tt]').forEach(e => { e.title = t(e.getAttribute('data-tt')); e.setAttribute('aria-label', e.title); });")
# ---- connection + busy state ----
rep("function conn(on) { if (on != null) CONN = on; $('#dot').classList.toggle('on', !!CONN); $('#connText').textContent = CONN == null ? t('connecting') : CONN ? t('connected') + (R.queue ? ' · ' + t('queue', R.queue) : '') : t('offline'); }",
    "function conn(on) { if (on != null) CONN = on; $('#dot').classList.toggle('on', !!CONN); $('#connText').textContent = CONN == null ? t('connecting') : CONN ? t('connected') : t('offlineS'); $('#connIp').textContent = API_URL.host; }")
rep("function busy() { const n = R.jobs.size; $('#stopBtn').disabled = n === 0; $('#goBtn').textContent = n ? t('goQ', n) : t('go'); }",
    "function busy() { const n = R.jobs.size; $('#stopBtn').disabled = n === 0; const g = $('#goBtn'); g.classList.toggle('busy', n > 0);\n"
    "  if (n) { g.replaceChildren(h('i', {class: 'spin'}), t('generating') + (n > 1 ? ' (+' + (n - 1) + ')' : '')); } else g.textContent = t('go');\n"
    "  $('#stageSpin').hidden = n === 0; }")
rep("$('#progText').textContent = raw != null && raw !== '' ? raw : t(key, ...(args || []));",
    "$('#progText').textContent = raw != null && raw !== '' ? raw : t(key, ...(args || [])); const st_ = $('#spinText'); if (st_) st_.textContent = $('#progText').textContent;")
# ---- open folder + native picker ----
rep("h('button', {class: 'btn sm', type: 'button', text: t('open'), onclick: () => window.open(R.cur, '_blank')})",
    "h('button', {class: 'btn sm', type: 'button', text: t('open'), onclick: () => openFolder(R.cur)})")
rep("\n  drop.onclick = () => file.click();\n",
    "\n  drop.onclick = async () => { try { const r = await fetch(API + '/artflow/pick-image', {method: 'POST'}); if (!r.ok) throw new Error('HTTP ' + r.status); const j = await r.json(); if (j.cancelled) return; if (!j.name) throw new Error(j.error || '?');\n"
    "    if (!EXTRA_IMAGES.includes(j.name)) EXTRA_IMAGES.unshift(j.name); if (id === '48') setVal('48', 'source_folder', 'input'); pick(j.name); fill(); } catch (_) { file.click(); } };\n")
# ---- help markers ----
rep("function card(n, title, kids, open) { return h('details', {class: 'card', open: open !== false}, h('summary', null, h('span', {class: 'n', text: n}), title)",
    "function card(n, title, kids, open) { return h('details', {class: 'card', open: open !== false}, h('summary', {'data-help': 'card:' + n}, h('span', {class: 'n', text: n}), title)")
rep("c.append(h('div', {class: 'ghead'}, sw(", "c.append(h('div', {class: 'ghead', 'data-help': 'group:' + key}, sw(")
rep("  const row = h('div', {class: 'f'}); const lab = h('label', {class: 'lab', text: label}); let ctl;",
    "  const row = h('div', {class: 'f', 'data-help': id + '.' + name}); const lab = h('label', {class: 'lab', text: label}); let ctl;")
rep("  return h('div', {class: 'f'}, h('label', {class: 'lab', text: t('seedL')})", "  return h('div', {class: 'f', 'data-help': 'seed'}, h('label', {class: 'lab', text: t('seedL')})")
rep("  return h('div', {class: 'sub'},\n    h('div', {class: 'subhead'}", "  return h('div', {class: 'sub', 'data-help': 'baselora'},\n    h('div', {class: 'subhead'}")
rep("const box = h('div', {class: 'loras'});", "const box = h('div', {class: 'loras', 'data-help': 'loras'});")
rep("h('div', {class: 'f'}, h('label', {class: 'lab', text: t('fnPrefix')}), pre),", "h('div', {class: 'f', 'data-help': 'save:prefix'}, h('label', {class: 'lab', text: t('fnPrefix')}), pre),")
rep("const chips = h('div', {class: 'row', style: 'flex-wrap:wrap;gap:6px 14px'});", "const chips = h('div', {class: 'row', style: 'flex-wrap:wrap;gap:6px 14px', 'data-help': 'save:tags'});")
rep("const meta = h('div', {class: 'f inline'}, h('label', {class: 'lab', text: t('metaOn')})", "const meta = h('div', {class: 'f inline', 'data-help': 'save:meta'}, h('label', {class: 'lab', text: t('metaOn')})")
# ---- custom family ----
rep("      h('div', {class: 'two'}, field('86', 'choice', t('theme')), field('87', 'choice', t('ratio'))),",
    "      T.family === 'custom' ? h('div', {class: 'two'}, field('87', 'choice', t('ratio')), field('127', 'value', t('baseSize'), {min: 256, max: 2048, step: 64}))\n"
    "        : h('div', {class: 'two'}, field('86', 'choice', t('theme')), field('87', 'choice', t('ratio'))),")
rep("const known = new Set(CAT.models.map(m => m.file)); const own = onDisk.filter(x => !known.has(x));",
    "const known = new Set(CAT.models.map(m => m.file)); const own = FAMILY === 'custom' ? onDisk : onDisk.filter(x => !known.has(x));")
rep("    fi ? h('div', {class: 'muted', text: t('famHint') + ': ' + (fi['best_' + LANG] || fi.best_en || '')}) : null, box,",
    "    fi ? h('div', {class: 'muted', text: t('famHint') + ': ' + (fi['best_' + LANG] || fi.best_en || '')}) : null, box,\n"
    "    T.groups.v && T.family !== 'custom' ? groupCard('v', [field('125', 'vae_name', t('vae'), {pretty: true, onchange: () => renderMissing()})]) : null,")
rep("function shortName() {\n  const f = val('2', modelField());",
    "function shortName() {\n  const f = val('2', modelField());\n  if (FAMILY === 'custom') return (slug(pretty(f || '')).slice(0, 28)) || 'CUSTOM';")
rep("async function run() {\n  if (!T) return;", "async function run() {\n  if (!T) return; if (!val('2', modelField())) { toast(t('noModelSel'), 'err'); return; }")
# ---- new functions ----
rep("function openNotif() {", r"""const HELP = """ + json.dumps(_HELP, ensure_ascii=False) + r""";
function helpText(k) { const fam = T && T.family; let v = HELP[k + '@' + fam] || HELP[k]; if (!v && k.indexOf('.') > 0) v = HELP['*.' + k.slice(k.indexOf('.') + 1)]; if (!v) return null; return LANG === 'hu' ? [v[2], v[3]] : [v[0], v[1]]; }
const LS_LEARN = 'artflow.studio.learn';
let LEARN = null; try { LEARN = localStorage.getItem(LS_LEARN); } catch (_) {}
function setLearn(on) { LEARN = on ? '1' : '0'; try { localStorage.setItem(LS_LEARN, LEARN); } catch (_) {} document.body.classList.toggle('learn', on); const s = $('#learnSw'); if (s) s.checked = on; if (!on) $('#helpPop').hidden = true; }
function initHelp() {
  const pop = $('#helpPop'); let cur = null;
  document.addEventListener('mouseover', e => {
    if (LEARN !== '1') return; let el = e.target.closest ? e.target.closest('[data-help]') : null; if (el && !$('#gmenu').hidden && !el.closest('#gmenu')) el = null; if (el === cur) return; cur = el;
    const tx = el ? helpText(el.getAttribute('data-help')) : null; if (!tx) { pop.hidden = true; return; }
    pop.replaceChildren(h('b', {text: tx[0]}), h('div', {text: tx[1]})); pop.hidden = false;
    const r = el.getBoundingClientRect(), pw = pop.offsetWidth, ph = pop.offsetHeight;
    let x = Math.min(Math.max(8, r.left), innerWidth - pw - 8), y = r.bottom + 6; if (y + ph > innerHeight - 8) y = Math.max(8, r.top - ph - 6);
    pop.style.left = x + 'px'; pop.style.top = y + 'px';
  });
  document.addEventListener('scroll', () => { pop.hidden = true; cur = null; }, true);
}
function welcome() {
  MODAL_KIND = 'welcome'; $('#modalTitle').textContent = t('welT');
  $('#modalBody').replaceChildren(h('div', {class: 'welcome'}, h('p', {text: t('welP')}), h('div', {class: 'row', style: 'justify-content:flex-end;gap:8px'},
    h('button', {class: 'btn', type: 'button', text: t('welNo'), onclick: () => { setLearn(false); $('#modal').classList.remove('open'); }}),
    h('button', {class: 'btn go', type: 'button', text: t('welYes'), onclick: () => { setLearn(true); $('#modal').classList.remove('open'); }}))));
  $('#modal').classList.add('open');
}
/* ---------- viewer zoom (real-pixel %, from "fit" up to 300 %) ---------- */
const Z = {s: 1, x: 0, y: 0, fit: 1, nw: 0, nh: 0, atFit: true};
function zMax() { return Math.max(3, Z.fit); }
function zClamp() { const st = $('#stage'), W = st.clientWidth, H = st.clientHeight, w = Z.nw * Z.s, hh = Z.nh * Z.s;
  Z.x = w <= W ? (W - w) / 2 : Math.min(0, Math.max(W - w, Z.x)); Z.y = hh <= H ? (H - hh) / 2 : Math.min(0, Math.max(H - hh, Z.y)); }
function zApply() { const v = $('#view'), st = $('#stage'); v.style.width = Z.nw + 'px'; v.style.height = Z.nh + 'px'; v.style.transform = 'translate(' + Z.x + 'px,' + Z.y + 'px) scale(' + Z.s + ')';
  const p = $('#zoomPct'); p.hidden = v.hidden || !Z.nw; p.textContent = Math.round(Z.s * 100) + '%'; st.classList.toggle('zoomed', Z.s > Z.fit * 1.001); }
function zFit() { const v = $('#view'), st = $('#stage'); if (!v.naturalWidth) return; Z.nw = v.naturalWidth; Z.nh = v.naturalHeight; Z.fit = Math.min(st.clientWidth / Z.nw, st.clientHeight / Z.nh); Z.s = Z.fit; Z.atFit = true; zClamp(); zApply(); }
function initZoom() {
  const st = $('#stage'), v = $('#view');
  v.addEventListener('load', () => { if (!Z.atFit && v.naturalWidth === Z.nw && v.naturalHeight === Z.nh) { zApply(); return; } zFit(); });
  st.addEventListener('wheel', e => { if (v.hidden || !Z.nw) return; e.preventDefault(); const r = st.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
    const ns = Math.min(zMax(), Math.max(Z.fit, Z.s * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); Z.x = mx - (mx - Z.x) * ns / Z.s; Z.y = my - (my - Z.y) * ns / Z.s; Z.s = ns; Z.atFit = Z.s <= Z.fit * 1.001; zClamp(); zApply(); }, {passive: false});
  let drag = null;
  st.addEventListener('mousedown', e => { if (e.button !== 0 || Z.s <= Z.fit * 1.001) return; drag = {x: e.clientX - Z.x, y: e.clientY - Z.y}; st.classList.add('drag'); e.preventDefault(); });
  addEventListener('mousemove', e => { if (!drag) return; Z.x = e.clientX - drag.x; Z.y = e.clientY - drag.y; zClamp(); zApply(); });
  addEventListener('mouseup', () => { drag = null; st.classList.remove('drag'); });
  st.addEventListener('dblclick', () => zFit());
  if (window.ResizeObserver) new ResizeObserver(() => { if (!Z.nw) return; const was = Z.atFit; const v2 = $('#view'); Z.fit = Math.min(st.clientWidth / Z.nw, st.clientHeight / Z.nh); if (was) zFit(); else { Z.s = Math.min(zMax(), Math.max(Z.fit, Z.s)); zClamp(); zApply(); } }).observe(st);
}
async function openFolder(url) {
  try { const u = new URL(url, location.href); if (u.protocol === 'blob:') return;
    const r = await fetch(API + '/artflow/open-folder', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({filename: u.searchParams.get('filename'), subfolder: u.searchParams.get('subfolder') || '', type: u.searchParams.get('type') || 'output'})});
    if (!r.ok) throw new Error('HTTP ' + r.status); } catch (e) { toast(t('folderErr', e.message), 'err'); }
}
function downloadJson(obj, name) { const a = h('a', {href: URL.createObjectURL(new Blob([JSON.stringify(obj, null, 1)], {type: 'application/json'})), download: name}); document.body.append(a); a.click(); a.remove(); }
function openComfyCopy() {
  // a COPY of the current graph in ComfyUI's own editor – nothing done there flows back into the Studio
  let prompt; try { prompt = buildPrompt(S.seedRandom ? rndSeed() : (Number(S.seed) || 0), 0); } catch (e) { toast(t('buildErr', e.message), 'err'); return; }
  const w = window.open(API + '/', '_blank'); let n = 0;
  const tm = setInterval(async () => { n++;
    try { if (w && w.app && typeof w.app.loadApiJson === 'function' && w.app.graph) { clearInterval(tm); await w.app.loadApiJson(prompt, 'ArtFlawless-copy.json'); toast(t('copyOk')); return; } } catch (_) {}
    if (n > 80 || !w || w.closed) { clearInterval(tm); downloadJson(prompt, 'ArtFlawless-copy-api.json'); toast(t('copyErr'), 'err'); } }, 500);
}
function openNotif() {""")
rep("$('#notifBtn').onclick = openNotif; $('#wfBtn').onclick = openWf; $('#infoBtn').onclick = openInfo;",
    "$('#notifBtn').onclick = openNotif; $('#wfBtn').onclick = openWf; $('#infoBtn').onclick = openInfo;\n"
    "  const gm = $('#gmenu'); $('#gearBtn').onclick = e => { e.stopPropagation(); gm.hidden = !gm.hidden; $('#gearBtn').classList.toggle('act', !gm.hidden); };\n"
    "  document.addEventListener('click', e => { if (!gm.hidden && !gm.contains(e.target)) { gm.hidden = true; $('#gearBtn').classList.remove('act'); } });\n"
    "  $('#learnSw').onchange = e => setLearn(e.target.checked); $('#comfyBtn').onclick = () => { gm.hidden = true; $('#gearBtn').classList.remove('act'); openComfyCopy(); };\n"
    "  addEventListener('beforeunload', e => { if (R.jobs.size) { e.preventDefault(); e.returnValue = ''; } });\n"
    "  initZoom(); initHelp();")
rep("$('#advBtn').onclick = () => { renderAdvanced(); $('#drawer').classList.add('open'); };",
    "$('#advBtn').onclick = () => { $('#gmenu').hidden = true; $('#gearBtn').classList.remove('act'); renderAdvanced(); $('#drawer').classList.add('open'); };")
rep("  setProg('ready', [], 0); applyLang(); connect(); $('#boot').remove();",
    "  setProg('ready', [], 0); applyLang(); connect(); $('#boot').remove();\n  if (LEARN === null) welcome(); else setLearn(LEARN === '1');")
rep("else if (MODAL_KIND === 'info') openInfo(); else openAbout(); }", "else if (MODAL_KIND === 'info') openInfo(); else if (MODAL_KIND === 'welcome') welcome(); else openAbout(); }")
# ---- name + About disclaimer ----
h = h.replace('ArtFlow Studio', 'ArtFlawless Studio')
rep("<p><b>Third-party components.</b>",
    "<p><b>Independent project.</b> ArtFlawless Studio is an independent interface. It is not affiliated with, endorsed by or connected to Comfy Org or the ComfyUI developers. ComfyUI is free software released under the GNU General Public License v3.0; it is installed unmodified from its official release and its licence applies to it.</p>\n<p><b>Third-party components.</b>")
rep("<p><b>Külső összetevők.</b>",
    "<p><b>Független projekt.</b> Az ArtFlawless Studio független kezelőfelület. Semmilyen kapcsolatban nem áll a Comfy Orggal és a ComfyUI fejlesztőivel, és ők nem is támogatják vagy hagyják jóvá. A ComfyUI szabad szoftver a GNU General Public License v3.0 licenc alatt; a hivatalos kiadásból, módosítás nélkül települ, és a saját licence vonatkozik rá.</p>\n<p><b>Külső összetevők.</b>")
# ---- licence links + usage notice ----
rep("""  if (own.length || (cur && !known.has(cur))) box.append(field('2', modelField(), t('ownModel'), {pretty: true, onchange: () => renderControls()}));""",
    """  if (own.length || (cur && !known.has(cur))) { box.append(field('2', modelField(), t('ownModel'), {pretty: true, onchange: () => renderControls()}));
    const open = LIC_OPEN.has('_own'); box.append(h('div', {class: 'meta'}, h('button', {class: 'licbtn' + (open ? ' act' : ''), type: 'button', text: t('licenseL') + (open ? ' ▴' : ' ▾'), onclick: () => { LIC_OPEN.has('_own') ? LIC_OPEN.delete('_own') : LIC_OPEN.add('_own'); drawModels(box); }})));
    if (open) box.append(h('div', {class: 'licbox'}, h('div', {text: t('ownLic')}), h('div', {class: 'licw', text: '⚠ ' + t('ownDisc')}))); }""")
rep("licenseL: 'Licence', ", "licenseL: 'Licence', licOpen: 'Open the licence page', ownLic: 'Models you downloaded yourself are not checked by the Studio. Each one is subject to its own licence: read it on the page you downloaded it from (Civitai, Hugging Face…), especially before commercial use.', ownDisc: 'Disclaimer: the author of ArtFlawless Studio takes no responsibility for models added by the user, their licences, or the images made with them. You are responsible for following the licence of each model and the law.', licNote: 'The Studio runs every model unmodified. What you may do with the images is set by each model\\'s licence: read it before commercial use (brand deals, selling images, paid services). LoRAs from Civitai have their own licences too, shown on their pages.', ")
rep("licenseL: 'Licenc', ", "licenseL: 'Licenc', licOpen: 'Licenc oldal megnyitása', ownLic: 'A saját magad által letöltött modelleket a Studio nem ellenőrzi. Mindegyikre a saját licence vonatkozik: olvasd el azon az oldalon, ahonnan letöltötted (Civitai, Hugging Face…), különösen kereskedelmi használat előtt.', ownDisc: 'Felelősségkizárás: az ArtFlawless Studio szerzője nem vállal felelősséget a felhasználó által hozzáadott modellekért, azok licencéért és a velük készült képekért. Az egyes modellek licencének és a jogszabályoknak a betartása a felhasználó felelőssége.', licNote: 'A Studio minden modellt módosítás nélkül futtat. Hogy mire használhatod a képeket, azt az adott modell licence szabja meg: kereskedelmi használat (márkás együttműködés, képeladás, fizetős szolgáltatás) előtt olvasd el. A Civitai LoRA-knak is saját licencük van, ezt az oldalukon látod.', ")
rep("""    row.append(h('div', {class: 'meta', text: (m['note_' + LANG] || m.note_en || '') + '  ·  ' + t('licenseL') + ': ' + (m.license || '?')}));""",
    """    { const mt = h('div', {class: 'meta'}); const nt = m['note_' + LANG] || m.note_en || ''; if (nt) mt.append(nt + '  ');
      const open = LIC_OPEN.has(m.id), lb = h('button', {class: 'licbtn' + (open ? ' act' : ''), type: 'button', text: t('licenseL') + (open ? ' ▴' : ' ▾'), onclick: () => { LIC_OPEN.has(m.id) ? LIC_OPEN.delete(m.id) : LIC_OPEN.add(m.id); drawModels(box); }});
      mt.append(lb); row.append(mt);
      if (open) { const ln = m['license_note_' + LANG] || m.license_note_en; const d = h('div', {class: 'licbox'});
        d.append(h('div', null, h('b', {text: m.license || '?'}), m.license_url ? h('span', null, '  ·  ', h('a', {href: m.license_url, target: '_blank', rel: 'noopener', class: 'lic', text: t('licOpen')})) : null));
        if (ln) d.append(h('div', {class: 'licw', text: '⚠ ' + ln})); d.append(h('div', {class: 'muted', text: t('licNote')})); row.append(d); } }""")
rep("""    h('div', {class: 'row', style: 'justify-content:flex-end'}, refreshBtn())]);""",
    """    h('div', {class: 'row', style: 'justify-content:flex-end'}, refreshBtn())]);""")
rep("</style>", "a.lic,#modalBody a{color:var(--acc,#f2b84b);text-decoration:underline dotted;text-underline-offset:2px}a.lic:hover,#modalBody a:hover{text-decoration-style:solid}.licbtn{background:#2a2412;border:1px solid #5c4a18;color:#f3dfa6;border-radius:9px;padding:1px 9px;font-size:11px;font-weight:600;cursor:pointer}.licbtn:hover,.licbtn.act{background:#3a3016;border-color:#8a6a2a;color:var(--acc)}.licbox{margin-top:6px;padding:8px 10px;background:#2a2412;border:1px solid #5c4a18;color:#f3dfa6;border-radius:8px;font-size:12px;display:flex;flex-direction:column;gap:4px}.licbox .muted{color:#cbbb8a}.licw{color:var(--acc)}\n#modalBody ul.licl{margin:4px 0 0 18px;padding:0}#modalBody ul.licl li{margin:2px 0}\n</style>")
_L = [('Z-Image Turbo', 'Apache-2.0', 'https://huggingface.co/Tongyi-MAI/Z-Image-Turbo'),
      ('Flux.1 schnell', 'Apache-2.0', 'https://huggingface.co/black-forest-labs/FLUX.1-schnell'),
      ('Juggernaut XL v9', 'CreativeML Open RAIL-M', 'https://huggingface.co/RunDiffusion/Juggernaut-XL-v9'),
      ('RealVisXL V5.0', 'OpenRAIL++', 'https://huggingface.co/SG161222/RealVisXL_V5.0'),
      ('Pony Diffusion V6 XL', 'Fair AI Public License 1.0-SD', 'https://civitai.com/models/257749/pony-diffusion-v6-xl'),
      ('ComfyUI', 'GPL-3.0', 'https://github.com/comfyanonymous/ComfyUI/blob/master/LICENSE')]
_li = ''.join('<li><a href="%s" target="_blank" rel="noopener">%s</a> – %s</li>' % (u, n, l) for n, l, u in _L)
rep("<p><b>Third-party components.</b>",
    "<p><b>System requirements.</b></p><ul class=\"licl\"><li><b>Minimum:</b> Windows 10 64-bit (1803 or newer) or Windows 11; NVIDIA GeForce RTX card with 8 GB video memory (e.g. RTX 2070, 3060 Ti, 4060) and an up-to-date driver; 32 GB RAM; 4-core 64-bit processor; 50 GB free disk space (SSD); Microsoft Edge (part of Windows 10 and 11, it also provides the WebView2 engine of the Studio window); internet connection for the setup and the model downloads.</li><li><b>Recommended:</b> Windows 11 or Windows 10 22H2; NVIDIA RTX card with 12 GB or more video memory (e.g. RTX 3060 12 GB, 4070 or better); 64 GB RAM; 6 or more cores; 100 GB free space on an NVMe SSD.</li><li><b>Tested on:</b> RTX 3060 Ti 8 GB, 64 GB RAM, Windows 10 22H2. AMD and Intel graphics cards are not supported.</li></ul>\n<p><b>Licences and use.</b> The Studio does not modify any model; it only loads them the way ComfyUI does. What you may do with the generated images is set by each model's own licence, not by the program you run it in. Before commercial use (brand deals, selling images, offering generation as a paid service) read the licence of the model and of every LoRA you used. Z-Image Turbo and Flux.1 schnell are the most permissive; Pony may not be used as a paid generation service, and Juggernaut may not be put behind a paid API without RunDiffusion's licence. The licences also forbid harmful uses, such as misleading content or depicting a real person without consent. Models you add yourself are not checked by the Studio; the author of ArtFlawless Studio takes no responsibility for them, their licences or the images made with them. This is not legal advice.</p><ul class=\"licl\">" + _li + "</ul>\n<p><b>Third-party components.</b>")
rep("<p><b>Külső összetevők.</b>",
    "<p><b>Rendszerkövetelmények.</b></p><ul class=\"licl\"><li><b>Minimum:</b> Windows 10 64 bites (1803 vagy újabb) vagy Windows 11; NVIDIA GeForce RTX videokártya 8 GB videomemóriával (pl. RTX 2070, 3060 Ti, 4060) és friss illesztőprogrammal; 32 GB RAM; 4 magos 64 bites processzor; 50 GB szabad hely (SSD); Microsoft Edge (a Windows 10 és 11 része, ez adja a Studio ablakának WebView2 motorját is); internetkapcsolat a telepítéshez és a modellek letöltéséhez.</li><li><b>Ajánlott:</b> Windows 11 vagy Windows 10 22H2; NVIDIA RTX videokártya legalább 12 GB videomemóriával (pl. RTX 3060 12 GB, 4070 vagy jobb); 64 GB RAM; legalább 6 mag; 100 GB szabad hely NVMe SSD-n.</li><li><b>Tesztelve:</b> RTX 3060 Ti 8 GB, 64 GB RAM, Windows 10 22H2. AMD és Intel videokártyák nem támogatottak.</li></ul>\n<p><b>Licencek és felhasználás.</b> A Studio egyetlen modellt sem módosít, csak betölti őket, ahogy a ComfyUI. Hogy mire használhatod a kész képeket, azt az adott modell saját licence szabja meg, nem az, hogy milyen programmal futtatod. Kereskedelmi használat előtt (márkás együttműködés, képeladás, fizetős generáló szolgáltatás) olvasd el a modell és minden használt LoRA licencét. A Z-Image Turbo és a Flux.1 schnell a legszabadabb; a Pony nem használható fizetős generáló szolgáltatásként, a Juggernaut pedig nem tehető fizetős API mögé a RunDiffusion engedélye nélkül. A licencek tiltják a káros felhasználást is, például a félrevezető tartalmat vagy valós személy hozzájárulás nélküli ábrázolását. A magad által hozzáadott modelleket a Studio nem ellenőrzi; az ArtFlawless Studio szerzője nem vállal felelősséget értük, a licencükért és a velük készült képekért. Ez nem jogi tanács.</p><ul class=\"licl\">" + _li + "</ul>\n<p><b>Külső összetevők.</b>")
# ---- frameless window (WebView2 host): own title area, minimise / maximise / close buttons ----
rep("</header>", """  <div class="wctl" id="wctl" hidden>
    <button type="button" id="wMin" class="wb" data-tt="wMin"><svg viewBox="0 0 12 12"><path d="M2 6.5h8" stroke="currentColor" stroke-width="1.2"/></svg></button>
    <button type="button" id="wMax" class="wb" data-tt="wMax"><svg viewBox="0 0 12 12" class="i1"><rect x="2.5" y="2.5" width="7" height="7" fill="none" stroke="currentColor" stroke-width="1.1"/></svg><svg viewBox="0 0 12 12" class="i2"><path d="M4 2.5h5.5V8M2.5 4h5.5v5.5H2.5z" fill="none" stroke="currentColor" stroke-width="1.1"/></svg></button>
    <button type="button" id="wClose" class="wb wx" data-tt="wClose"><svg viewBox="0 0 12 12"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" stroke-width="1.2"/></svg></button>
  </div>
</header>""")
rep("</style>", """/* ---- frameless window ---- */
html.inhost header{-webkit-app-region:drag;app-region:drag;padding-right:0}
html.inhost header button,html.inhost header input,html.inhost header label,html.inhost header a,html.inhost header .gmenu,html.inhost .wctl{-webkit-app-region:no-drag;app-region:no-drag}
.wctl{align-self:flex-start;display:flex;margin-left:2px}
.wb{width:42px;height:30px;display:flex;align-items:center;justify-content:center;background:none;border:0;color:#8d95a8;cursor:default;padding:0}
.wb svg{width:11px;height:11px}.wb:hover{background:#272c38;color:#e8eaf0}
.wb.wx:hover{background:#c42b1c;color:#fff}.wb.wx:active{background:#a3271a}
.wb .i2{display:none}html.wmax .wb .i1{display:none}html.wmax .wb .i2{display:block}
</style>""")
rep("initZoom(); initHelp();", "initZoom(); initHelp(); initHost();")
rep("function openNotif() {", r"""const HOST = !!(window.chrome && window.chrome.webview);
function hostMsg(m) { try { window.chrome.webview.postMessage(m); } catch (_) {} }
function initHost() {
  if (!HOST) return; document.documentElement.classList.add('inhost'); $('#wctl').hidden = false;
  $('#wMin').onclick = () => hostMsg('min'); $('#wMax').onclick = () => hostMsg('max'); $('#wClose').onclick = () => window.afHostClose();
  const hd = document.querySelector('header'), free = e => !e.target.closest('button,input,label,select,a,textarea,[role=button],.gmenu,.wctl');
  hd.addEventListener('mousedown', e => { if (e.button === 0 && e.detail === 1 && free(e)) hostMsg('drag'); });
  hd.addEventListener('dblclick', e => { if (free(e)) hostMsg('max'); });
}
window.afHostState = st => document.documentElement.classList.toggle('wmax', st === 'max');
window.afHostClose = () => { if (R.jobs.size) closeAsk(); else hostMsg('close'); };
function closeAsk() {
  MODAL_KIND = 'closeq'; const body = $('#modalBody'); body.replaceChildren(h('p', {text: t('closeP')}),
    h('div', {class: 'row', style: 'justify-content:flex-end;gap:8px'}, h('button', {class: 'btn sm', type: 'button', text: t('closeNo'), onclick: () => $('#modal').classList.remove('open')}),
      h('button', {class: 'btn sm', type: 'button', style: 'background:#c42b1c;border-color:#c42b1c;color:#fff', text: t('closeYes'), onclick: () => hostMsg('close')})));
  $('#modalTitle').textContent = t('closeT'); $('#modal').classList.add('open');
}
function openNotif() {""")
rep("else if (MODAL_KIND === 'welcome') welcome(); else openAbout(); }", "else if (MODAL_KIND === 'welcome') welcome(); else if (MODAL_KIND === 'closeq') closeAsk(); else openAbout(); }")
rep("licenseL: 'Licence', ", "licenseL: 'Licence', wMin: 'Minimise', wMax: 'Maximise / restore', wClose: 'Close', closeT: 'Close ArtFlawless Studio?', closeP: 'A generation is still running. If you close the Studio now, it stops and the unfinished image is lost.', closeYes: 'Close', closeNo: 'Keep working', ")
rep("licenseL: 'Licenc', ", "licenseL: 'Licenc', wMin: 'Kis méret', wMax: 'Teljes méret / visszaállítás', wClose: 'Bezárás', closeT: 'Bezárod az ArtFlawless Studiót?', closeP: 'Még fut egy generálás. Ha most bezárod, leáll, és a félkész kép elvész.', closeYes: 'Bezárás', closeNo: 'Mégse', ")
# ---- footer strip + resize edges in the frameless window ----
rep("</main>", """</main>
<footer class="afoot"></footer>
<div class="rz" data-ht="12" style="top:0;left:6px;right:6px;height:5px;cursor:n-resize"></div>
<div class="rz" data-ht="15" style="bottom:0;left:6px;right:6px;height:5px;cursor:s-resize"></div>
<div class="rz" data-ht="10" style="left:0;top:6px;bottom:6px;width:5px;cursor:w-resize"></div>
<div class="rz" data-ht="11" style="right:0;top:6px;bottom:6px;width:5px;cursor:e-resize"></div>
<div class="rz" data-ht="13" style="top:0;left:0;width:8px;height:8px;cursor:nw-resize"></div>
<div class="rz" data-ht="14" style="top:0;right:0;width:8px;height:8px;cursor:ne-resize"></div>
<div class="rz" data-ht="16" style="bottom:0;left:0;width:8px;height:8px;cursor:sw-resize"></div>
<div class="rz" data-ht="17" style="bottom:0;right:0;width:12px;height:12px;cursor:se-resize"></div>""")
rep("</style>", """.afoot{flex:0 0 7px;background:var(--panel);border-top:1px solid var(--line)}
.rz{position:fixed;z-index:200;display:none;-webkit-app-region:no-drag;app-region:no-drag}
html.inhost:not(.wmax) .rz{display:block}
</style>""")
rep("  hd.addEventListener('dblclick',", "  document.querySelectorAll('.rz').forEach(z => z.addEventListener('mousedown', e => { if (e.button === 0) { e.preventDefault(); hostMsg('resize:' + z.dataset.ht); } }));\n  hd.addEventListener('dblclick',")
# ---- narrow windows: the header folds step by step (brand lines, icon buttons -> "more" menu, family tabs -> dropdown) ----
rep('<div class="hbox hmid" data-help="h:fam"><div class="fam" id="famTabs"></div></div>',
    '<div class="hbox hmid" data-help="h:fam"><div class="fam" id="famTabs"></div><span class="gw famdd"><button class="ddb" id="famDdBtn" type="button"><span id="famDdTxt"></span><svg viewBox="0 0 12 12"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.4"/></svg></button><div class="gmenu dd" id="famDd" hidden></div></span></div>')
rep('<div class="hbox icons">',
    '<div class="hbox icons">\n    <span class="gw more"><button class="ib" id="moreBtn" type="button" data-tt="more"><svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/></svg><b id="moreBadge" hidden>!</b></button><div class="gmenu dd" id="moreDd" hidden></div></span>')
rep("</style>", """/* ---- folding header ---- */
header .gw.more,header .gw.famdd{display:none}
header.c1 .genb .runs span{display:none}
#ver{position:relative;top:2px}
header.c2 .icons>.ib:not(#gearBtn),header.c2 .icons>.gw:not(.more) .ib:not(#gearBtn){display:none}
header.c2 .icons>.ib#aboutBtn{display:none}header.c2 .gw.more{display:flex}
header.c3 #famTabs{display:none}header.c3 .gw.famdd{display:flex}
header.cc .conn .ip,header.cc .conn #connText{display:none}header.cc .hbox.conn{padding:0 12px}header.cb .bt{display:none}header.cb .hbox.hbrand{padding:0 7px}
.ddb{display:flex;align-items:center;gap:8px;background:var(--acc);color:var(--accText);border:0;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap}
.ddb svg{width:12px;height:12px}
.gmenu.dd{right:auto;left:0;width:auto;min-width:200px}.gw.more .gmenu.dd{left:auto;right:0}
.gmenu.dd .mi.act{color:var(--acc);font-weight:700}
</style>""")
rep("function openNotif() {", r"""const FOLD = ['c1', 'c2', 'cc', 'cb', 'c3'];   // order: "runs" label, icon buttons, connection text, brand texts, family tabs
function fitHeader() {
  const hd = document.querySelector('header'); if (!hd) return; const mid = hd.querySelector('.hmid'), ft = $('#famTabs');
  const act = ft && ft.querySelector('button.act'); $('#famDdTxt').textContent = act ? act.textContent : '';
  hd.classList.remove(...FOLD);
  const over = () => hd.scrollWidth > hd.clientWidth + 1 || (!hd.classList.contains('c3') && ft && mid && ft.scrollWidth > mid.clientWidth - 22);
  for (const c of FOLD) { if (!over()) break; hd.classList.add(c); }
  $('#moreBadge').hidden = $('#notifBadge').hidden;
}
function ddToggle(menu, btn, fill) {
  const open = menu.hidden; document.querySelectorAll('.gmenu.dd').forEach(m => m.hidden = true); if (!open) return;
  fill(menu); menu.hidden = false;
}
function initFold() {
  const more = $('#moreDd'), fd = $('#famDd');
  $('#moreBtn').onclick = e => { e.stopPropagation(); ddToggle(more, e.currentTarget, m => { m.replaceChildren();
    for (const [id, k] of [['wfBtn', 'wf'], ['infoBtn', 'ttInfo'], ['notifBtn', 'notif'], ['aboutBtn', 'about']]) {
      const b = h('button', {class: 'mi', type: 'button', text: t(k) + (id === 'notifBtn' && !$('#notifBadge').hidden ? '  !' : ''), onclick: ev => { ev.stopPropagation(); m.hidden = true; $('#' + id).click(); }}); m.append(b); } }); };
  $('#famDdBtn').onclick = e => { e.stopPropagation(); ddToggle(fd, e.currentTarget, m => { m.replaceChildren();
    $('#famTabs').querySelectorAll('button').forEach(src => m.append(h('button', {class: 'mi' + (src.classList.contains('act') ? ' act' : ''), type: 'button', text: src.textContent, title: src.title, onclick: ev => { ev.stopPropagation(); m.hidden = true; src.click(); }}))); }); };
  document.addEventListener('click', e => { document.querySelectorAll('.gmenu.dd').forEach(m => { if (!m.hidden && !m.contains(e.target)) m.hidden = true; }); });
  let raf = 0; const go = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(fitHeader); };
  if (window.ResizeObserver) new ResizeObserver(go).observe(document.querySelector('header')); addEventListener('resize', go);
  new MutationObserver(go).observe($('#famTabs'), {childList: true, subtree: true, attributes: true}); new MutationObserver(go).observe($('#notifBadge'), {attributes: true});
  go();
}
function openNotif() {""")
rep("initZoom(); initHelp(); initHost();", "initZoom(); initHelp(); initHost(); initFold();")
rep("licenseL: 'Licence', ", "licenseL: 'Licence', more: 'More', ")
rep("licenseL: 'Licenc', ", "licenseL: 'Licenc', more: 'Továbbiak', ")
# ---- content safety: 18+ check, blur, child protection, safe mode (logic in assets/safety.js) ----
_SS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'safety_strings.json'), encoding='utf-8'))
rep("mLearn: 'Learning mode (hints)', ", "mLearn: 'Learning mode (hints)', " + _SS['en'])
rep("mLearn: 'Tanuló mód (súgó)', ", "mLearn: 'Tanuló mód (súgó)', " + _SS['hu'])
rep('<label class="mi"><span data-t="mLearn"></span><span class="sw"><input type="checkbox" id="learnSw"><span></span></span></label>',
    '<label class="mi"><span data-t="mLearn"></span><span class="sw"><input type="checkbox" id="learnSw"><span></span></span></label>\n'
    '        <label class="mi"><span data-t="mNsfw"></span><span class="sw"><input type="checkbox" id="nsfwSw"><span></span></span></label>\n'
    '        <label class="mi"><span data-t="mSafe"></span><span class="sw"><input type="checkbox" id="safeSw"><span></span></span></label>')
rep("#modal a{color:var(--acc)}", """#modal a{color:var(--acc)}
#stage.nsfw #view{filter:blur(44px) saturate(.7)}
#stage.nsfwPend #view{visibility:hidden}
#stage.blocked #view{filter:blur(70px) brightness(.35)}
#nsfwCov{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;gap:10px;z-index:5;text-align:center;padding:20px;background:rgba(9,10,13,.35)}
#stage.nsfw #nsfwCov,#stage.blocked #nsfwCov{display:flex}
#stage.nsfw #nsfwCov{-webkit-backdrop-filter:blur(48px) saturate(.6);backdrop-filter:blur(48px) saturate(.6)}
#stage.blocked #nsfwCov{-webkit-backdrop-filter:blur(80px) brightness(.35);backdrop-filter:blur(80px) brightness(.35)}
#nsfwCov .eye{width:58px;height:58px;border-radius:50%;border:1px solid var(--line2);background:rgba(21,24,31,.85);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text);padding:0}
#nsfwCov .eye:hover{border-color:var(--acc);color:var(--acc)}
#nsfwCov .eye svg{width:28px;height:28px}
#nsfwCov b{font-size:15px}
#nsfwCov small{color:#b9c0cf;max-width:440px;line-height:1.45}
#stage.blocked #nsfwCov .eye{display:none}
#hist img.nsfw,#steps .chip img.nsfw,.iih img.nsfw{filter:blur(6px) saturate(.6)}
#hist img.ckpend,#steps .chip img.ckpend,.iih img.ckpend{visibility:hidden}
#nsfwHide{position:absolute;right:12px;bottom:12px;z-index:5;display:none;align-items:center;gap:6px;padding:6px 11px;border-radius:8px;border:1px solid var(--line2);background:rgba(21,24,31,.85);color:var(--text);font-size:12.5px;cursor:pointer}
#nsfwHide:hover{border-color:var(--acc);color:var(--acc)}
.imgpick .nembTag{display:none}
.imgpick.noemb .drop{border-color:var(--err)}
.imgpick.noemb .nembTag{display:block;position:absolute;left:50%;bottom:8px;transform:translateX(-50%);background:rgba(20,8,8,.85);color:#ffb4b4;border:1px solid var(--err);border-radius:6px;padding:2px 8px;font-size:11.5px;white-space:nowrap;z-index:2}
.imgpick.noemb .dropmsg{display:none}
#nsfwHide svg{width:16px;height:16px}
#stage.nsfwRev #nsfwHide{display:inline-flex}
.iiprev img.nsfw{filter:blur(18px) saturate(.6)}
.adck{display:flex;gap:9px;align-items:flex-start;margin:12px 0 14px;padding:10px 12px;border:1px solid var(--line2);border-radius:8px;background:var(--panel2);cursor:pointer;font-weight:600}
.adck input{margin-top:3px;accent-color:var(--acc)}
.btn.go2{background:var(--acc);border-color:var(--acc);color:var(--accText);font-weight:700}
.btn.go2:disabled{opacity:.45;cursor:not-allowed}
#wctl[hidden]{display:none!important}
body{-webkit-user-select:none;user-select:none}
input,textarea,[contenteditable="true"],pre,#modalBody p,#modalBody li,#modalBody td,#modalBody h3,#modalBody code{-webkit-user-select:text;user-select:text}
#modalBody button,#modalBody .btn,#modalBody label{-webkit-user-select:none;user-select:none}""")
rep("const HOST = !!(window.chrome && window.chrome.webview);", open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'safety.js'), encoding='utf-8').read() + "\nconst HOST = !!(window.chrome && window.chrome.webview);")
rep("initZoom(); initHelp(); initHost(); initFold();", "initZoom(); initHelp(); initHost(); initFold(); initSafety();")
# ---- support: "Buy me a coffee" button in the About header and a quiet link in the main header ----
COFFEE_URL = 'https://buymeacoffee.com/lalikavics'
MONKEY = ('<svg class="mk" viewBox="5 7 54 55" aria-hidden="true">'
  '<path d="M44 52c6 2 12-1 13-7" fill="none" stroke="#4a2a12" stroke-width="3" stroke-linecap="round"/>'
  '<ellipse cx="32" cy="48" rx="13" ry="11" fill="#5a3518"/><ellipse cx="32" cy="50" rx="8" ry="7" fill="#e0ad7e"/>'
  '<circle cx="13" cy="25" r="7" fill="#5a3518"/><circle cx="13" cy="25" r="4" fill="#e0ad7e"/><circle cx="51" cy="25" r="7" fill="#5a3518"/><circle cx="51" cy="25" r="4" fill="#e0ad7e"/>'
  '<circle cx="32" cy="25" r="17" fill="#5a3518"/>'
  '<path d="M20 26c0-6 5-9 8-7 2 1 6 1 8 0 3-2 8 1 8 7 0 8-5 12-12 12s-12-4-12-12z" fill="#e0ad7e"/>'
  '<ellipse cx="22" cy="31" rx="2.4" ry="1.5" fill="#f29a8a" opacity=".8"/><ellipse cx="42" cy="31" rx="2.4" ry="1.5" fill="#f29a8a" opacity=".8"/>'
  '<circle cx="26.3" cy="24" r="3.5" fill="#1a1305"/><circle cx="37.7" cy="24" r="3.5" fill="#1a1305"/><circle cx="27.5" cy="22.7" r="1.3" fill="#fff"/><circle cx="38.9" cy="22.7" r="1.3" fill="#fff"/>'
  '<ellipse cx="32" cy="33.2" rx="3.6" ry="3" fill="#5a1d14"/>'
  '<path d="M41.8 60.4L57.8 48.4 56 46 40 58z" fill="#c9852f" stroke="#8a5418" stroke-width=".8" stroke-linejoin="round"/>'
  '<path d="M31.5 32.5L56 46 40 58z" fill="#f6c453" stroke="#b8741f" stroke-width="1" stroke-linejoin="round"/>'
  '<circle cx="41" cy="45" r="2.5" fill="#d9442f"/><circle cx="47.5" cy="49" r="2.2" fill="#d9442f"/><circle cx="42.5" cy="52.5" r="2" fill="#d9442f"/><circle cx="46" cy="44.5" r="1.1" fill="#3f7d2c"/><circle cx="38" cy="40.5" r="1" fill="#3f7d2c"/>'
  '<path d="M46.5 56.2q.6 3.4 1.9 3.6 1.1-.2.8-3.4z" fill="#ffd36b"/>'
  '<path d="M28.6 33.6q3.4 2.6 6.8 0" fill="none" stroke="#e0ad7e" stroke-width="1.6" stroke-linecap="round"/>'
  '<circle cx="42" cy="56.5" r="3.6" fill="#5a3518"/><circle cx="54.5" cy="47.2" r="3.6" fill="#5a3518"/></svg>')
CUP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9h12v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5z"/><path d="M16 10h1.5a2.5 2.5 0 0 1 0 5H16"/><path d="M8 3.5c0 1 1 1 1 2s-1 1-1 2M12 3.5c0 1 1 1 1 2s-1 1-1 2"/></svg>'
rep("#modal a{color:var(--acc)}", """#modal a{color:var(--acc)}
#modal a.cof{display:none;align-items:center;gap:7px;background:var(--acc);color:var(--accText);border:1px solid #ffd27a;border-radius:8px;height:34px;box-sizing:border-box;padding:0 14px;font-size:14px;font-weight:750;text-decoration:none;white-space:nowrap;will-change:transform;box-shadow:0 2px 10px rgba(242,184,75,.25);transition:box-shadow .2s,transform .2s}
#modal.about a.cof{display:inline-flex}
#modal a.cof .more{display:inline-grid;grid-template-columns:0fr;opacity:0;will-change:opacity;transition:grid-template-columns .35s ease,opacity .35s ease}
#modal a.cof .in{display:inline-flex;align-items:center;gap:5px;min-width:0;overflow:clip;overflow-clip-margin:4px;white-space:nowrap}
#modal a.cof .mk{width:30px;height:30px;flex:0 0 30px;overflow:visible;transform-origin:50% 85%}
#modal a.cof:hover{box-shadow:0 3px 18px rgba(242,184,75,.55);transform:translateY(-1px)}
#modal a.cof:hover .more{grid-template-columns:1fr;opacity:1}
#modal a.cof:hover .mk{animation:afSway 1.75s ease-in-out -.875s infinite alternate}
@keyframes afSway{from{rotate:-4deg}to{rotate:4deg}}
@media (prefers-reduced-motion:reduce){#modal a.cof:hover .mk{animation:none}}
.cofm{display:none}
html.inhost .cofm{position:absolute;right:16px;top:38px;display:inline-flex;align-items:center;gap:5px;font-size:12px;color:#5f6676;text-decoration:none;padding:3px 7px;border-radius:6px;transition:color .2s,background .2s}
html.inhost header{position:relative}
.cofm svg{width:14px;height:14px}
.cofm:hover{color:var(--acc);background:rgba(242,184,75,.08)}""")
rep('<button class="btn sm" id="modalClose" type="button" data-t="close"></button>',
    '<a class="cof" id="cofBtn" href="' + COFFEE_URL + '" target="_blank" rel="noopener">☕ Buy me a coffee<span class="more"><span class="in">…or a pizza ' + MONKEY + '</span></span></a><button class="btn sm" id="modalClose" type="button" data-t="close"></button>')
rep("</header>", '<a class="cofm" id="cofMini" href="' + COFFEE_URL + '" target="_blank" rel="noopener" title="ArtFlawless Studio is free. Support is voluntary.">' + CUP + '<span>Buy me a coffee</span></a>\n</header>')
rep("function openAbout() {", """function initCoffee() {
  const m = $('#modal'), sync = () => m.classList.toggle('about', MODAL_KIND === 'about' && m.classList.contains('open'));
  new MutationObserver(sync).observe(m, {attributes: true, attributeFilter: ['class']});
  new MutationObserver(sync).observe($('#modalTitle'), {childList: true, characterData: true, subtree: true}); sync();
}
if (document.readyState === 'loading') addEventListener('DOMContentLoaded', initCoffee); else initCoffee();
function openAbout() {""")
# ---- contact: the project's GitHub page (REPO_URL file) ----
h = h.replace('__REPO_URL__', REPO_URL)
open(p, 'w', encoding='utf-8', newline='').write(h)

# ---- layout of the original workflow, used to arrange "Open a copy in ComfyUI" ----
_w = json.load(open(os.path.join(OUT, 'ArtFlawless-Studio-ZImageTurbo-EN.json'), encoding='utf-8'))
_tp = os.path.join(OUT, 'web', 'template.json')
_t = json.load(open(_tp, encoding='utf-8'))
_DECOR = ('MarkdownNote', 'Note', 'Fast Groups Bypasser (rgthree)', 'Label (rgthree)')
_lay = {'nodes': {}, 'groups': [], 'extra': []}
for _n in _w['nodes']:
    _lay['nodes'][str(_n['id'])] = [_n['pos'][0], _n['pos'][1], _n['size'][0], _n['size'][1]]
    if _n['type'] in _DECOR:
        _x = {k: _n[k] for k in ('id', 'type', 'pos', 'size', 'title', 'properties', 'color', 'bgcolor', 'flags') if k in _n}
        if _n.get('widgets_values') is not None:
            _x['widgets_values'] = [str(v).replace('ArtFlow workflow', 'ArtFlawless Studio workflow') if isinstance(v, str) else v for v in _n['widgets_values']]
        _lay['extra'].append(_x)
for _g in _w.get('groups', []):
    _lay['groups'].append({'title': _g['title'], 'bounding': _g['bounding'], 'color': _g.get('color')})
_t['layout'] = _lay
with open(_tp, 'w', encoding='utf-8') as f:
    json.dump(_t, f, ensure_ascii=False, separators=(',', ':'))

# ---- structured copy in ComfyUI + small fixes (1.2.0) ---------------------------
h = open(p, encoding='utf-8').read()
rep("openComfyCopy(); };", "openComfyCopy2(); };")
rep("function openNotif() {", r"""let LIC_OPEN = new Set();
const PP_OUT = ['prompt', 'width', 'height', 'shift', 'LoRA', 'refine', 'upscale', 'summary', 'base denoise', 'studio data', 'steps', 'cfg'];
const PP_IN = {a: 'theme', b: 'aspect ratio', c: 'prompt', d: 'own prompt', e: 'manual LoRA on', f: 'manual LoRA value', g: 'base LoRA on', h: 'start image denoise', i: 'default look on', j: 'steps (0 = theme)', k: 'cfg (0 = theme)', l: 'base size'};
function fixLinks(w, prompt) {
  // ComfyUI's API loader cannot connect dynamic slots (Power Puter outputs/inputs, extra switch inputs): add them and connect
  const g = w.app.rootGraph || w.app.graph, get = id => g.getNodeById(id) || g.getNodeById(Number(id)) || g.getNodeById(String(id)); let added = 0;
  for (const [id, nd] of Object.entries(prompt)) { if (!/^Power Puter/.test(nd.class_type)) continue; const n = get(id); if (!n) continue;
    const types = (nd.inputs.outputs && nd.inputs.outputs.outputs) || [];
    types.forEach((ty, i) => { if (!n.outputs[i]) n.addOutput(PP_OUT[i] || ('out ' + i), ty); else n.outputs[i].type = ty; if (PP_OUT[i]) n.outputs[i].label = PP_OUT[i]; }); }
  for (const [id, nd] of Object.entries(prompt)) { const n = get(id); if (!n) continue;
    for (const [k, v] of Object.entries(nd.inputs || {})) { if (!Array.isArray(v)) continue;
      let i = n.inputs ? n.inputs.findIndex(x => x.name === k) : -1; if (i >= 0 && n.inputs[i].link != null) continue;
      const src = get(v[0]); if (!src) continue;
      while (src.outputs && src.outputs.length <= v[1]) src.addOutput('out ' + src.outputs.length, '*');
      if (i < 0) { n.addInput(k, '*'); i = n.inputs.findIndex(x => x.name === k); }
      try { src.connect(v[1], n, i); added++; } catch (e) { console.warn('link', id, k, e); } } }
  for (const [id, nd] of Object.entries(prompt)) { if (!/^Power Puter/.test(nd.class_type)) continue; const n = get(id); if (!n) continue;
    for (const x of n.inputs || []) if (PP_IN[x.name]) x.label = x.name + ' = ' + PP_IN[x.name]; }
  return added;
}
function tidyCopy(w) {
  // a file browser of the prompt-manager pack pops up while widget values are applied; close it, and store the arranged graph in the tab
  let k = 0; const iv = w.setInterval(() => { w.document.querySelectorAll('.prompt-extractor-browser-overlay').forEach(e => e.remove()); if (++k > 20) w.clearInterval(iv); }, 250);
  try { const wf = w.app.extensionManager && w.app.extensionManager.workflow; const ct = wf && wf.activeWorkflow && wf.activeWorkflow.changeTracker; if (ct && ct.checkState) ct.checkState(); } catch (_) {}
}
function arrangeCopy(w, lay) {
  // positions, sizes, groups, guide and ON/OFF switches of the original workflow; Studio-only extra nodes go below the base-image group
  const L = w.LiteGraph, g = w.app.graph, ns = (g._nodes || g.nodes || []).slice(); const extras = [];
  const mx = Math.max(0, ...ns.map(n => Number(n.id) || 0)); if (g.state) g.state.lastNodeId = Math.max(g.state.lastNodeId || 0, mx + 200); g.last_node_id = Math.max(g.last_node_id || 0, mx + 200);
  for (const n of ns) { const p = lay.nodes[String(n.id)]; if (p) { n.pos = [p[0], p[1]]; const cs = n.computeSize ? n.computeSize() : n.size; n.size = [Math.max(p[2], cs[0]), Math.max(p[3], cs[1])]; } else extras.push(n); }
  const base = lay.groups.find(x => /^1\. /.test(x.title)); let gx = base ? base.bounding[0] + 40 : 3840, gy = base ? base.bounding[1] + base.bounding[3] + 60 : 1700, y0 = gy;
  for (const n of extras) { const cs = n.computeSize ? n.computeSize() : n.size; n.pos = [gx, gy]; n.size = [Math.max(360, cs[0]), cs[1]]; gy += n.size[1] + 50; }
  for (const k of Object.keys(T.groups)) if (!S.groups[k]) for (const id of T.groups[k].nodes) { const n = g.getNodeById(id) || g.getNodeById(Number(id)); if (n) n.mode = 4; }
  for (const gr of lay.groups) { const b = gr.bounding.slice(); if (base && gr === base && extras.length) b[3] = Math.max(b[3], gy - b[1] + 20);
    if (/^B · /.test(gr.title) && extras.length) b[3] = Math.max(b[3], gy - b[1] + 60);
    const G = new L.LGraphGroup(gr.title); if (G.configure) G.configure({title: gr.title, bounding: b, color: gr.color || '#3f789e', font_size: 24}); else { G.pos = [b[0], b[1]]; G.size = [b[2], b[3]]; G.color = gr.color; } g.add(G); }
  for (const x of lay.extra || []) { const n = L.createNode(x.type); if (!n) continue; g.add(n); n.pos = x.pos.slice(); n.size = x.size.slice(); if (x.title) n.title = x.title;
    n.properties = Object.assign(n.properties || {}, x.properties || {}); if (x.color) n.color = x.color; if (x.bgcolor) n.bgcolor = x.bgcolor; if (x.flags) n.flags = Object.assign(n.flags || {}, x.flags);
    if (x.widgets_values && n.widgets) x.widgets_values.forEach((v, i) => { if (n.widgets[i]) n.widgets[i].value = v; }); }
  g.setDirtyCanvas(true, true);
  const fit = () => { try { const c = w.app.canvas, el = c.canvas, cw = el.clientWidth, ch = el.clientHeight; if (!cw || !ch) return false;
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const gr of lay.groups) { const b = gr.bounding; x0 = Math.min(x0, b[0]); y0 = Math.min(y0, b[1]); x1 = Math.max(x1, b[0] + b[2]); y1 = Math.max(y1, b[1] + b[3]); }
    for (const x of lay.extra || []) { x0 = Math.min(x0, x.pos[0]); y0 = Math.min(y0, x.pos[1]); }
    const s = Math.min(cw / (x1 - x0 + 120), ch / (y1 - y0 + 120)); c.ds.scale = s; c.ds.offset = [-x0 + 60 / s, -y0 + 60 / s]; c.setDirty(true, true); return true; } catch (_) { return false; } };
  if (!fit()) { let k = 0; const iv = w.setInterval(() => { if (fit() || ++k > 40) w.clearInterval(iv); }, 300); }
}
function openComfyCopy2() {
  // a COPY of the full graph (switched-off groups are bypassed, not removed) – nothing done there flows back into the Studio
  const keep = JSON.stringify(S.groups); let prompt;
  try { for (const k of Object.keys(T.groups)) S.groups[k] = true; prompt = buildPrompt(S.seedRandom ? rndSeed() : (Number(S.seed) || 0), 0); } catch (e) { toast(t('buildErr', e.message), 'err'); return; }
  finally { S.groups = JSON.parse(keep); }
  const w = window.open(API + '/', '_blank'); let n = 0; const fam = (famInfo(FAMILY) || {}).label || FAMILY;
  const tm = setInterval(async () => { n++;
    try { if (w && w.app && typeof w.app.loadApiJson === 'function' && w.app.graph && w.LiteGraph) { clearInterval(tm); await w.app.loadApiJson(prompt, 'ArtFlawless ' + fam + ' (copy).json'); await new Promise(r => setTimeout(r, 1200));
      try { fixLinks(w, prompt); } catch (e) { console.warn('links', e); }
      try { if (T.layout) arrangeCopy(w, T.layout); } catch (e) { console.warn('arrange', e); } tidyCopy(w); toast(t('copyOk')); return; } } catch (_) {}
    if (n > 80 || !w || w.closed) { clearInterval(tm); downloadJson(prompt, 'ArtFlawless-copy-api.json'); toast(t('copyErr'), 'err'); } }, 500);
}
function openNotif() {""")
# the "where is what" message disappears as soon as a generation starts
rep("  $('#stageSpin').hidden = n === 0; }", "  $('#stageSpin').hidden = n === 0; if (n) $('#empty').hidden = true; }")
# themed scrollbars
rep("/* ---- learning mode ---- */", "/* ---- scrollbars ---- */\n*{scrollbar-width:thin;scrollbar-color:#343a49 transparent}\n*::-webkit-scrollbar{width:10px;height:10px}*::-webkit-scrollbar-track{background:transparent}\n*::-webkit-scrollbar-thumb{background:#2c3240;border-radius:8px;border:2px solid var(--bg)}*::-webkit-scrollbar-thumb:hover{background:#3d4456}\n/* ---- learning mode ---- */")
# ---- Hungarian prompting: HU -> EN translation of the prompt (logic in assets/hu_prompt.js, backend in studio_init.py) ----
rep("#modal a{color:var(--acc)}", """#modal a{color:var(--acc)}
.hub{border:1px solid var(--line2);border-radius:8px;padding:9px 11px;background:var(--panel2);display:flex;flex-direction:column;gap:7px}
.hub .f.inline{margin:0}
.hub .tag,.mi .tag{font-size:10.5px;border:1px solid var(--line2);border-radius:5px;padding:1px 5px;color:var(--muted);margin-left:6px;font-weight:400}
.hub .dl{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--line);padding-top:8px}
.hub .row,.tr .row{display:flex;gap:8px;align-items:center}
.hub .pbar{flex:1;height:6px;background:#2a2f3c;border-radius:4px;overflow:hidden}.hub .pbar i{display:block;height:100%;background:var(--acc);transition:width .3s}
.btn.acc{border-color:var(--acc);color:var(--acc)}
.tr{border:1px dashed var(--line2);border-radius:8px;padding:8px 10px;background:#11141a;display:flex;flex-direction:column;gap:6px}
.tr[hidden]{display:none}
.tr .th{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.tr .th b{color:var(--acc);font-weight:600}
.tr textarea{background:transparent;border-color:transparent;padding:4px 2px;resize:vertical;line-height:1.45}
.tr textarea:hover{border-color:var(--line2)}
.tr textarea:focus{border-color:var(--acc);background:var(--bg)}
.tr.busy textarea{opacity:.55}
.tr .ft{display:flex;flex-direction:column;gap:6px}
.tr .ft .row{justify-content:space-between;align-items:flex-start}
.tr .hint.warn{color:#f3dfa6}
.gmenu .mi[hidden]{display:none}""")
rep('        <label class="mi"><span data-t="mSafe"></span><span class="sw"><input type="checkbox" id="safeSw"><span></span></span></label>',
    '        <label class="mi"><span data-t="mSafe"></span><span class="sw"><input type="checkbox" id="safeSw"><span></span></span></label>\n'
    '        <label class="mi" id="huMi" hidden><span>Magyar promptolás <span class="tag">HU → EN</span></span><span class="sw"><input type="checkbox" id="huSw"><span></span></span></label>')
rep("const HOST = !!(window.chrome && window.chrome.webview);", open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'hu_prompt.js'), encoding='utf-8').read() + "\nconst HOST = !!(window.chrome && window.chrome.webview);")
# ---- model / LoRA family check and time estimate (assets/studio_extras.js, backend /artflow/model-kind) ----
rep("const HOST = !!(window.chrome && window.chrome.webview);", open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'studio_extras.js'), encoding='utf-8').read() + "\nconst HOST = !!(window.chrome && window.chrome.webview);")
rep("const classes = [...new Set([...Object.values(T.prompt).map(n => n.class_type), 'LoraLoaderModelOnly', 'Image Saver', 'Image Saver Simple'])];",
    "const classes = [...new Set([...Object.values(T.prompt).map(n => n.class_type), 'LoraLoaderModelOnly', 'Image Saver', 'Image Saver Simple', 'KSampler',\n"
    "    ...(T.family === 'custom' ? ['CheckpointLoaderSimple', 'UNETLoader', 'UnetLoaderGGUF', 'CLIPLoader', 'DualCLIPLoader', 'VAELoader', 'ModelSamplingAuraFlow', 'FluxGuidance', 'EmptySD3LatentImage'] : [])])];")
# ---- CUSTOM tab: universal model loader + LoRA fit / trigger words (assets/custom_universal.js, backend /artflow/model-kind, /artflow/lora-match) ----
rep("const HOST = !!(window.chrome && window.chrome.webview);", open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'custom_universal.js'), encoding='utf-8').read() + "\nconst HOST = !!(window.chrome && window.chrome.webview);")
rep("#progText{white-space:nowrap;", ".cuinfo{font-size:12px;margin-top:2px}.cuinfo.bad{color:var(--err)}.cuhw{font-size:12px;border-radius:6px;padding:5px 8px;margin-top:2px}.cuhw:empty{display:none}"
    ".cuhw.ok{color:#7fd19b;background:rgba(79,179,122,.08)}.cuhw.mid{color:#e8c46a;background:rgba(224,179,65,.10)}.cuhw.bad{color:#f08b78;background:rgba(229,101,79,.12)}"
    ".cuset{display:flex;flex-direction:column;gap:8px;margin-top:6px;padding:10px;border:1px solid var(--line);border-radius:8px}.cuset input[type=text]{width:100%}"
    ".lorax{display:flex;flex-direction:column;gap:4px;margin:-2px 0 6px 6px;font-size:11.5px}.lorax:empty{display:none}.lorax .lrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap}"
    ".lfit{font-weight:600}.lfit.ok{color:#7fd19b}.lfit.part{color:#e8c46a}.lfit.bad{color:#f08b78}.lfit.na{color:var(--muted)}.lora.lbad select{color:var(--muted)}"
    ".ltrig{display:flex;flex-wrap:wrap;gap:4px;align-items:center}.tchip{font:11px inherit;padding:2px 7px;border-radius:10px;border:1px solid var(--line);background:transparent;color:inherit;cursor:pointer}"
    ".tchip:hover{border-color:var(--acc);color:var(--acc)}.tchip.sub{opacity:.75;font-size:10.5px}.ltags summary{cursor:pointer;font-size:11px;margin:2px 0}.ltags .ltrig{margin-top:3px}\n#progText{white-space:nowrap;")
rep("#progText{white-space:nowrap;", "#eta{white-space:nowrap;font-variant-numeric:tabular-nums;margin-right:6px}\n#progText{white-space:nowrap;")
rep(".conn .ip{font:10.5px ui-monospace,Consolas,monospace;color:#5d6475;text-align:center}",
    ".conn .ip{font:10.5px ui-monospace,Consolas,monospace;color:#5d6475;text-align:center}\n"
    ".conn .cw{gap:0}.conn .ct{line-height:13px}.conn .ip{line-height:11px;margin-top:1px}"
    ".conn .lms{display:grid;gap:1px;margin-top:3px}.conn .lm{display:flex;align-items:center;gap:5px;font:9px/9px ui-monospace,Consolas,monospace;color:#7c8396}"
    ".conn .lml{width:22px}.conn .lmb{width:58px;height:3px;border-radius:3px;background:#262b36;overflow:hidden}"
    ".conn .lmb i{display:block;height:100%;width:0;background:#4fb37a;transition:width .4s}.conn .lmb i.mid{background:#e0b341}.conn .lmb i.hi{background:#e5654f}"
    ".conn .lmv{width:28px;text-align:right;color:#aab1c2}")
rep("initSafety();", "initSafety(); initHuPrompt();")
rep("initSafety(); initHuPrompt();", "initSafety(); initHuPrompt(); initExtras();")
rep("      h('div', {class: 'note', id: 'promptHint', hidden: true}),\n      field('46', 'value', t('prompt'), {rows: 9}),\n      mini(t('neg'), field('51', 'value', T.family === 'sdxl' ? t('negHintX') : t('negHint'), {rows: 3})),",
    "      h('div', {class: 'note', id: 'promptHint', hidden: true}),\n      huPrompt(),\n      field('46', 'value', huActive() ? HUS.label : t('prompt'), {rows: huActive() ? 7 : 9}),\n      huDetect(),\n      huTrans('p'),\n      mini(t('neg'), field('51', 'value', T.family === 'sdxl' ? t('negHintX') : t('negHint'), {rows: 3}), huTrans('n')),")
rep("    ], false)\n  );\n  const pr = (p, n) =>", "    ], false)\n  );\n  huBoxes();\n  const pr = (p, n) =>")
rep("function renderControls() {\n  const lookId = T.ids && T.ids.look;", "function renderControls() {\n  huLookDefault(); const lookId = T.ids && T.ids.look;")
rep("function applyLang() {\n  document.documentElement.lang = LANG;", "function applyLang() {\n  document.documentElement.lang = LANG; { const hm = $('#huMi'); if (hm) hm.hidden = LANG !== 'hu'; }")
open(p, 'w', encoding='utf-8', newline='').write(h)
