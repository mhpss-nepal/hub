/* Historical reading adapter. Private summary file -> memory-only presentation.
   No operational collector, record store, queue, register reader or publisher is called. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var panel = $('historical-baseline'), current = null, generation = 0;
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
    if (!x || Array.isArray(x) || typeof x !== 'object' || Object.keys(x).sort().join('|') !== keys.slice().sort().join('|')) throw Error('Not a minimized historical summary. Use the supplied private summary file, not a full record export.');
    if (x.schema !== 'mhpss-private-historical-summary-v1' || x.version !== 'historical-master-v1' ||
      x.classification !== 'private-owner-reading' || x.unit !== 'service contacts, not unique people' ||
      x.combine_classes !== false || x.historical_date_status !== 'unresolved-bs-dates') throw Error('Unsupported summary contract.');
    ['historical_entries', 'known_service_contacts', 'unknown_count_entries', 'unverified_form_entries'].forEach(function (k) {
      if (!Number.isSafeInteger(x[k]) || x[k] < 0) throw Error('Invalid count: ' + k);
    });
    if (x.unknown_count_entries > x.historical_entries) throw Error('Unknown counts exceed historical entries.');
    if (!validDay(x.original_export_date) || !validCapture(x.backup_capture_utc)) throw Error('Invalid source date.');
    return Object.freeze(Object.assign({}, x));
  }
  function setStatus(message) { $('historical-status').textContent = message; }
  function card(value, label, note) {
    var c = document.createElement('div'); c.className = 'stat';
    [['k', label], ['v', value], ['s', note]].forEach(function (pair) {
      var e = document.createElement('div'); e.className = pair[0]; e.textContent = pair[1]; c.appendChild(e);
    }); return c;
  }
  function render() {
    var stats = $('historical-stats'); stats.replaceChildren();
    $('historical-results').hidden = !current;
    if (!current) {
      $('historical-provenance').textContent = '';
      $('historical-summary').textContent = '';
      return;
    }
    var x = current;
    stats.appendChild(card(x.historical_entries.toLocaleString('en-GB'), 'Historical entries', 'Entries, not unique sessions'));
    stats.appendChild(card(x.known_service_contacts.toLocaleString('en-GB'), 'Known service contacts', 'Not unique people; incomplete total'));
    stats.appendChild(card(x.unknown_count_entries.toLocaleString('en-GB'), 'Entries with unknown counts', 'Unknown, never zero'));
    stats.appendChild(card('—', 'Organisations', 'Not available in this minimized summary'));
    stats.appendChild(card('—', 'Site coverage', 'No validated denominator'));
    $('historical-provenance').textContent = 'Historical ministry source · original export ' + x.original_export_date +
      ' · retained backup captured ' + x.backup_capture_utc + ' · version ' + x.version +
      '. Historical BS reporting dates remain unresolved. These dates are not a current response period.';
    $('historical-summary').textContent = x.unverified_form_entries.toLocaleString('en-GB') +
      ' later form entries are retained separately with trial legitimacy unverified. Their contacts are excluded from the historical figures. No combined achievement, unique-person, trend, sex/age or geographic claim is made.';
    setStatus('Private historical summary loaded in page memory only. Not live cloud data. No record import, save, queue, synchronization or public publication. Reload or Clear removes this view.');
  }
  function show() {
    panel.hidden = false;
    $('entry-shell').hidden = true;
    $('app').hidden = true;
    $('access-options').open = false;
  }
  function hide() { panel.hidden = true; }
  function clear() {
    generation += 1; current = null; $('historical-file').value = ''; render();
    setStatus('No historical data attached. Import the supplied private summary file. It stays in page memory and is not uploaded.');
  }
  function read(file) {
    var mine = ++generation;
    current = null; render();
    if (!file || file.size > 16384) { clear(); setStatus('No file loaded: choose a minimized summary smaller than 16 KB.'); return; }
    setStatus('Reading the private summary…');
    file.text().then(function (text) {
      if (mine !== generation) return;
      try { current = validate(JSON.parse(text)); render(); }
      catch (e) { current = null; render(); setStatus('Not loaded: ' + e.message); }
    }).catch(function () {
      if (mine !== generation) return;
      current = null; render(); setStatus('Not loaded: the file could not be read.');
    });
  }
  function csv() {
    if (!current) return '';
    var x = current;
    return 'version,historical_entries,known_service_contacts,unknown_count_entries,unverified_form_entries,unit,backup_capture_utc,original_export_date,historical_date_status,scope\r\n' +
      [x.version, x.historical_entries, x.known_service_contacts, x.unknown_count_entries, x.unverified_form_entries,
        'service contacts; not unique people', x.backup_capture_utc, x.original_export_date,
        x.historical_date_status, 'all historical entries; later forms excluded from contacts'].join(',') + '\r\n';
  }
  $('historical-file').addEventListener('change', function (e) { read(e.target.files[0]); });
  $('historical-clear').addEventListener('click', clear);
  $('historical-export').addEventListener('click', function () {
    if (!current) return;
    var url = URL.createObjectURL(new Blob(['\ufeff' + csv()], { type: 'text/csv;charset=utf-8' }));
    var a = document.createElement('a'); a.href = url; a.download = 'private-historical-summary.csv'; a.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });
  $('useHistorical').addEventListener('click', show);
  ['useDemo', 'useLive', 'useLocal', 'file', 'file2', 'drop'].forEach(function (id) {
    var e = $(id); if (e) e.addEventListener(id === 'file' || id === 'file2' ? 'change' : id === 'drop' ? 'drop' : 'click', hide, true);
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
})();
