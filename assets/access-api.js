/* =====================================================================
   MHPSS Nepal — access cards and sign-in for the field forms and the team page
   ---------------------------------------------------------------------
   One account per person; the server (mhpss5ws /access/*) decides what the
   person sees. Sign-in is by a link sent to the person's email, so nobody has
   to type a long password on a phone (lesson from Sadar Hati, Aug 2026); a
   password remains as the other way in. The session stays on the device until
   the person signs out. Loads after current-auth.js (window.BaselineAuth).
   ===================================================================== */
(function () {
  "use strict";
  var BASE = "https://mhpss5ws-tdp3xtfnsq-as.a.run.app";
  if (!window.STAFF_AUTH_RETURN) window.STAFF_AUTH_RETURN = location.origin + location.pathname;
  function T(k, en) { try { var v = window.I18N && I18N.t(k); return v && v.charAt(0) !== "[" ? v : en; } catch (e) { return en; } }
  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  async function call(path, opt) {
    opt = opt || {};
    var h = { Authorization: "Bearer " + await BaselineAuth.token() };
    if (opt.org) h["X-Selected-Org"] = opt.org;
    if (opt.cursor) h["X-Listing-Cursor"] = opt.cursor;
    if (opt.body) h["Content-Type"] = "application/json";
    var r = await fetch(BASE + path, { method: opt.body ? "POST" : "GET", headers: h, body: opt.body ? JSON.stringify(opt.body) : undefined });
    var j = {}; try { j = await r.json(); } catch (e) { /* empty */ }
    if (!r.ok) { var err = new Error(j.error || ("HTTP " + r.status)); err.status = r.status; throw err; }
    return j;
  }
  async function all(path) {
    var rows = [], cursor = null, guard = 0;
    do { var j = await call(path, { cursor: cursor }); rows = rows.concat(j.rows || []); cursor = j.nextCursor; } while (cursor && ++guard < 60);
    return rows;
  }
  var API = {
    BASE: BASE, esc: esc, T: T, call: call,
    me: function () { return call("/access/me"); },
    team: function () { return call("/access/team"); },
    progress: function () { return call("/access/progress"); },
    invite: function (b) { return call("/access/invite", { body: b }); },
    disable: function (email) { return call("/access/disable", { body: { email: email } }); },
    review: function (b) { return call("/access/review", { body: b }); },
    griefEntries: function (org) { return call("/grief/entries", { org: org }); },
    griefSummary: function (org) { return call("/grief/summary", { org: org }); },
    dirAll: function () { return all("/directory/servicepoints2/current"); },
    dirMine: function () { return all("/directory/servicepoints2/entries"); },
    user: function () { return window.BaselineAuth && BaselineAuth.currentUser && BaselineAuth.currentUser(); },
    signOut: function () { return BaselineAuth.signOut(); }
  };

  /* Sign-in panel: email link first, password as the other way in. */
  API.signInPanel = function (host, onDone) {
    host.innerHTML =
      '<div class="acc-signin">' +
      '<label class="f" for="accEmail" data-i18n="acc.email">Your work email</label>' +
      '<input type="email" id="accEmail" autocomplete="username" inputmode="email">' +
      '<div class="actions" style="margin-top:10px"><button type="button" class="btn" id="accLink" data-i18n="acc.sendLink">Email me a sign-in link</button>' +
      '<button type="button" class="btn ghost" id="accFinish" hidden data-i18n="acc.finish">Finish signing in</button></div>' +
      '<p class="lead acc-msg" id="accMsg" style="margin:10px 0 0"></p>' +
      '<details style="margin-top:10px"><summary data-i18n="acc.usePassword">Use a password instead</summary>' +
      '<label class="f" for="accPass" data-i18n="acc.password">Password</label><input type="password" id="accPass" autocomplete="current-password">' +
      '<div class="actions" style="margin-top:10px"><button type="button" class="btn ghost" id="accIn" data-i18n="acc.signin">Sign in</button></div></details></div>';
    try { window.I18N && I18N.apply(host); } catch (e) { /* optional */ }
    var $ = function (s) { return host.querySelector(s); };
    try { var ev = getComputedStyle($("#accEmail")), pw = $("#accPass"); ["width","height","padding","border","borderRadius","font","fontSize","background","color","boxSizing"].forEach(function (k) { pw.style[k] = ev[k]; }); } catch (e) { /* cosmetic */ }
    try { var saved = localStorage.getItem("mhpss-np-linkmail") || localStorage.getItem("mhpss-np-last-email"); if (saved) $("#accEmail").value = saved; } catch (e) { /* storage optional */ }
    function msg(t, ok) { var m = $("#accMsg"); m.textContent = t; m.style.color = ok === true ? "#1a7f37" : ok === false ? "#a3221c" : "#52647a"; }
    function email() { var v = $("#accEmail").value.trim(); try { localStorage.setItem("mhpss-np-last-email", v); } catch (e) { /* optional */ } return v; }
    $("#accLink").addEventListener("click", async function () {
      var e = email(); if (!/^\S+@\S+\.\S+$/.test(e)) { msg(T("acc.badEmail", "Type the email address first."), false); return; }
      msg(T("acc.sending", "Sending…"));
      try { await BaselineAuth.sendLink(e); msg(T("acc.sent", "Link sent. Open your email on this phone and tap the link; it brings you back here signed in."), true); }
      catch (x) { msg(T("acc.sendFailed", "The link could not be sent. Check the address and the connection, or use a password."), false); }
    });
    $("#accFinish").addEventListener("click", async function () {
      try { await BaselineAuth.finishLink(email()); } catch (x) { msg(T("acc.finishFailed", "This link does not match the email typed. Use the same address the link was sent to."), false); }
    });
    $("#accIn").addEventListener("click", async function () {
      msg(T("acc.signingIn", "Signing in…"));
      try { await BaselineAuth.signIn(email(), $("#accPass").value); $("#accPass").value = ""; msg(""); }
      catch (x) { msg(T("acc.signinFailed", "Sign-in failed. Check the email and password, or use the email link."), false); }
    });
    if (window.BaselineAuth) BaselineAuth.onChange(function (u, st) {
      $("#accFinish").hidden = !(st && st.linkPending && !u);
      if (st && st.linkPending && !u) msg(T("acc.confirm", "Type the email address the link was sent to, then choose Finish signing in."));
      if (u && onDone) onDone(u);
    });
  };
  window.AccessAPI = API;
})();
