/* Presentation-only Layer 2 navigation. No data, Auth, queue or storage access. */
(function () {
  'use strict';
  // Canonical arrival aliases preserve every Auth action parameter and hash.
  var arrival = new URL(location.href), source = arrival.searchParams.get('source');
  if (!/\/review-(?:current-v51|analytics-v48)\//.test(arrival.pathname) && (!source || source === 'historical')) {
    var destination = new URL(source === 'historical' ? 'review-analytics-v48/' : 'review-current-v51/', arrival);
    destination.search = arrival.search; destination.hash = arrival.hash;
    location.replace(destination.href); return;
  }
  var historicalButton = document.getElementById('useHistorical');
  if (historicalButton && !window.BASELINE_ONLY) historicalButton.addEventListener('click', function () { location.href = 'review-analytics-v48/?source=historical'; });
  var rail = document.querySelector('.l2-shell .rail');
  if (!rail) return;
  var menu = document.querySelector('.l2-menu'), close = rail.querySelector('.l2-close');
  var backdrop = document.querySelector('.l2-backdrop');
  var phone = window.matchMedia('(max-width:899px)');
  var inerted = [];
  function setOpen(open, returnFocus) {
    if (open && !phone.matches) return;
    document.body.classList.toggle('l2-menu-open', open);
    menu.setAttribute('aria-expanded', String(open));
    backdrop.hidden = !open;
    if (open) {
      rail.setAttribute('role', 'dialog'); rail.setAttribute('aria-modal', 'true');
      Array.from(document.body.children).forEach(function (el) {
        if (el === rail || el === backdrop || el.tagName === 'SCRIPT' || el.inert) return;
        el.inert = true; inerted.push(el);
      });
      close.focus();
    } else {
      rail.removeAttribute('role'); rail.removeAttribute('aria-modal');
      inerted.forEach(function (el) { el.inert = false; }); inerted = [];
      if (returnFocus) menu.focus();
    }
  }
  menu.addEventListener('click', function () { setOpen(true); });
  close.addEventListener('click', function () { setOpen(false, true); });
  backdrop.addEventListener('click', function () { setOpen(false, true); });
  document.addEventListener('keydown', function (e) {
    if (!document.body.classList.contains('l2-menu-open')) return;
    if (e.key === 'Escape') { e.preventDefault(); setOpen(false, true); }
    if (e.key !== 'Tab') return;
    var nodes = Array.from(rail.querySelectorAll('a[href],button')).filter(function (el) { return el.getClientRects().length; });
    var first = nodes[0], last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  phone.addEventListener('change', function () { setOpen(false); });
  function mark() {
    var path = location.pathname;
    var key = /\/review-current-v51\/(?:index.html)?$/.test(path) ? 'current' : /\/review-analytics-v48\/(?:index.html)?$/.test(path) ? 'historical' : new URLSearchParams(location.search).get('source') === 'demo' ? 'sample' : '';
    rail.querySelectorAll('[data-destination]').forEach(function (a) {
      if (a.dataset.destination === key) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    if (document.body.classList.contains('l2-menu-open')) setOpen(false, true);
  }
  window.__railMark = mark;
  window.addEventListener('hashchange', mark);
  rail.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
  mark();
})();
