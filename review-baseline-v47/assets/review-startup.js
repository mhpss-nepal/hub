/* This route can only read the private baseline. Preserve Auth action parameters. */
(function () {
  'use strict';
  window.BASELINE_ONLY = true;
  var url = new URL(location.href);
  if (url.searchParams.get('source') !== 'historical') {
    url.searchParams.set('source', 'historical');
    history.replaceState({}, document.title, url.pathname + url.search + url.hash);
  }
})();
