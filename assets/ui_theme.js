/* ---------- interface design: "frosted aluminium" (default) or the classic one; the settings item is hidden for now,
   Ctrl+Shift+F12 switches between them (not Ctrl+Alt: that is AltGr on Hungarian keyboards) ---------- */
const LS_UI = 'artflow.studio.ui';
const UIS = {hu: 'Új kezelőfelület (frosted, próba)', en: 'New interface (frosted, trial)'};
function uiFrost() { return document.documentElement.classList.contains('ui2'); }
function setUiTheme(on) {
  const a = document.getElementById('uiA'), b = document.getElementById('uiB'); if (!a || !b) return;
  a.media = on ? 'not all' : 'all'; b.media = on ? 'all' : 'not all'; document.documentElement.classList.toggle('ui2', on);
  try { localStorage.setItem(LS_UI, on ? 'frost' : 'classic'); } catch (_) {}
  const s = $('#uiSw'); if (s) s.checked = on;
  requestAnimationFrame(() => { try { if (typeof measureFold === 'function') { measureFold(); applyFold(); } renderHistory(); } catch (_) {} });
}
function initUiTheme() {
  const tx = () => { const e = $('#uiMiT'); if (e) e.textContent = UIS[LANG] || UIS.en; }; tx();
  const s = $('#uiSw'); if (s) { s.checked = uiFrost(); s.onchange = e => setUiTheme(e.target.checked); }
  const _al = applyLang; applyLang = function () { _al.apply(this, arguments); tx(); };
  document.addEventListener('keydown', e => { if (e.ctrlKey && e.shiftKey && !e.altKey && e.key === 'F12') { e.preventDefault(); setUiTheme(!uiFrost()); } });
}
