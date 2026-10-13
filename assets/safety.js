/* ---------- content safety: 18+ check, blur, child protection ----------
   SPDX-License-Identifier: GPL-3.0-or-later
   - every shown image is checked locally (/artflow/check); adult images are blurred while the content filter is on
   - prompts with nudity / sexual words ask once for an 18+ confirmation
   - a minor together with nudity / sexual content is always refused (cannot be switched off)
   - safe mode adds "no nudity" words to the negative prompt (can be switched off)
   Getting around these protections, or changing the program to do so, is the user's own responsibility. */
const LS_SAFE = 'artflow.studio.safety.v1';
let SAFE = {filter: true, safe: true, adult: false, adultAt: ''};
try { Object.assign(SAFE, JSON.parse(localStorage.getItem(LS_SAFE) || '{}')); } catch (_) {}
const SAFE_URL = () => API + '/api/userdata/' + encodeURIComponent('artflow/safety.json');
const SAFE_TEST = (() => { try { return localStorage.getItem('artflow.studio.safety.test') === '1'; } catch (_) { return false; } })();   // developer test: treat every image as 18+
const SAFE_NEG = 'nsfw, nude, naked, nudity, nipples, genitals, explicit, sexual, porn, erotic';
function saveSafe() {
  try { localStorage.setItem(LS_SAFE, JSON.stringify(SAFE)); } catch (_) {}
  fetch(SAFE_URL() + '?overwrite=true', {method: 'POST', body: JSON.stringify(SAFE)}).catch(() => {});
  syncSafeUi();
}
async function loadSafe() {
  try { const r = await fetch(SAFE_URL(), {cache: 'no-store'}); if (r.ok) { const j = await r.json(); if (j && typeof j === 'object') Object.assign(SAFE, j); } } catch (_) {}
  syncSafeUi();
}
function syncSafeUi() { const a = $('#nsfwSw'), b = $('#safeSw'); if (a) a.checked = !!SAFE.filter; if (b) b.checked = !!SAFE.safe; applyGuard(); }

/* word lists: accents removed, lower case; "*" = word start */
const fold = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const WL = list => list.map(fold);
const W_ADULT = WL(['nude', 'nudes', 'naked', 'nudity', 'nsfw', 'topless', 'bottomless', 'nipple*', 'areola*', 'genital*', 'vagina*', 'vulva*', 'labia', 'pussy', 'pussies',
  'penis*', 'cock', 'cocks', 'dick', 'dicks', 'erection*', 'testicle*', 'scrotum', 'clitoris', 'anus', 'anal', 'sex', 'sexual*', 'porn*', 'hentai', 'erotic*', 'explicit',
  'xxx', 'fetish*', 'bdsm', 'bondage', 'orgasm*', 'masturbat*', 'blowjob*', 'handjob*', 'fellatio', 'cunnilingus', 'cum', 'cumshot*', 'creampie', 'ejaculat*', 'intercourse',
  'lewd', 'striptease', 'stripper*', 'undress*', 'unclothed', 'no clothes', 'without clothes', 'no clothing', 'bare breast*', 'breasts out', 'spread legs', 'rule34', 'r34',
  'meztelen*', 'pucer*', 'anyaszult*', 'felmeztelen*', 'ruhatlan*', 'ruha nelkul', 'vetkoz*', 'sztriptiz*', 'szex', 'szexel*', 'szexualis*', 'porno*', 'erotik*',
  'mellbimbo*', 'nemi szerv*', 'nemiszerv*', 'punci*', 'pina', 'pinaja', 'fasz', 'faszat', 'faszt', 'penisz*', 'himvesszo*', 'vagin*', 'csiklo*', 'maszturb*',
  'onkielegit*', 'orgazmus*', 'kozosul*', 'szeretkez*']);
const W_SEXY = WL(['sexy', 'seductive*', 'sensual*', 'provocative*', 'lingerie', 'underwear', 'panties', 'thong', 'suggestive', 'flirt*', 'lust*', 'arous*', 'kinky',
  'szexi', 'csabito*', 'kihivo*', 'fehernemu*', 'bugyi*', 'tanga', 'erzeki*', 'buja']);
const W_MINOR = WL(['child', 'children', 'childs', 'childlike', 'kid', 'kids', 'kiddie*', 'toddler*', 'infant*', 'newborn*', 'minor', 'minors', 'underage*', 'under age',
  'preteen*', 'pre teen*', 'tween', 'tweens', 'teen', 'teens', 'teenage*', 'teenager*', 'schoolgirl*', 'schoolboy*', 'school girl*', 'school boy*', 'loli', 'lolis',
  'lolicon', 'lolita*', 'shota*', 'young girl*', 'young boy*', 'little girl*', 'little boy*', 'kindergarten*', 'elementary school*', 'middle school*', 'junior high',
  'grade school*', 'jailbait', 'pubescent', 'prepubescent', 'puberty',
  'gyerek*', 'gyermek*', 'kisgyerek*', 'kislany*', 'kisfiu*', 'kiskoru*', 'fiatalkoru*', 'tini', 'tinik', 'tinit', 'tinedzser*', 'kamasz*', 'serdulo*', 'iskolas*',
  'ovodas*', 'csecsemo*', 'ujszulott*', 'diaklany*', 'diakfiu*']);
const W_BABY = WL(['baby', 'babies', 'baba', 'babak', 'babat', 'bebi*']);
const AGE_RE = /\b(?:[1-9]|1[0-7])\s*(?:yo|y o|yrs? old|years? old|year old|eves|eves kor\w*)\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen) (?:years? old|year old|yo)\b|\b(?:egy|ket|ketto|harom|negy|ot|hat|het|nyolc|kilenc|tiz|tizen\w*) eves\b/;
function hasWord(text, list) {
  const toks = text.split(' ').filter(Boolean); const joined = ' ' + toks.join(' ') + ' ';
  return list.some(w => { const pre = w.endsWith('*'), k = pre ? w.slice(0, -1) : w;
    if (k.includes(' ')) return joined.includes(' ' + k + (pre ? '' : ' '));
    return pre ? toks.some(x => x.startsWith(k)) : toks.includes(k); });
}
function verdict(raw) {
  const text = fold(raw).replace(/[^a-z0-9]+/g, ' ').trim();
  const adult = hasWord(text, W_ADULT), sexy = hasWord(text, W_SEXY);
  const minor = hasWord(text, W_MINOR) || AGE_RE.test(text), baby = hasWord(text, W_BABY);
  return {adult, block: (minor && (adult || sexy)) || (baby && adult)};
}
function userPromptText() { return [val('46', 'value'), (S.loras || []).filter(L => L && L.on).map(L => L.lora).join(' ')].join(' '); }

/* image checks */
const CK = new Map(); const REVEAL = new Set(); const BLOCKED = new Set(); let CK_NA = false;
function qp(url) { try { const u = new URL(url, location.href); return {filename: u.searchParams.get('filename'), subfolder: u.searchParams.get('subfolder') || '', type: u.searchParams.get('type') || 'output'}; } catch (_) { return null; } }
const vUrl = q => API + '/view?filename=' + encodeURIComponent(q.filename) + '&subfolder=' + encodeURIComponent(q.subfolder || '') + '&type=' + encodeURIComponent(q.type || 'output');
function renameUrl(a, b) {
  for (const k of Object.keys(R.steps)) R.steps[k] = R.steps[k].map(u => u === a ? b : u);
  if (R.cur === a) R.cur = b; let ch = false; H = H.map(x => { if (x.url === a) { ch = true; return Object.assign({}, x, {url: b}); } return x; });
  if (ch) { try { localStorage.setItem(LS_HIST, JSON.stringify(H)); } catch (_) {} }
  if (REVEAL.has(a)) REVEAL.add(b);
  if (R.shown === a) { R.shown = b; $('#view').src = b; }
  renderSteps(); renderHistory();
}
function checkImg(url) {
  if (!url || /^(blob|data):/.test(url) || CK.has(url)) return;
  const q = qp(url); if (!q || !q.filename || (q.type !== 'output' && q.type !== 'temp')) { CK.set(url, {st: 'ok'}); return; }
  const e = {st: 'pend'}; CK.set(url, e);
  fetch(API + '/artflow/check', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(q)})
    .then(r => r.json()).then(j => {
      if (j.error || j.nsfw == null) { e.st = 'na'; if (!CK_NA && j.nsfw === null) { CK_NA = true; toast(t('ckNa'), 'err'); } }
      else e.st = (j.nsfw || SAFE_TEST) ? 'nsfw' : 'ok';
      if (j.moved) { const nu = vUrl(j.moved); CK.set(nu, {st: e.st}); renameUrl(url, nu); }
    }).catch(() => { e.st = 'na'; }).finally(applyGuard);
}
function hiddenUrl(url) {
  if (!url) return false; if (BLOCKED.has(url)) return 'blocked';
  if (/^blob:/.test(url)) return SAFE.filter && R.liveAdult ? 'nsfw' : false;
  if (!SAFE.filter || REVEAL.has(url)) return false;
  const st = (CK.get(url) || {}).st; return st === 'nsfw' ? 'nsfw' : st === 'pend' ? 'pend' : false;
}
function applyGuard() {
  const stg = $('#stage'); if (!stg) return; const v = $('#view'); const hid = v.hidden ? false : hiddenUrl(R.shown);
  stg.classList.toggle('nsfw', hid === 'nsfw'); stg.classList.toggle('nsfwPend', hid === 'pend'); stg.classList.toggle('blocked', hid === 'blocked');
  const cov = $('#nsfwCov'); if (cov) { cov.querySelector('b').textContent = t(hid === 'blocked' ? 'blkT' : hid === 'pend' ? 'ckPend' : 'nsfwT');
    cov.querySelector('small').textContent = hid === 'blocked' ? t('blkS') : t('nsfwS'); }
  document.querySelectorAll('#hist img, #steps .chip img, .iih img').forEach(i => { const hh = hiddenUrl(i.getAttribute('src')); i.classList.toggle('nsfw', !!hh); });
}
const _show = show;
show = function (url, badgeKey, live) { _show(url, badgeKey, live); R.shown = url; if (!live) checkImg(url); applyGuard(); };
const _renderSteps = renderSteps;
renderSteps = function () { _renderSteps(); for (const id of Object.keys(R.steps)) (R.steps[id] || []).forEach(checkImg); applyGuard(); };
const _renderHistory = renderHistory;
renderHistory = function () { _renderHistory(); H.forEach(x => checkImg(x.url)); applyGuard(); };
const _openInfo = openInfo;
openInfo = function () { _openInfo(); H.forEach(x => checkImg(x.url)); applyGuard(); };
let INFO_SRC = null;
document.addEventListener('click', e => { const i = e.target.closest && e.target.closest('.iih img'); if (i) INFO_SRC = i.getAttribute('src'); }, true);
const _showInfo = showInfo;
showInfo = function (meta, url) {
  const src = INFO_SRC; INFO_SRC = null; _showInfo(meta, url);
  const img = document.querySelector('#iiOut .iiprev img'); if (!img || !SAFE.filter) return;
  const txt = meta ? [meta.parameters, meta.prompt].filter(Boolean).join(' ') : '';
  if ((src && hiddenUrl(src)) || (txt && verdict(txt).adult)) {
    img.classList.add('nsfw'); img.title = t('nsfwShow'); img.style.cursor = 'pointer';
    img.addEventListener('click', () => { img.classList.remove('nsfw'); if (src) REVEAL.add(src); applyGuard(); }, {once: true});
  }
};
const _buildPrompt = buildPrompt;
buildPrompt = function (seed, cnt) {
  if (!SAFE.safe || !T.prompt['51']) return _buildPrompt(seed, cnt);
  const k = '51.value', had = Object.prototype.hasOwnProperty.call(S.vals, k), old = S.vals[k];
  const base = String(had ? old : (T.prompt['51'].inputs.value || '')).trim();
  S.vals[k] = base + (base && !/,\s*$/.test(base) ? ', ' : base ? ' ' : '') + SAFE_NEG;
  try { return _buildPrompt(seed, cnt); } finally { if (had) S.vals[k] = old; else delete S.vals[k]; }
};
const _finish = finish;
finish = async function (id, ok) {
  await _finish(id, ok);
  if (ok && R.texts['91'] && verdict(R.texts['91']).block) {   // the final prompt (e.g. from an image description) turned out to be forbidden
    const urls = new Set(); for (const k of Object.keys(R.steps)) (R.steps[k] || []).forEach(u => urls.add(u));
    for (const u of urls) { BLOCKED.add(u); const q = qp(u); if (q && q.filename) fetch(API + '/artflow/check', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.assign(q, {discard: true}))}).catch(() => {}); }
    H = H.filter(x => !urls.has(x.url)); try { localStorage.setItem(LS_HIST, JSON.stringify(H)); } catch (_) {} renderHistory(); renderSteps(); blockedModal();
  }
};
const _run = run;
run = async function () {
  if (!T) return _run();
  // 1d "read embedded prompt": for A1111 / Civitai images (also the Studio's own) the Studio reads the prompt itself,
  // because the extractor node picks the first text field of the embedded graph (e.g. the face detailer's)
  if (S.groups['1d'] && T.prompt['48']) {
    const nm = val('48', 'image'); let r = null;
    if (nm && nm !== '(none)') { try { const [sub, fn] = splitName(nm); const buf = await (await fetch(API + '/view?filename=' + encodeURIComponent(fn) + '&subfolder=' + encodeURIComponent(sub) + '&type=input')).arrayBuffer(); const meta = await readMeta(buf); if (meta && meta.parameters) r = parseA1111(meta.parameters); } catch (_) {} }
    if (r && r.pos) {
      const keep = {g: S.groups['1d'], p: S.vals['46.value'], n: S.vals['51.value'], hp: '46.value' in S.vals, hn: '51.value' in S.vals};
      S.groups['1d'] = false; S.vals['46.value'] = r.pos.replace(/<lora:[^>]+>/g, '').trim(); if (r.neg != null) S.vals['51.value'] = r.neg;
      try { return await run(); } finally { S.groups['1d'] = keep.g; if (keep.hp) S.vals['46.value'] = keep.p; else delete S.vals['46.value']; if (keep.hn) S.vals['51.value'] = keep.n; else delete S.vals['51.value']; save(); }
    }
  }
  const v = verdict(userPromptText());
  if (v.block) { blockedModal(); return; }
  if (v.adult && !SAFE.adult && !(await adultModal('prompt'))) return;
  R.liveAdult = v.adult;
  return _run();
};
function blockedModal() {
  MODAL_KIND = 'blocked'; $('#modalTitle').textContent = t('blkT');
  const body = $('#modalBody'); body.replaceChildren(h('p', {text: t('blkP1')}), h('p', {text: t('blkP2')}),
    h('p', {class: 'muted', text: t('blkP3')}),
    h('div', {class: 'row', style: 'justify-content:flex-end'}, h('button', {class: 'btn sm', type: 'button', text: t('okBtn'), onclick: () => $('#modal').classList.remove('open')})));
  $('#modal').classList.add('open');
}
function adultModal(why) {
  return new Promise(res => {
    MODAL_KIND = 'adult'; $('#modalTitle').textContent = t('adT'); let done = false;
    const fin = v => { if (done) return; done = true; obs.disconnect(); $('#modal').classList.remove('open'); res(v); };
    const cb = h('input', {type: 'checkbox', id: 'adCb'}); const go = h('button', {class: 'btn sm go2', type: 'button', text: t('adGo'), disabled: true});
    cb.onchange = () => { go.disabled = !cb.checked; };
    go.onclick = () => { SAFE.adult = true; SAFE.adultAt = new Date().toISOString(); saveSafe(); fin(true); };
    const body = $('#modalBody'); body.replaceChildren(h('p', {text: t(why === 'filter' ? 'adP1f' : 'adP1')}), h('p', {text: t('adP2')}),
      SAFE.safe && why !== 'filter' ? h('p', {class: 'muted', text: t('adSafe')}) : null,
      h('label', {class: 'adck'}, cb, h('span', {text: t('adCb')})),
      h('div', {class: 'row', style: 'justify-content:flex-end;gap:8px'}, h('button', {class: 'btn sm', type: 'button', text: t('closeNoC'), onclick: () => fin(false)}), go));
    $('#modal').classList.add('open');
    const obs = new MutationObserver(() => { if (!$('#modal').classList.contains('open')) fin(false); }); obs.observe($('#modal'), {attributes: true, attributeFilter: ['class']});
  });
}
function initSafety() {
  const st = $('#stage'); const cov = h('div', {id: 'nsfwCov'}, h('button', {class: 'eye', type: 'button', title: t('nsfwShow')}),
    h('b'), h('small')); cov.querySelector('.eye').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l18 18"/><path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c6 0 9.5 7 9.5 7a17 17 0 0 1-2.6 3.4M6.3 6.4C3.9 8 2.5 12 2.5 12S6 19 12 19c1.8 0 3.3-.5 4.6-1.2"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';
  cov.querySelector('.eye').onclick = e => { e.stopPropagation(); if (R.shown && !BLOCKED.has(R.shown)) { REVEAL.add(R.shown); applyGuard(); } };
  cov.addEventListener('wheel', e => e.stopPropagation()); cov.addEventListener('mousedown', e => e.stopPropagation());
  st.append(cov);
  $('#nsfwSw').onchange = async e => { if (!e.target.checked && !SAFE.adult && !(await adultModal('filter'))) { e.target.checked = true; return; } SAFE.filter = e.target.checked; saveSafe(); };
  $('#safeSw').onchange = e => { SAFE.safe = e.target.checked; saveSafe(); };
  syncSafeUi(); loadSafe().then(() => { renderHistory(); });
  setTimeout(() => fetch(API + '/artflow/check-status').then(r => r.json()).then(j => { if (!j.nudenet && !j.falconsai) { if (!CK_NA) { CK_NA = true; toast(t('ckNa'), 'err'); } } else if (!j.nudenet || !j.falconsai) toast(t('ckPart', j.nudenet ? 'Falconsai' : 'NudeNet')); }).catch(() => {}), 2500);
}
