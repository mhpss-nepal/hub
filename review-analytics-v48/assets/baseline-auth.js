/* Same project and Firebase Auth provider as the website. Auth-only: no Firestore
   import, legacy queue reader/flush, role lookup, report watcher or publication. */
(function () {
  'use strict';
  var SDK = 'https://www.gstatic.com/firebasejs/10.13.0/', auth, api, user = null, callbacks = [], ready = false, error = '';
  var signedOutIntent = false, lifecycle = 0, pendingLink = false;
  function storedEmail() { try { return localStorage.getItem('mhpss-np-linkmail'); } catch (e) { return null; } }
  function forgetEmail() { try { localStorage.removeItem('mhpss-np-linkmail'); } catch (e) { /* Storage is optional for link completion. */ } }
  async function consumeLink(email) {
    var credential = await api.signInWithEmailLink(auth, email, location.href);
    pendingLink = false; forgetEmail();
    history.replaceState({}, document.title, location.pathname + '?source=historical');
    return credential;
  }
  function currentUser() { return signedOutIntent ? null : user; }
  function notify() { callbacks.forEach(function (f) { f(currentUser(), { ready: ready, error: error, linkPending: pendingLink }); }); }
  async function completeSignIn(operation) {
    var mine = lifecycle;
    await initialized;
    if (!ready) throw Error(error);
    var credential = await operation();
    var nextUser = credential && credential.user || user;
    // Only an explicit successful sign-in may release intent. A later sign-out wins.
    if (mine === lifecycle && nextUser && typeof nextUser.getIdToken === 'function') {
      user = nextUser; signedOutIntent = false; error = ''; notify();
    }
    return credential;
  }
  var initialized = (async function () {
    try {
      var app = await import(SDK + 'firebase-app.js');
      api = await import(SDK + 'firebase-auth.js');
      auth = api.getAuth(app.getApps().length ? app.getApp() : app.initializeApp(window.FB_CONFIG));
      // Explicitly preserve the website's persistent cross-page local session, not TEST in-memory Auth.
      await api.setPersistence(auth, api.browserLocalPersistence);
      ready = true;
      api.onIdTokenChanged(auth, function (value) { user = value || null; notify(); });
      pendingLink = api.isSignInWithEmailLink(auth, location.href);
      if (pendingLink) {
        var email = storedEmail();
        if (email) {
          try { await consumeLink(email); error = ''; }
          catch (e) { error = 'Sign-in link could not be completed. Enter your email to retry, request a replacement link, or use your password.'; }
        } else {
          error = 'Enter the email address that requested this link and choose Complete email sign-in, request a replacement link, or use your password.';
        }
        notify();
      }
    } catch (e) { error = 'Authentication unavailable. Retry when online.'; notify(); }
  })();
  window.BaselineAuth = Object.freeze({
    onChange: function (f) { callbacks.push(f); f(currentUser(), { ready: ready, error: error, linkPending: pendingLink }); },
    currentUser: currentUser,
    token: async function () {
      var mine = lifecycle;
      await initialized;
      var value = currentUser();
      if (!value || !ready) throw Error('Sign in required');
      var token = await value.getIdToken();
      if (mine !== lifecycle || currentUser() !== value) throw Error('Sign in required');
      return token;
    },
    signIn: function (email, password) { return completeSignIn(function () { return api.signInWithEmailAndPassword(auth, email, password); }); },
    signOut: async function () {
      signedOutIntent = true; lifecycle += 1; notify();
      await initialized;
      if (ready) return api.signOut(auth);
    },
    finishLink: function (email) {
      return completeSignIn(function () {
        if (!pendingLink || !email) throw Error('Email sign-in link and address required');
        return consumeLink(email);
      });
    },
    sendLink: async function (email) {
      await initialized; if (!ready) throw Error(error);
      await api.sendSignInLinkToEmail(auth, email, { url: location.origin + location.pathname + '?source=historical', handleCodeInApp: true });
      try { localStorage.setItem('mhpss-np-linkmail', email); } catch (e) { /* Re-enter the address in the receiving browser. */ }
    }
  });
})();
