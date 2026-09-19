/* =====================================================================
   MHPSS Nepal — Firestore bridge
   ---------------------------------------------------------------------
   Modelled on the Sadar Hati hub module (saha-shared.js): dynamic import
   of the Firebase 10.13.0 modular SDK from gstatic, initialiseApp, then
   a thin push function. Two deliberate differences, both because field
   workers in Rasuwa will often have no signal at all:

   1. LOCAL FIRST, ALWAYS. Every record is written to this device before
      any network call. Sadar Hati is online-first; that is fine in
      Malang and wrong in a holding centre above Dhunche. A record must
      never depend on the network to survive.

   2. IMMUTABLE EVENT IDs, via setDoc rather than addDoc. A new record gets
      a random id once, before either local copy is written, and carries
      that id through every retry. Legacy queued and imported records keep
      their existing `_rid`. Retrying is therefore idempotent without
      collapsing two distinct events that happen to have the same content.

   Nothing here logs record content to the console. Never add that: a
   phone screen in a shelter is not a private place.
   ===================================================================== */
(function () {
  "use strict";

  var SDK = "https://www.gstatic.com/firebasejs/10.13.0/";
  var cfg = window.FB_CONFIG || {};
  var COLL = window.FB_COLLECTION || "submissions";
  var QKEY = "mhpss-np-queue-v1";
  var LKEY = "mhpss-np-linkmail";
  /* Kept in step with isOwner() in the security rules. The rules are what
     enforce it; this copy only lets a page explain itself without a read. */
  var OWNER = "asroriadib@gmail.com";
  var ROLE_LIST = [
    ["admin",       "Full access. Can read and delete records, and can grant access to others."],
    ["coordinator", "Can read every record, and can publish the public aggregates and the site list."],
    ["im_officer",  "Same as coordinator. A separate label so the audit trail says who did what."],
    ["viewer",      "Can read records. Cannot publish, delete, or grant access."]
  ];

  var state = {
    configured: !!(cfg.projectId && cfg.apiKey),
    ready: false,
    error: "",
    queueError: "",
    queueReadFailed: false,
    storageError: "",
    user: null
  };
  var db = null, auth = null, api = {};
  var userCbs = [], stateCbs = [];

  function announce() {
    stateCbs.forEach(function (f) { try { f(status()); } catch (e) { /* ignore */ } });
  }
  function status() {
    return {
      configured: state.configured,
      ready: state.ready,
      error: state.error,
      persistenceError: state.storageError || state.queueError,
      online: navigator.onLine,
      user: state.user ? { email: state.user.email, uid: state.user.uid } : null,
      pending: queue().length
    };
  }

  /* ---------- local queue ---------------------------------------------
     The queue is the record of truth until the server confirms. An entry
     leaves the queue only once Firestore has acknowledged the write. */
  function queue() {
    try {
      var raw = localStorage.getItem(QKEY);
      /* When a write failed, the page copy is newer than localStorage. Do not
         hide it from status, export, retry, or a later successful write. */
      if (state.queueError && !state.queueReadFailed && window.__fbq) return window.__fbq;
      state.queueReadFailed = false;
      var parsed = JSON.parse(raw || "[]");
      if (!Array.isArray(parsed)) throw new Error("queue is not a list");
      return parsed;
    } catch (e) {
      state.queueReadFailed = true;
      state.queueError = "The existing send queue could not be read from this device.";
      return window.__fbq || [];
    }
  }
  function setQueue(q) {
    try {
      localStorage.setItem(QKEY, JSON.stringify(q));
      state.queueError = "";
      state.queueReadFailed = false;
      return true;
    } catch (e) {
      /* Keep the page copy available for an immediate retry, but never call
         it persisted: it disappears when this page closes. */
      window.__fbq = q;
      state.queueError = "The send queue could not be stored on this device.";
      return false;
    }
  }

  /* ---------- legacy deterministic id ---------------------------------
     Kept as a public compatibility helper for old exports and readers.
     New submissions do NOT use this content hash: two real events can have
     identical answers and must still be two remote documents. */
  function rid(rec) {
    /* The 4Ws activity report names its fields dateAD / activity / modality
       (camelCase, from store.js), not date_ad / service like the l1.js
       forms. Until 16 Sep 2026 this basis read only the snake_case names,
       so every activity report from one organisation at one site hashed to
       the SAME document id -- each new day's report overwrote the last in
       the register. The report's own deterministic id (store.js recordId,
       over org, site, palika, date, activity, modality) is the identity, so
       it is the first thing in the basis; the camelCase fields follow for a
       record that arrives without one. */
    var basis = [
      rec.kind || "", rec.id || "", rec.org || "", rec.date_ad || rec.dateAD || "", rec.site || "",
      rec.palika || "", rec.activity || "", rec.modality || "",
      rec.contact_code || "", rec.service || rec.reason || rec.instrument || "",
      rec.focal_name || "", rec.administration || "", rec.direction || "",
      rec.q1 === undefined ? "" : String(rec.q1),
      rec.coping === undefined ? "" : String(rec.coping),
      rec.minutes || "", rec.total === undefined || rec.total === null ? "" : String(rec.total)
    ].join("|");
    var h1 = 0x811c9dc5 >>> 0, h2 = 0x01000193 >>> 0, i;
    for (i = 0; i < basis.length; i++) {
      h1 ^= basis.charCodeAt(i); h1 = Math.imul(h1, 0x01000193) >>> 0;
    }
    for (i = basis.length - 1; i >= 0; i--) {
      h2 ^= basis.charCodeAt(i); h2 = Math.imul(h2, 0x01000193) >>> 0;
    }
    function p(n) { var s = n.toString(36).toUpperCase(); while (s.length < 7) s = "0" + s; return s; }
    return (rec.kind || "rec") + "_" + p(h1) + p(h2);
  }

  var fallbackEventCounter = 0;
  function eventId(rec) {
    var bytes = new Uint8Array(16), hex = "", i;
    if (window.crypto && typeof window.crypto.getRandomValues === "function") {
      window.crypto.getRandomValues(bytes);
    } else {
      /* getRandomValues is available in the trial's supported browsers. This
         fallback still mixes time, randomness and a page counter so an older
         browser does not fall back to content-derived identity. */
      fallbackEventCounter++;
      var seed = Date.now().toString(16) + Math.random().toString(16).slice(2) +
        fallbackEventCounter.toString(16);
      for (i = 0; i < bytes.length; i++) {
        bytes[i] = (parseInt(seed.slice(i * 2, i * 2 + 2), 16) || 0) ^
          Math.floor(Math.random() * 256);
      }
    }
    for (i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, "0");
    var kind = String(rec && rec.kind || "rec").replace(/[^A-Za-z0-9_-]/g, "_");
    return kind + "_evt_" + hex;
  }

  function ensureEventId(rec) {
    if (!rec || typeof rec !== "object") throw new TypeError("a record is required");
    /* Existing ids are immutable compatibility data. In particular, never
       replace the deterministic ids already sitting in a legacy queue. */
    if (!rec._rid) rec._rid = eventId(rec);
    return rec._rid;
  }

  function persistenceFailure(message) {
    state.storageError = message || "A record could not be stored on this device.";
    announce();
  }

  function persistenceError(message) {
    var e = new Error(message);
    e.code = "PERSISTENCE_FAILED";
    return e;
  }

  /* ---------- init ---------------------------------------------------- */
  if (!state.configured) {
    state.error = "not configured";
  } else {
    (async function () {
      try {
        var appMod = await import(SDK + "firebase-app.js");
        var fsMod  = await import(SDK + "firebase-firestore.js");
        var auMod  = await import(SDK + "firebase-auth.js");
        var app = appMod.initializeApp(cfg);
        db = fsMod.getFirestore(app);
        auth = auMod.getAuth(app);
        api = {
          doc: fsMod.doc, setDoc: fsMod.setDoc, collection: fsMod.collection,
          query: fsMod.query, where: fsMod.where, orderBy: fsMod.orderBy,
          limit: fsMod.limit, onSnapshot: fsMod.onSnapshot, getDocs: fsMod.getDocs,
          getDoc: fsMod.getDoc, deleteDoc: fsMod.deleteDoc,
          serverTimestamp: fsMod.serverTimestamp,
          signIn: auMod.signInWithEmailAndPassword, signOut: auMod.signOut,
          onAuth: auMod.onAuthStateChanged,
          sendLink: auMod.sendSignInLinkToEmail,
          isLink: auMod.isSignInWithEmailLink,
          signInLink: auMod.signInWithEmailLink
        };
        /* An email link arrives as a URL on this same page. Finish the
           sign-in before wiring anything else up, so the page renders once
           in its final state rather than flashing a sign-in form first. */
        try {
          if (api.isLink(auth, window.location.href)) {
            var pending = "";
            try { pending = localStorage.getItem(LKEY) || ""; } catch (e) { /* ignore */ }
            if (!pending) {
              /* The link was opened in a different browser from the one that
                 asked for it, so the address is not on this device. Asking
                 for it again is the documented flow, not a failure. */
              pending = window.prompt(
                "To finish signing in, type the email address this link was sent to:") || "";
            }
            if (pending) {
              await api.signInLink(auth, pending, window.location.href);
              try { localStorage.removeItem(LKEY); } catch (e) { /* ignore */ }
              /* Strip the credential out of the address bar so it is not left
                 in history, bookmarks or a screenshot. */
              if (window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title,
                  window.location.pathname + window.location.search);
              }
            }
          }
        } catch (e) {
          state.error = "sign-in link failed: " +
            (e && e.message ? e.message.replace(/^Firebase:\s*/, "") : String(e));
        }

        api.onAuth(auth, function (u) {
          state.user = u || null;
          userCbs.forEach(function (f) { try { f(state.user); } catch (e) { /* ignore */ } });
          announce();
        });
        state.ready = true; state.error = "";
        announce();
        flush();
      } catch (e) {
        state.ready = false;
        state.error = "could not reach Firebase: " + (e && e.message ? e.message : String(e));
        announce();
      }
    })();
  }

  /* ---------- submit --------------------------------------------------
     The caller gets explicit local persistence and remote acknowledgement
     states. A failed queue write is never described as safe local storage. */
  function submit(rec) {
    ensureEventId(rec);
    var r = JSON.parse(JSON.stringify(rec || {}));
    r._device_ts = new Date().toISOString();
    var q = queue();
    if (state.queueReadFailed) {
      /* Never replace an unreadable queue with a new one. Keep this submission
         in memory and require export/recovery instead of risking older rows. */
      window.__fbq = (window.__fbq || []).concat([r]);
      var unreadable = {
        local: false,
        persisted: false,
        rid: r._rid,
        remote: false,
        error: "Not safely stored: the existing send queue could not be read."
      };
      announce();
      return Promise.resolve(unreadable);
    }
    /* already queued and unsent? replace rather than add a second copy */
    var at = -1;
    for (var i = 0; i < q.length; i++) { if (q[i]._rid === r._rid) { at = i; break; } }
    if (at >= 0) q[at] = r; else q.push(r);
    var persisted = setQueue(q);

    var out = {
      local: persisted,
      persisted: persisted,
      rid: r._rid,
      remote: false,
      error: persisted ? "" : "Not safely stored: the send queue is only in memory for this page."
    };
    if (!state.ready) {
      if (persisted) {
        out.error = state.configured ? (state.error || "not connected yet") : "not configured";
      }
      announce();
      return Promise.resolve(out);
    }
    return push(r).then(function () {
      out.remote = true; drop(r._rid); announce(); return out;
    }).catch(function (e) {
      out.error = e && e.message ? e.message : String(e);
      announce(); return out;
    });
  }

  /* ---------- what never crosses the network -------------------------
     A 4Ws report names a focal point so a figure can be queried later.
     That is normal humanitarian practice and the detail is useful -- but
     it is a named professional's mobile number, and the rule the data
     workstream set is that professionals' contact details stay in the
     source file and "do not go into any deliverable, any repository, or
     any hosted system".

     So the focal point stays on the handset and in the private export a
     worker sends to coordination, and is stripped before the record is
     pushed. Coordination still gets it, through the file; the hosted
     database never holds it.

     The security rules reject these keys as well. Two ends, because a
     form can be edited by anyone with repo access and the rules cannot.
     If the Technical Working Group later decides the hosted copy should carry a focal
     point, this list and the rules change together -- deliberately, not
     by an edit to one form. */
  var NEVER_SENT = ["focalName", "focalPhone", "focalEmail",
                    "focal_name", "focal_phone", "focal_email",
                    "referrerPhone", "referrer_phone"];

  function bodyForFirestore(r) {
    var body = JSON.parse(JSON.stringify(r));
    delete body._device_ts;
    for (var i = 0; i < NEVER_SENT.length; i++) delete body[NEVER_SENT[i]];
    return body;
  }

  function push(r) {
    var body = bodyForFirestore(r);
    body.server_ts = api.serverTimestamp();
    body.device_ts = r._device_ts;
    return api.setDoc(api.doc(db, COLL, r._rid), body);
  }

  function drop(id) {
    setQueue(queue().filter(function (x) { return x._rid !== id; }));
  }

  /* With no argument this retains the old clear-all API. A kind string or
     { kinds, rids } removes only queue entries related to a source store.
     Failure throws so a source clear cannot continue and claim success. */
  function clearQueue(match) {
    var q = queue(), ids = {}, kinds = {}, clearAll = match === undefined;
    if (state.queueReadFailed) {
      announce();
      throw persistenceError("Could not read the existing send queue; nothing was cleared.");
    }
    if (typeof match === "string") kinds[match] = true;
    else if (match && typeof match === "object") {
      if (match.kind) kinds[match.kind] = true;
      (match.kinds || []).forEach(function (kind) { if (kind) kinds[kind] = true; });
      (match.rids || []).forEach(function (id) { if (id) ids[id] = true; });
    }
    var keep = q.filter(function (r) {
      /* An id match is only a fallback for a legacy queue entry with no kind.
         Never let an accidental/corrupt cross-kind id clear another form. */
      var related = clearAll || (r.kind && kinds[r.kind]) ||
        (!r.kind && r._rid && ids[r._rid]);
      return !related;
    });
    var removed = q.length - keep.length;
    if (removed && !setQueue(keep)) {
      /* The clear did not persist, so keep the pre-clear page copy too. */
      window.__fbq = q;
      announce();
      throw persistenceError("Could not clear the related send queue from this device.");
    }
    announce();
    /* Return the exact snapshot this mutation was based on. A caller that
       cannot complete its source deletion must restore this snapshot, not a
       separate pre-read that another tab could have made stale. */
    return { cleared: true, queueCleared: removed, left: keep.length, originalQueue: q };
  }

  /* Put back a caller's pre-mutation snapshot. Source stores use this to make
     a queue clear and source clear one recoverable operation: if deleting the
     source fails after the queue changed, every queued row (including order and
     unrelated kinds) is written back. Failure throws and must be treated as a
     high-severity recovery condition by the caller. */
  function restoreQueue(snapshot) {
    if (!Array.isArray(snapshot)) {
      throw persistenceError("HIGH-SEVERITY WARNING: the original send queue snapshot is invalid and could not be restored.");
    }
    if (!setQueue(snapshot)) {
      announce();
      throw persistenceError("HIGH-SEVERITY WARNING: the original send queue could not be restored on this device.");
    }
    announce();
    return { restored: true, count: snapshot.length };
  }

  /* ---------- flush ---------------------------------------------------
     Sequential, not parallel: a phone on one bar of signal handles one
     write at a time far better than twenty at once. */
  function flush() {
    if (!state.ready || !navigator.onLine) return Promise.resolve({ sent: 0, left: queue().length });
    var q = queue().slice(), sent = 0;
    return q.reduce(function (chain, r) {
      return chain.then(function () {
        return push(r).then(function () { sent++; drop(r._rid); })
                      .catch(function () { /* stays queued */ });
      });
    }, Promise.resolve()).then(function () {
      announce();
      return { sent: sent, left: queue().length };
    });
  }

  window.addEventListener("online", function () { flush(); announce(); });
  window.addEventListener("offline", announce);

  /* ---------- read (coordination side, needs a signed-in user) -------- */
  function watch(cb, onErr) {
    if (!state.ready) { if (onErr) onErr("not connected"); return function () {}; }
    var qq = api.query(api.collection(db, COLL), api.orderBy("server_ts", "desc"), api.limit(2000));
    return api.onSnapshot(qq, function (snap) {
      var rows = [];
      snap.forEach(function (d) { var o = d.data(); o._id = d.id; rows.push(o); });
      cb(rows);
    }, function (e) { if (onErr) onErr(e && e.message ? e.message : String(e)); });
  }

  /* watchKind -- the listen an UNAUTHENTICATED reader has to use.
     Rules v3 opens one kind of record and only that kind, and Firestore
     evaluates a query against its POTENTIAL result set: "security rules are
     not filters ... queries are all or nothing". So an anonymous reader must
     name the kind in the query itself; watch() above, which names nothing, is
     refused outright even when every document in the collection would pass.

     No orderBy here, deliberately. Single-field indexes are automatic;
     combinations of fields are not, and an equality filter plus an orderBy on
     a different field is a combination. Dropping the sort keeps this path
     working with no composite index to create in the console, and costs
     nothing: every page that consumes these rows sorts them itself.
     If the collection ever outgrows the limit, the fix is the composite index
     on (kind, server_ts) -- Firestore returns the error with a link to build
     it -- not a larger limit. */
  function watchKind(kind, cb, onErr) {
    if (!state.ready) { if (onErr) onErr("not connected"); return function () {}; }
    var qq = api.query(api.collection(db, COLL), api.where("kind", "==", kind), api.limit(2000));
    return api.onSnapshot(qq, function (snap) {
      var rows = [];
      snap.forEach(function (d) { var o = d.data(); o._id = d.id; rows.push(o); });
      cb(rows);
    }, function (e) { if (onErr) onErr(e && e.message ? e.message : String(e)); });
  }

  function signIn(email, pass) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.signIn(auth, email, pass);
  }
  function signOutNow() {
    if (!state.ready) return Promise.resolve();
    return api.signOut(auth);
  }

  /* ---------- the sync strip -------------------------------------------
     Auto-mounted on any page that loads this file. It states the actual
     situation and never implies more than is true: "saved on this phone"
     is not "sent", and a queue of 3 says 3. A field worker who believes
     a record reached coordination when it did not is worse off than one
     who knows it is still waiting. */
  (function () {
    var css = document.createElement("style");
    css.textContent =
      "#fbbar{position:sticky;top:0;z-index:39;display:flex;gap:9px;align-items:center;" +
      "flex-wrap:wrap;padding:8px 14px;font:600 12px/1.35 'Noto Sans',system-ui,sans-serif;" +
      "background:#eef5f1;color:#24543f;border-bottom:1px solid #bcd9c9}" +
      "#fbbar.warn{background:#fdf2ea;color:#8f420f;border-bottom-color:#e8c9b0}" +
      "#fbbar.off{background:#f4f7f9;color:#5b6b76;border-bottom-color:#d8dfe4}" +
      "#fbbar .m{flex:1 1 200px;min-width:0}" +
      "#fbbar button{font:700 11.5px/1.2 inherit;font-family:inherit;border:1.5px solid currentColor;" +
      "background:#fff;color:inherit;border-radius:6px;padding:6px 11px;cursor:pointer}";
    document.head.appendChild(css);

    var bar = document.createElement("div");
    bar.id = "fbbar";

    function mount() {
      var pb = document.getElementById("pwabar");
      if (pb && pb.parentNode) pb.parentNode.insertBefore(bar, pb.nextSibling);
      else document.body.insertBefore(bar, document.body.firstElementChild);
      paint(status());
    }

    function paint(st) {
      var cls = "", msg;
      if (st.persistenceError) {
        cls = "warn";
        msg = "<b>Storage failed.</b> " + st.persistenceError +
              " Do not close this page; export the record before leaving.";
      } else if (!st.configured) {
        cls = "off";
        msg = "<b>Saving to this device only.</b> No database is connected yet, so records stay here " +
              "until you export them.";
      } else if (!st.ready) {
        cls = "warn";
        msg = "<b>Not connected to the database.</b> " +
              (st.online ? "Retrying. " : "No signal. ") +
              "Persisted records remain on this phone" +
              (st.pending ? " — " + st.pending + " waiting to send." : ".");
      } else if (st.pending) {
        cls = "warn";
        msg = "<b>" + st.pending + " record(s) still to send.</b> " +
              (st.online ? "Sending now." : "They go as soon as you have signal.");
      } else {
        msg = "<b>Connected.</b> Records reach coordination as you save them." +
              (st.user ? " Signed in as " + st.user.email + "." : "");
      }
      bar.className = cls;
      bar.innerHTML = '<span class="m">' + msg + "</span>";
      if (st.configured && st.pending && st.online) {
        var b = document.createElement("button");
        b.type = "button"; b.textContent = "Send now";
        b.onclick = function () { b.disabled = true; b.textContent = "Sending…"; flush(); };
        bar.appendChild(b);
      }
    }

    stateCbs.push(paint);
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mount);
    } else { mount(); }
  })();

  /* ---------- roles ----------------------------------------------------
     A signed-in account is not access. The rules require a named grant in
     /roles/{email}; this reads the caller's own grant so a page can say
     plainly why it can or cannot show records. */
  function myRole() {
    if (!state.ready || !state.user) return Promise.resolve(null);
    var mail = state.user.email || "";
    if (mail === OWNER) return Promise.resolve({ role: "admin", owner: true });
    return api.getDoc(api.doc(db, "roles", mail))
      .then(function (d) { return d.exists() ? d.data() : null; })
      .catch(function () { return null; });
  }

  function listRoles() {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.getDocs(api.collection(db, "roles")).then(function (snap) {
      var out = [];
      snap.forEach(function (d) { var o = d.data(); o._email = d.id; out.push(o); });
      out.sort(function (a, b) { return (a._email || "").localeCompare(b._email || ""); });
      return out;
    });
  }

  function grantRole(personEmail, role, note) {
    if (!state.ready || !state.user) return Promise.reject(new Error("not signed in"));
    var body = {
      role: role,
      added_by: state.user.email,
      added_at: api.serverTimestamp()
    };
    if (note) body.note = String(note).slice(0, 200);
    return api.setDoc(api.doc(db, "roles", personEmail), body);
  }

  function revokeRole(personEmail) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.deleteDoc(api.doc(db, "roles", personEmail));
  }

  /* ---------- passwordless sign-in ------------------------------------
     The person types their address once and clicks a link. No password is
     ever chosen, typed, shared or stored -- which also means nobody is
     holding anybody else's password. */
  function sendLink(mail) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    try { localStorage.setItem(LKEY, mail); } catch (e) { /* ignore */ }
    return api.sendLink(auth, mail, {
      url: window.location.origin + window.location.pathname,
      handleCodeInApp: true
    });
  }

  /* ---------- the public shelf -----------------------------------------
     public_stats is the ONLY thing the public website reads: aggregates a
     coordinator publishes on purpose, never the register itself. The rules
     let anyone read it and let a coordinator write it, provided the document
     stamps computed_at with the server clock, says in `basis` what it
     counts, and stays under 40 top-level fields. Everything written here is
     public the moment it lands, so the caller shows a preview first. */
  function publish(docId, body) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    if (!state.user) return Promise.reject(new Error("not signed in"));
    if (!body || typeof body.basis !== "string" || !body.basis.trim()) {
      return Promise.reject(new Error("a published document must say in `basis` what it counts"));
    }
    var out = JSON.parse(JSON.stringify(body));
    for (var i = 0; i < NEVER_SENT.length; i++) delete out[NEVER_SENT[i]];
    if (Object.keys(out).length + 1 >= 40) return Promise.reject(new Error("too many top-level fields for the rules (< 40)"));
    out.computed_at = api.serverTimestamp();
    out.published_by_role = "coordinator";
    return api.setDoc(api.doc(db, "public_stats", docId), out).then(function () { return docId; });
  }
  /* the published copy, as anyone would see it (no account needed) */
  function readPublic(docId) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.getDoc(api.doc(db, "public_stats", docId)).then(function (d) { return d.exists() ? d.data() : null; });
  }

  window.FB = {
    status: status,
    myRole: myRole, listRoles: listRoles, grantRole: grantRole, revokeRole: revokeRole,
    publish: publish, readPublic: readPublic,
    sendLink: sendLink, OWNER: OWNER, ROLES: ROLE_LIST,
    onStatus: function (f) { stateCbs.push(f); f(status()); },
    onUser: function (f) { userCbs.push(f); f(state.user); },
    submit: submit, flush: flush, queue: queue, rid: rid,
    bodyForFirestore: bodyForFirestore,
    ensureEventId: ensureEventId, reportPersistenceFailure: persistenceFailure,
    watch: watch, watchKind: watchKind, signIn: signIn, signOut: signOutNow,
    clearQueue: clearQueue, restoreQueue: restoreQueue
  };
})();
