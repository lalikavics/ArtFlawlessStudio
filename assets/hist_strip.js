/* ---------- history strip: a header (open / close triangle in the middle, image count on the right), the thumbnails,
   and on the right a narrow panel with the thumbnail size slider. Collapsed it is one row that shows only whole images;
   open it shows the whole output folder, and its top edge (above the status line) can be dragged to any height ---------- */
const HX_SIZES = [40, 54, 72, 96, 128];   // the steps of the + and - buttons; the slider itself is stepless
const HX_MIN = 40, HX_MAXS = 128;
const HX = {exp: false, px: 54, total: 0, h: 0, adHide: false};   // px: thumbnail size, h: height of the open strip (0 = two rows)
const LS_HX = 'artflow.studio.histui.v2';
const HXS = {
  hu: {open: 'Kibontás: a teljes output mappa', close: 'Összecsukás', size: 'Bélyegkép mérete', count: '{0} kép', adHide: 'A 18+ képek elrejtése a listából', adShow: 'A 18+ képek megjelenítése a listában', adNone: 'Nincs 18+ kép a mappában', folder: 'Az output mappa megnyitása', ui: 'A felület frissítése (modell- és LoRA-listák, katalógus, képek)', uiBusy: 'Generálás közben nem frissíthető.', reload: 'A lista frissítése (új képek a mappából)'},
  en: {open: 'Expand: the whole output folder', close: 'Collapse', size: 'Thumbnail size', count: '{0} images', adHide: 'Hide the 18+ images from the list', adShow: 'Show the 18+ images in the list', adNone: 'There are no 18+ images in the folder', folder: 'Open the output folder', ui: 'Refresh the interface (model and LoRA lists, catalog, images)', uiBusy: 'Not while a generation is running.', reload: 'Refresh the list (new images in the folder)'}
};
const hxs = (k, a) => String((HXS[LANG] || HXS.en)[k]).replace('{0}', a);
function histLimit() { return 0; }   // 0 = every image of the folder (the collapsed strip shows the first ones)
function hxSave() { try { localStorage.setItem(LS_HX, JSON.stringify({exp: HX.exp, px: HX.px, h: HX.h, pxSet: HX.pxSet || 0, adHide: !!HX.adHide})); } catch (_) {} }
function hxFit() {   // whole thumbnails that fit into one row at this size
  const b = $('#hist'); if (!b) return 0; const cs = getComputedStyle(b);
  const w = b.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  return Math.max(1, Math.floor((w + 6) / (HX.px + 6)));
}
let HX_N = 0;   // how many thumbnails the collapsed strip shows now
// every thumbnail element is made once and kept (HX_EL), with a small cached thumbnail as its picture, so changing the
// size or the number of images that fit only moves elements that are already loaded and decoded
const HX_EL = new Map();
function hxThumb(x) {
  const q = qp(x.url); if (!q || q.type !== 'output' || !q.filename) return x.url;
  return API + '/artflow/thumb?filename=' + encodeURIComponent(q.filename) + '&subfolder=' + encodeURIComponent(q.subfolder || '') + '&type=output&m=' + (x.t || '');
}
function hxEl(x) {
  let i = HX_EL.get(x.url); if (i) return i;
  i = h('img', {src: hxThumb(x), alt: '', draggable: 'false', decoding: 'async'}); i.dataset.u = x.url;
  i.onerror = () => { if (i.dataset.fb) { H = H.filter(y => y.url !== x.url); HX_EL.delete(x.url); i.remove(); return; } i.dataset.fb = '1'; i.src = x.url; };   // no thumbnail: the image itself
  HX_EL.set(x.url, i); return i;
}
function hxWarm() {   // loads the thumbnails of the whole folder in the background, a few at a time
  const todo = H.filter(x => !HX_EL.has(x.url)); let k = 0;
  const step = () => { const end = Math.min(todo.length, k + 12); for (; k < end; k++) hxEl(todo[k]); if (k < todo.length) setTimeout(step, 60); };
  step();
  const keep = new Set(H.map(x => x.url)); for (const u of [...HX_EL.keys()]) if (!keep.has(u)) HX_EL.delete(u);
}
// an image of the 18+ subfolder (or one the check found adult) is an adult image of the list
function hxAdult(u) { const q = qp(u); const sub = String((q && q.subfolder) || '').replace(/\\/g, '/'); return sub === '18+' || sub.startsWith('18+/') || (CK.get(u) || {}).st === 'nsfw'; }
const hxList = () => HX.adHide ? H.filter(x => !hxAdult(x.url)) : H;
renderHistory = function () {
  const b = $('#hist'); if (!b) return; const all = hxList();
  const list = HX.exp ? all : all.slice(0, hxFit()); HX_N = list.length;
  b.replaceChildren(...list.map(x => { const i = hxEl(x); i.title = t('seed', x.seed == null ? '?' : x.seed); return i; }));
  list.forEach(x => ckByFolder(x.url));
  hxBar(); applyGuard(); setTimeout(hxWarm, 300);
};
addHistory = function (url) {
  if (!url) return; H = [{url, seed: R.seed, t: Date.now()}, ...H.filter(x => x.url !== url)]; HX.total = Math.max(HX.total + 1, H.length);
  try { localStorage.setItem(LS_HIST, JSON.stringify(H.slice(0, 120))); } catch (_) {} renderHistory();
};
// height of the collapsed strip: one row of thumbnails, but never less than the icon stack on its right needs
const hxRowH = () => { const sz = $('#hxSize'); let need = 78; if (sz) { const cs = getComputedStyle(sz); need = Math.max(need, [...sz.children].reduce((a, c) => a + c.offsetHeight, 0) + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) + parseFloat(cs.rowGap || 0) * Math.max(0, sz.children.length - 1)); } return Math.max(need, HX.px + 12); };
function hxMax() {   // the strip may grow until the viewer above keeps 160 pixels
  const st = $('#stage'), hb = $('#hist'); if (!st || !hb) return 600;
  return Math.max(hxRowH(), hb.offsetHeight + st.offsetHeight - 160);
}
function hxBar() {
  const bar = $('#histBar'); if (!bar) return;
  const tr = bar.querySelector('.hxt'); tr.classList.toggle('open', HX.exp); tr.title = hxs(HX.exp ? 'close' : 'open');
  const nAd = H.filter(x => hxAdult(x.url)).length; const shown = HX.adHide ? Math.max(0, HX.total - nAd) : HX.total;
  bar.querySelector('.hxn').textContent = HX.total ? hxs('count', shown) : '';
  const eye = bar.querySelector('.hxe'); if (eye) { eye.classList.toggle('hid', !!HX.adHide); eye.classList.toggle('none', !nAd);
    eye.innerHTML = HX.adHide ? HX_EYE_OFF : HX_EYE; eye.title = !nAd ? hxs('adNone') : hxs(HX.adHide ? 'adShow' : 'adHide'); }
  const pop = $('#hxPop'); if (pop) { pop.querySelector('.trk i').style.left = 'calc((100% - 12px) * ' + ((HX.px - HX_MIN) / (HX_MAXS - HX_MIN)).toFixed(4) + ')'; pop.querySelector('.hxv').textContent = HX.px + ' px'; }
  const hb = $('#hist'); hb.classList.toggle('exp', HX.exp); hb.style.setProperty('--hs', HX.px + 'px');
  const row = $('#hxRow'); if (row) { row.style.height = HX.exp ? Math.max(hxRowH(), HX.h ? Math.min(HX.h, hxMax()) : HX.px * 2 + 18) + 'px' : ''; row.style.minHeight = HX.exp ? '' : hxRowH() + 'px'; }
}
function hxSetPx(px) {   // stepless size; the collapsed strip is rebuilt only when another number of images fits
  px = Math.round(Math.min(HX_MAXS, Math.max(HX_MIN, px))); if (px === HX.px) return; HX.px = px; hxBar();
  if (!HX.exp && Math.min(hxFit(), hxList().length) !== HX_N) renderHistory();
}
function hxGrip() {   // the top edge of the thumbnail panel: drag it up or down to make the strip taller or shorter
  const g = h('div', {id: 'histGrip'}); $('#histBox').prepend(g);
  g.addEventListener('mousedown', e => {
    if (e.button !== 0) return; e.preventDefault(); e.stopPropagation();
    const y0 = e.clientY, h0 = $('#hxRow').offsetHeight, max = hxMax(); document.body.classList.add('hxdrag');
    const pxUser = HX.exp ? HX.px : (HX.pxSet || HX.px);   // the size the user chose; the drag never changes it for good
    const mv = ev => {
      const nh = Math.min(max, h0 + (y0 - ev.clientY));
      // lower than one row of the chosen size: the thumbnails shrink with the strip, step by step, down to 69 px
      const px = Math.round(Math.min(pxUser, Math.max(HX_ROW_PX, nh - 12)));
      if (px !== HX.px) { HX.px = px; if (!HX.exp) renderHistory(); }
      // folded only at the lowest height of the strip (with 69 px thumbnails)
      if (px <= HX_ROW_PX && nh <= hxRowH() + 1) { if (HX.exp) { HX.exp = false; HX.h = 0; HX.pxSet = pxUser; hxBar(); renderHistory(); } else hxBar(); return; }
      HX.h = Math.round(nh); if (!HX.exp) { HX.exp = true; hxBar(); syncHistory().then(() => renderHistory()); } else hxBar();
    };
    const up = () => { removeEventListener('mousemove', mv); removeEventListener('mouseup', up); document.body.classList.remove('hxdrag'); hxSave(); };
    addEventListener('mousemove', mv); addEventListener('mouseup', up);
  });
}
const HX_EYE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/></svg>';
const HX_EYE_OFF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l18 18"/><path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c6 0 9.5 7 9.5 7a17 17 0 0 1-2.6 3.4M6.3 6.4C3.9 8 2.5 12 2.5 12S6 19 12 19c1.8 0 3.3-.5 4.6-1.2"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';
const HX_ROW_PX = 69;   // thumbnail size of the collapsed strip
async function hxSetExp(on) { if (!on && HX.exp) HX.pxSet = HX.px; if (on && !HX.exp && HX.pxSet) HX.px = HX.pxSet; HX.exp = on; if (!on) HX.px = HX_ROW_PX; if (on && HX.h && HX.h < hxRowH() * 1.5) HX.h = 0; hxSave(); hxBar(); if (on) await syncHistory(); renderHistory(); if (!on) $('#hist').scrollTop = 0; }
function initHist() {
  try { const s = JSON.parse(localStorage.getItem(LS_HX) || 'null'); if (s) { HX.exp = !!s.exp; HX.px = Math.min(HX_MAXS, Math.max(HX_MIN, +s.px || 54)); HX.h = Math.max(0, s.h | 0); HX.pxSet = +s.pxSet || 0; HX.adHide = !!s.adHide; } } catch (_) {}
  // the centre column becomes two rounded panels like the side ones: the viewer with its status line, steps and texts,
  // and below it the thumbnail panel
  const view = h('div', {id: 'viewCard'}); $('#stage').parentNode.insertBefore(view, $('#stage'));
  view.append($('#stage'), $('#prog'), $('#steps'), $('#infoWrap'));
  const hb = $('#hist'); const box = h('div', {id: 'histBox'});
  hb.parentNode.insertBefore(box, hb);
  const tri = h('button', {class: 'hxt', type: 'button'}); tri.innerHTML = '<svg viewBox="0 0 10 6"><path d="M1 5.2 5 1l4 4.2z" fill="currentColor"/></svg>';
  tri.onclick = () => hxSetExp(!HX.exp);
  // right panel: thumbnail size (a small horizontal slider pops up beside the icon) and the output folder
  const ico = (title, svg) => { const b = h('button', {type: 'button', class: 'hxi', title}); b.innerHTML = svg; return b; };
  const szBtn = ico(hxs('size'), '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/></svg>');
  const fdBtn = ico(hxs('folder'), '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.2h7a2 2 0 0 1 2 2v7.8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/></svg>');
  fdBtn.onclick = () => openFolder(API + '/view?filename=&subfolder=&type=output');
  const trk = h('div', {class: 'trk'}, h('i'));
  const fromX = x => { const r = trk.getBoundingClientRect(); const f = (x - r.left - 6) / Math.max(1, r.width - 12); hxSetPx(HX_MIN + Math.min(1, Math.max(0, f)) * (HX_MAXS - HX_MIN)); };
  trk.addEventListener('pointerdown', e => { e.preventDefault(); trk.setPointerCapture(e.pointerId); fromX(e.clientX);
    const mv = ev => fromX(ev.clientX), up = () => { trk.removeEventListener('pointermove', mv); trk.removeEventListener('pointerup', up); hxSave(); };
    trk.addEventListener('pointermove', mv); trk.addEventListener('pointerup', up); });
  const pop = h('div', {id: 'hxPop', hidden: true}, h('span', {class: 'hxl', text: '−'}), trk, h('span', {class: 'hxl', text: '+'}), h('span', {class: 'hxv'}));
  pop.addEventListener('wheel', e => { e.preventDefault(); hxSetPx(HX.px + (e.deltaY < 0 ? 4 : -4)); hxSave(); }, {passive: false});
  const popShow = on => { pop.hidden = !on; szBtn.classList.toggle('on', on); if (on) { const r = szBtn.getBoundingClientRect(), br = box.getBoundingClientRect(); pop.style.top = (r.top - br.top + r.height / 2) + 'px'; hxBar(); } };
  szBtn.onclick = () => popShow(pop.hidden);
  document.addEventListener('mousedown', e => { if (!pop.hidden && !pop.contains(e.target) && !szBtn.contains(e.target)) popShow(false); }, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !pop.hidden) popShow(false); });
  const rlBtn = ico(hxs('reload'), '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/></svg>');
  rlBtn.onclick = async () => { rlBtn.classList.add('spin'); await pruneMissing(); renderHistory(); setTimeout(() => rlBtn.classList.remove('spin'), 500); };
  const sz = h('div', {id: 'hxSize'}, szBtn, fdBtn, rlBtn);
  const eye = h('button', {class: 'hxe', type: 'button'}); eye.onclick = () => { HX.adHide = !HX.adHide; hxSave(); renderHistory(); };
  box.append(h('div', {id: 'histBar'}, h('span', {class: 'hxn'}), eye, tri), h('div', {id: 'hxRow'}, hb, sz), pop);
  let rt = null; new ResizeObserver(() => { if (HX.exp) return; clearTimeout(rt); rt = setTimeout(() => { if (Math.min(hxFit(), hxList().length) !== HX_N) renderHistory(); }, 60); }).observe(hb);
  hxGrip(); hxBar(); syncHistory().then(ok => { if (ok) renderHistory(); });
  // images deleted or moved in Explorer leave the strip, the viewer and the step chips: checked every few seconds while the
  // Studio is visible (the window's focus event does not always reach the page), and when it becomes visible again
  setInterval(() => { if (!document.hidden && !(R.jobs && R.jobs.size)) pruneMissing(); }, 4000);
  renderSteps();
}
// before the first image (or when its files are gone) the step bar shows its chip and buttons greyed out, so the layout
// stays the same
// a small "refresh the interface" button at the right end of the step bar: re-reads the model and LoRA lists, the
// catalog and the output folder and redraws the panels in place (no page reload, so nothing flashes): the arrow turns
// for about a second while the panels fade softly and come back
const UI_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/></svg>';   // the same arrow as on the thumbnail panel
let UI_BUSY = false;
async function uiRefresh(btn) {
  if (UI_BUSY) return; if (R.jobs && R.jobs.size) { toast(hxs('uiBusy')); return; }
  UI_BUSY = true; btn.classList.add('spin'); const t0 = Date.now();
  const cols = [$('#colL'), $('#colR')].filter(Boolean); const sc = cols.map(c => c.scrollTop);
  document.body.classList.add('uiFade');
  try { await loadOI(); await loadCatalog(); await pruneMissing(); } catch (_) {}
  await new Promise(r => setTimeout(r, Math.max(0, 700 - (Date.now() - t0))));
  try { renderControls(); } catch (_) {}
  cols.forEach((c, i) => { c.scrollTop = sc[i]; });
  renderHistory(); applyGuard();
  await new Promise(r => setTimeout(r, Math.max(0, 1000 - (Date.now() - t0))));
  document.body.classList.remove('uiFade'); UI_BUSY = false; renderSteps();
}
function uiBtn() { const b = h('button', {class: 'btn sm uiRl' + (UI_BUSY ? ' spin' : ''), type: 'button', title: hxs('ui')}); b.innerHTML = UI_SVG; b.onclick = () => uiRefresh(b); return b; }
const _hxSteps = renderSteps;
renderSteps = function () {
  _hxSteps(); const box = $('#steps'); if (!box) return;
  // more than one step: a small triangle between the step thumbnails shows the order they were made in
  const chips = [...box.querySelectorAll('.chip:not(.off)')];
  if (chips.length >= 2) chips.slice(1).forEach(c => c.before(h('span', {class: 'stepArr', 'aria-hidden': 'true'})));
  if (R.cur) { box.append(uiBtn()); return; }
  const dis = (text) => h('button', {class: 'btn sm', type: 'button', text, disabled: true});
  if (!box.querySelector('.chip')) box.append(h('div', {class: 'chip off'}, h('i', {class: 'ph'}), t('s8')));
  box.append(...[h('span', {class: 'sp'}), dis(t('open')), dis(t('download')), T && T.groups && T.groups['1e'] ? dis(t('useStart')) : null, uiBtn()].filter(Boolean));
};

/* ---------- longer explanations fold away behind a small triangle in front of their label (opened ones are remembered) ---------- */
const HF_OPEN = new Set();
function foldHints(root) {
  (root || document).querySelectorAll('.hint:not([data-hf])').forEach(e => {
    e.dataset.hf = '1'; if ((e.textContent || '').trim().length < 60) return;
    const p = e.parentElement; if (!p) return;
    if (e.dataset.short) {   // a one-line summary stays visible; its triangle opens the full explanation under it
      const key = 's:' + e.dataset.short; const tog = h('button', {class: 'hfold', type: 'button'}, h('i'));
      const sh = h('div', {class: 'hint hshort', 'data-hf': '1'}, tog, h('span', {text: e.dataset.short}));
      const set = on => { tog.classList.toggle('open', on); e.classList.toggle('hfx', !on); if (on) HF_OPEN.add(key); else HF_OPEN.delete(key); };
      const flip = ev => { ev.preventDefault(); ev.stopPropagation(); set(e.classList.contains('hfx')); };
      sh.addEventListener('click', flip); sh.style.cursor = 'pointer'; p.insertBefore(sh, e); set(HF_OPEN.has(key)); return;
    }
    let anchor = e.previousElementSibling; if (!anchor) anchor = p.previousElementSibling; if (!anchor) return;
    if (anchor.matches('.f.inline, .f')) { const l = anchor.querySelector('label, .lab') || anchor; anchor = l; }
    const key = (e.textContent || '').trim().slice(0, 48);
    const tog = h('button', {class: 'hfold', type: 'button', title: LANG === 'hu' ? 'Bővebben' : 'More'}, h('i'));
    const set = on => { tog.classList.toggle('open', on); e.classList.toggle('hfx', !on); if (on) HF_OPEN.add(key); else HF_OPEN.delete(key); };
    tog.addEventListener('click', ev => { ev.preventDefault(); ev.stopPropagation(); set(e.classList.contains('hfx')); });
    anchor.insertBefore(tog, anchor.firstChild); set(HF_OPEN.has(key));
  });
}
// "output mappába" / "output folder" in the panel texts opens the output folder, like the folder buttons
function linkOutput() {
  const re = /output (mappába|mappa|folder)/;
  for (const root of [$('#colL'), $('#colR')]) {
    if (!root) continue;
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n => re.test(n.nodeValue) && !(n.parentElement && n.parentElement.closest('.olink, textarea, select, option, button')) ? 1 : 3});
    const hits = []; let n; while ((n = tw.nextNode())) hits.push(n);
    for (const node of hits) {
      const m = re.exec(node.nodeValue); if (!m) continue;
      const after = node.splitText(m.index); after.splitText(m[0].length);
      const a = h('span', {class: 'olink', title: hxs('folder'), text: m[0]});
      a.addEventListener('click', ev => { ev.preventDefault(); ev.stopPropagation(); openFolder(API + '/view?filename=&subfolder=&type=output'); });
      after.replaceWith(a);
    }
  }
}
(() => { let t = 0; const run = () => { t = 0; foldHints(); linkOutput(); };
  new MutationObserver(() => { if (!t) t = requestAnimationFrame(run); }).observe(document.body, {childList: true, subtree: true}); })();
