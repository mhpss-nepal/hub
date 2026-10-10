/* Select before any legacy bridge initialization. No datastore/queue access. */
(function () {
  'use strict';
  var source = new URLSearchParams(location.search).get('source');
  window.BASELINE_ONLY = !source || source === 'historical';
  document.write('<script src="assets/' + (window.BASELINE_ONLY ? 'baseline-auth.js' : 'fb.js') + '"><\/script>');
})();
