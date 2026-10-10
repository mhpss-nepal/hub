/* Historical reading adapter. Authenticated private backend -> memory-only presentation.
   No operational collector, record store, queue, register reader or publisher is called. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var panel = $('historical-baseline'), current = null, generation = 0, controller = null, readAt = null;
  var ENDPOINT = 'https://mhpss5ws-tdp3xtfnsq-as.a.run.app/admin/baseline/analytics';
  var keys = ['schema', 'version', 'classification', 'historical_entries', 'known_service_contacts',
    'unknown_count_entries', 'unverified_form_entries', 'backup_capture_utc', 'original_export_date',
    'historical_date_status', 'unit', 'combine_classes'];
  function validDay(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    var date = new Date(value + 'T00:00:00.000Z');
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
  }
  function validCapture(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$/.test(value) || !validDay(value.slice(0, 10))) return false;
    var parts = value.slice(11, 19).split(':').map(Number);
    return parts[0] < 24 && parts[1] < 60 && parts[2] < 60 && Number.isFinite(Date.parse(value));
  }
  function validate(x) {
    return window.HistoricalAnalytics.validate(x);
  }
  var linkPending = false;
  function setStatus(message, focus) {
    $('historical-status').textContent = message;
    if (focus) $('historical-status').focus();
  }
  function syncActions(user) {
    $('historical-refresh').hidden = !user;
    $('historical-export').hidden = !user || !current;
    $('historical-account').hidden = !user;
    if (!user) $('historical-account').open = false;
  }
  function card(value, label, note) {
    var c = document.createElement('div'); c.className = 'stat';
    [['k', label], ['v', value], ['s', note]].forEach(function (pair) {
      var e = document.createElement('div'); e.className = pair[0]; e.textContent = pair[1]; c.appendChild(e);
    }); return c;
  }
  function render() {
    var stats = $('historical-stats'); stats.replaceChildren();
    $('historical-results').hidden = !current;
    syncActions(window.BaselineAuth && window.BaselineAuth.currentUser());
    if (!current) {
      $('historical-provenance').textContent = '';
      $('historical-summary').textContent = '';
      window.HistoricalAnalytics.clear();
      return;
    }
    window.HistoricalAnalytics.render(current, readAt);
    setStatus('Updated ' + readAt.slice(11,16) + ' UTC · historical source, not current reporting.');
  }
  function show() {
    panel.hidden = false;
    document.body.classList.add('historical-entry');
    $('source-tools').open = false;
    $('entry-shell').hidden = true;
    $('app').hidden = true;
    $('access-options').open = false;
  }
  function hide() { panel.hidden = true; document.body.classList.remove('historical-entry'); $('source-tools').open = true; }
  function clear(message) {
    generation += 1;
    if (controller) controller.abort(); controller = null;
    current = null; readAt = null; render();
    setStatus(typeof message === 'string' ? message : 'Historical view cleared. Refresh to read the private backend again.');
  }
  async function refresh() {
    clear('Reading the private historical backend…');
    var auth = window.BaselineAuth, user = auth && auth.currentUser();
    if (!user) { clear('Sign in with the enabled primary administrator account to read the private baseline.'); return; }
    var mine = generation, abort = new AbortController(); controller = abort;
    var timeout = setTimeout(function () { abort.abort(); }, 30000);
    try {
      var token = await auth.token();
      if (mine !== generation || auth.currentUser() !== user) return;
      var response = await fetch(ENDPOINT, { method: 'GET', headers: { Authorization: 'Bearer ' + token },
        credentials: 'omit', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', signal: abort.signal });
      token = null;
      if (mine !== generation || auth.currentUser() !== user) return;
      if (response.status !== 200) throw Error(response.status === 401 || response.status === 403 ? 'Private baseline access refused. Sign in again or check primary administrator access.' : 'Private baseline unavailable. Retry when online.');
      var text = await response.text();
      if (text.length > 131072) throw Error('Private reader response refused.');
      var value = validate(JSON.parse(text));
      if (mine !== generation || auth.currentUser() !== user) return;
      current = value; readAt = new Date().toISOString(); render();
    } catch (e) {
      if (mine !== generation) return;
      current = null; readAt = null; render();
      setStatus(e.name === 'AbortError' ? 'Private baseline unavailable: request timed out or cancelled. Retry when online.' : e.message === 'Private baseline access refused. Sign in again or check primary administrator access.' ? e.message : 'Private baseline unavailable or invalid. Retry when online; no figures substituted.');
    } finally { clearTimeout(timeout); if (mine === generation) controller = null; }
  }
  function csv() {
    if (!current || !window.BaselineAuth.currentUser()) return '';
    return window.HistoricalAnalytics.csv();
  }
  $('historical-refresh').addEventListener('click', refresh);
  $('historical-login-form').addEventListener('submit', async function (event) {
    event.preventDefault();
    try {
      var email = $('historical-email').value.trim(), password = $('historical-password').value;
      if (password || event.submitter === $('historical-password-signin')) {
        await window.BaselineAuth.signIn(email, password);
      } else if (linkPending) {
        await window.BaselineAuth.finishLink(email);
      } else {
        await window.BaselineAuth.sendLink(email);
        setStatus('Sign-in link requested. Open it in this browser.');
      }
    }
    catch (e) { clear('Sign-in failed. Check your account and try again.'); setStatus($('historical-status').textContent, true); }
    finally { $('historical-password').value = ''; }
  });
  $('historical-link').addEventListener('click', async function () {
    try { await window.BaselineAuth.sendLink($('historical-email').value.trim()); setStatus('Sign-in link requested. Open it in this browser.'); }
    catch (e) { clear('Sign-in link unavailable. Check your email address and connection.'); }
  });
  $('historical-signout').addEventListener('click', function () { clear('Signed out view cleared.'); window.BaselineAuth.signOut().catch(function () { setStatus('Sign-out unavailable. Close this private view and retry when online.'); }); });
  $('historical-clear').addEventListener('click', clear);
  $('historical-export').addEventListener('click', function () {
    var content = csv();
    if (!content) return;
    var url = URL.createObjectURL(new Blob(['\ufeff' + content], { type: 'text/csv;charset=utf-8' }));
    var a = document.createElement('a'); a.href = url; a.download = 'private-historical-summary.csv'; a.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });
  $('useHistorical').addEventListener('click', function () { if (!window.BASELINE_ONLY) { location.search = '?source=historical'; return; } show(); refresh(); });
  ['useDemo', 'useLive', 'useLocal', 'file', 'file2', 'drop'].forEach(function (id) {
    var e = $(id); if (e) e.addEventListener(id === 'file' || id === 'file2' ? 'change' : id === 'drop' ? 'drop' : 'click', function () { clear(); hide(); }, true);
  });
  // The legacy arrival observer may repaint its placeholder shell. Hide only
  // that placeholder while this separate historical presentation is active.
  new MutationObserver(function () {
    if (!panel.hidden && !$('entry-shell').hidden) $('entry-shell').hidden = true;
  }).observe($('entry-shell'), { attributes: true, attributeFilter: ['hidden'] });
  clear();
  var source = new URLSearchParams(location.search).get('source');
  if (!source || source === 'historical') show();
  else hide();
  if (window.BaselineAuth) {
    window.BaselineAuth.onChange(function (user, state) {
      clear(state.error || (user ? 'Reading the private historical backend…' : 'Sign in with the enabled primary administrator account to read the private baseline.'));
      linkPending = !!state.linkPending;
      $('historical-login').hidden = !!user && !linkPending;
      $('historical-signin').textContent = linkPending ? 'Complete email sign-in' : 'Send sign-in link';
      $('historical-signout').hidden = !user;
      syncActions(user);
      if (user && !panel.hidden) refresh();
    });
    window.addEventListener('offline', function () { clear('Private baseline unavailable offline. Refresh after reconnecting.'); });
    window.addEventListener('online', function () { if (!panel.hidden) refresh(); });
  }
  // Enter legacy live mode only through a full, explicit source switch.
  if (window.BASELINE_ONLY) $('useLive').addEventListener('click', function () { location.search = '?source=live'; }, true);
})();
