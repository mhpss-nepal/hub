/* Same project and Firebase Auth provider as the website. Auth-only: no Firestore
   import, legacy queue reader/flush, role lookup, report watcher or publication. */
(function () {
  'use strict';
  var SDK = 'https://www.gstatic.com/firebasejs/10.13.0/', auth, api, user = null, callbacks = [], ready = false, error = '';
  function notify() { callbacks.forEach(function (f) { f(user, { ready: ready, error: error }); }); }
  var initialized = (async function () {
    try {
      var app = await import(SDK + 'firebase-app.js');
      api = await import(SDK + 'firebase-auth.js');
      auth = api.getAuth(app.getApps().length ? app.getApp() : app.initializeApp(window.FB_CONFIG));
      // Explicitly preserve the website's persistent cross-page local session, not TEST in-memory Auth.
      await api.setPersistence(auth, api.browserLocalPersistence);
      if (api.isSignInWithEmailLink(auth, location.href)) {
        var email = localStorage.getItem('mhpss-np-linkmail');
        if (!email) throw Error('Open this link in the browser that requested it.');
        await api.signInWithEmailLink(auth, email, location.href);
        localStorage.removeItem('mhpss-np-linkmail');
        history.replaceState({}, document.title, location.pathname + '?source=historical');
      }
      ready = true;
      api.onIdTokenChanged(auth, function (value) { user = value || null; notify(); });
    } catch (e) { error = 'Authentication unavailable. Retry when online.'; notify(); }
  })();
  window.BaselineAuth = Object.freeze({
    onChange: function (f) { callbacks.push(f); f(user, { ready: ready, error: error }); },
    currentUser: function () { return user; },
    token: async function () { await initialized; if (!user || !ready) throw Error('Sign in required'); return user.getIdToken(); },
    signIn: async function (email, password) { await initialized; if (!ready) throw Error(error); return api.signInWithEmailAndPassword(auth, email, password); },
    signOut: async function () { await initialized; if (ready) return api.signOut(auth); },
    sendLink: async function (email) {
      await initialized; if (!ready) throw Error(error);
      await api.sendSignInLinkToEmail(auth, email, { url: location.origin + location.pathname + '?source=historical', handleCodeInApp: true });
      localStorage.setItem('mhpss-np-linkmail', email);
    }
  });
})();
