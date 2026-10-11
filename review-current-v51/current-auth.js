/* Same project and Firebase Auth provider as the website. Auth-only: no Firestore
   import, legacy queue reader/flush, role lookup, report watcher or publication. */
(function () {
  'use strict';
  var SDK = 'https://www.gstatic.com/firebasejs/10.13.0/', auth, api, user = null, callbacks = [], ready = false, error = '';
  var signedOutIntent = false, lifecycle = 0, pendingLink = false;
  var restoration = 'restoring', errorCode = '', failureStage = '';
  var safeCodes = ['auth/invalid-action-code', 'auth/expired-action-code', 'auth/invalid-email', 'auth/network-request-failed', 'auth/web-storage-unsupported', 'auth/operation-not-allowed', 'auth/unauthorized-domain', 'auth/user-disabled', 'auth/invalid-credential', 'auth/too-many-requests'];
  function state() { return { ready: ready, error: error, linkPending: pendingLink, restoration: restoration, errorCode: errorCode, failureStage: failureStage }; }
  function clearFailure() { error = ''; errorCode = ''; failureStage = ''; }
  function fail(e, stage) {
    errorCode = e && safeCodes.indexOf(e.code) !== -1 ? e.code : 'auth/unknown';
    failureStage = stage;
    var guidance = errorCode === 'auth/network-request-failed' ? 'Connection failed. Reconnect and retry this operation.' :
      errorCode === 'auth/web-storage-unsupported' ? 'Browser storage is unavailable. Session restoration cannot be confirmed.' :
      errorCode === 'auth/invalid-action-code' || errorCode === 'auth/expired-action-code' ? 'This link is invalid, expired, already used, or does not match the entered email. Existing sign-in has not been cleared.' :
      'Authentication could not complete. Existing sign-in has not been cleared. Share only this error code with support.';
    error = guidance + ' (' + errorCode + ')'; notify();
  }
  function storedEmail() { try { return localStorage.getItem('mhpss-np-linkmail'); } catch (e) { return null; } }
  function forgetEmail() { try { localStorage.removeItem('mhpss-np-linkmail'); } catch (e) { /* Storage is optional for link completion. */ } }
  async function consumeLink(email) {
    var credential = await api.signInWithEmailLink(auth, email, location.href);
    pendingLink = false; forgetEmail();
    history.replaceState({}, document.title, location.pathname + '?source=current');
    return credential;
  }
  function currentUser() { return signedOutIntent ? null : user; }
  function notify() { callbacks.forEach(function (f) { f(currentUser(), state()); }); }
  async function completeSignIn(operation) {
    var mine = lifecycle;
    await initialized;
    if (!ready) throw Error(error);
    var credential;
    try { credential = await operation(); }
    catch (e) { fail(e, pendingLink ? 'email-link' : 'sign-in'); throw e; }
    var nextUser = credential && credential.user || user;
    // Only an explicit successful sign-in may release intent. A later sign-out wins.
    if (mine === lifecycle && nextUser && typeof nextUser.getIdToken === 'function') {
      user = nextUser; signedOutIntent = false; restoration = 'signed-in'; clearFailure(); notify();
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
      pendingLink = api.isSignInWithEmailLink(auth, location.href);
      ready = true;
      // Do not call an un-restored null user a completed signed-out session.
      await new Promise(function (resolve, reject) {
        api.onIdTokenChanged(auth, function (value) {
          user = value || null; restoration = currentUser() ? 'signed-in' : 'signed-out'; notify(); resolve();
        }, reject);
      });
      if (pendingLink) {
        var email = storedEmail();
        if (email) {
          try { await consumeLink(email); clearFailure(); }
          catch (e) { fail(e, 'email-link'); }
        } else {
          error = 'Enter the email address that requested this link and choose Complete email sign-in. No new link has been requested.';
        }
        notify();
      }
    } catch (e) { ready = false; restoration = 'failed'; fail(e, 'initialization'); }
  })();
  window.BaselineAuth = Object.freeze({
    onChange: function (f) { callbacks.push(f); f(currentUser(), state()); },
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
      signedOutIntent = true; lifecycle += 1; restoration = 'signed-out'; notify();
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
      await api.sendSignInLinkToEmail(auth, email, { url: location.origin + location.pathname + '?source=current', handleCodeInApp: true });
      try { localStorage.setItem('mhpss-np-linkmail', email); } catch (e) { /* Re-enter the address in the receiving browser. */ }
    }
  });
})();
