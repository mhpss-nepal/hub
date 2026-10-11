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

   2. DETERMINISTIC DOCUMENT IDs, via setDoc rather than addDoc. A queued
      record may be retried many times — on reconnect, on reload, on a
      second device that has the same export. addDoc would create a new
      document every time and silently inflate the count. setDoc with an
      stable source id (or an explicitly retained legacy ID) writes the same document
      again instead, so retrying is safe and de-duplication happens for
      free at the database.

   Nothing here logs record content to the console. Never add that: a
   phone screen in a shelter is not a private place.
   ===================================================================== */
(function () {
  "use strict";

  var SDK = "https://www.gstatic.com/firebasejs/10.13.0/";
  var cfg = window.FB_CONFIG || {};
  var COLL = window.FB_COLLECTION || "submissions";
  var LEGACY_QKEY = "mhpss-np-queue-v1";
  // Capture the destination BEFORE SDK initialization or any reconnect handler.
  // Never load/migrate another queue body. Legacy detection inspects key names only.
  var BINDING = [window.location.origin, cfg.projectId || "unconfigured",
    COLL, window.FB_QUEUE_SCOPE || (/preview|review-/.test(window.location.pathname) ? "preview" : "operational")];
  var QKEY = "mhpss-np-queue-v2:" + encodeURIComponent(JSON.stringify(BINDING));
  var queueError = "", flushing = null;
  // Page-lifetime recovery is authoritative after a failed durable write.
  // Never replace it with an older disk body or dispatch it as durable.
  var recoveryRows = null;
  function legacyQuarantined() {
    try {
      for (var i = 0; i < localStorage.length; i++) if (localStorage.key(i) === LEGACY_QKEY) return true;
      return false;
    } catch (e) { return true; }
  }
  function exportLegacyQueue(consent) {
    if (consent !== true || !window.confirm("Export the unchanged private legacy outbox? Keep the file private; do not upload or clear it. Destination review is still required.")) {
      throw new Error("explicit private-export consent required");
    }
    return localStorage.getItem(LEGACY_QKEY);
  }
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
      online: navigator.onLine,
      user: state.user ? { email: state.user.email, uid: state.user.uid } : null,
      pending: queue().length,
      queueError: queueError,
      legacyQuarantined: legacyQuarantined(),
      binding: BINDING.slice()
    };
  }

  /* ---------- local queue ---------------------------------------------
     The queue is the record of truth until the server confirms. An entry
     leaves the queue only once Firestore has acknowledged the write. */
  function queue() {
    if (recoveryRows !== null) return recoveryRows;
    try {
      var raw = localStorage.getItem(QKEY);
      if (!raw) return window.__fbq || [];
      var envelope = JSON.parse(raw);
      if (JSON.stringify(envelope.binding) !== JSON.stringify(BINDING) || !Array.isArray(envelope.rows)) {
        throw new Error("outbox binding mismatch");
      }
      if (!envelope.rows.every(function (r) { return r && typeof r === "object" && typeof r._rid === "string" && r._rid && typeof r._device_ts === "string"; })) {
        throw new Error("invalid bound outbox entry");
      }
      queueError = "";
      return envelope.rows;
    } catch (e) { queueError = "outbox quarantined: " + e.message; return []; }
  }
  function setQueue(q) {
    if (queueError) return false;
    try { localStorage.setItem(QKEY, JSON.stringify({ binding: BINDING, rows: q })); window.__fbq = null; return true; }
    catch (e) { recoveryRows = JSON.parse(JSON.stringify(q)); queueError = "device storage write failed; newest outbox is memory-only; export source records before leaving"; return false; }
  }

  /* ---------- deterministic id ----------------------------------------
     FNV-1a over the fields that make a record what it is. Two exports of
     the same record produce the same id; two genuinely different records
     do not. Timestamps added by the device are excluded on purpose. */
  function rid(rec) {
    if (typeof rec._rid === "string" && rec._rid) return rec._rid;
    // Stable source identity for NEW writes; legacy pending IDs are never read
    // or rewritten. Mutable attendance/answers must not fork a source report.
    if (typeof rec.id === "string" && rec.id) {
      return (rec.kind || "rec") + "_source_" + encodeURIComponent(rec.id);
    }
    return legacyRid(rec);
  }
  function legacyRid(rec) {
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
          getDocsFromServer: fsMod.getDocsFromServer,
          startAfter: fsMod.startAfter, documentId: fsMod.documentId,
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
     Returns immediately once the record is safe on this device. The
     network attempt continues in the background; the caller is told the
     truth either way, never "sent" when it was not. */
  function submit(rec) {
    var r = JSON.parse(JSON.stringify(rec || {}));
    r._rid = rid(r);
    r._device_ts = new Date().toISOString();
    var q = queue();
    if (queueError) return Promise.resolve({ local: false, persisted: false, remote: false, error: queueError });
    /* already queued and unsent? replace rather than add a second copy */
    var at = -1;
    for (var i = 0; i < q.length; i++) { if (q[i]._rid === r._rid) { at = i; break; } }
    if (at >= 0) q[at] = r; else q.push(r);
    var persisted = setQueue(q);

    var out = { local: true, persisted: persisted, rid: r._rid, remote: false, error: "" };
    if (!state.ready || !navigator.onLine || !persisted) {
      out.error = state.configured ? (state.error || "not connected yet") : "not configured";
      announce();
      return Promise.resolve(out);
    }
    return flush().then(function () {
      // A correction may have arrived while the preceding revision was in flight.
      if (queue().some(function (x) { return x._rid === r._rid && JSON.stringify(x) === JSON.stringify(r); })) return flush();
    }).then(function () {
      out.remote = !queue().some(function (x) { return x._rid === r._rid; });
      if (!out.remote) out.error = "delivery pending";
      return out;
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
                    "focal_name", "focal_phone", "focal_email"];

  function push(r) {
    var body = JSON.parse(JSON.stringify(r));
    delete body._device_ts;
    for (var i = 0; i < NEVER_SENT.length; i++) delete body[NEVER_SENT[i]];
    body.server_ts = api.serverTimestamp();
    body.device_ts = r._device_ts;
    return api.setDoc(api.doc(db, COLL, r._rid), body);
  }

  function drop(r) {
    // An old acknowledgment must not retire a correction queued in flight.
    setQueue(queue().filter(function (x) { return JSON.stringify(x) !== JSON.stringify(r); }));
  }

  /* ---------- flush ---------------------------------------------------
     Sequential, not parallel: a phone on one bar of signal handles one
     write at a time far better than twenty at once. */
  function flush() {
    if (flushing) return flushing;
    if (recoveryRows !== null || queueError) return Promise.resolve({ sent: 0, left: queue().length, error: queueError });
    if (!state.ready || !navigator.onLine) return Promise.resolve({ sent: 0, left: queue().length });
    var q = queue().slice(), sent = 0;
    flushing = q.reduce(function (chain, r) {
      return chain.then(function () {
        return push(r).then(function () { sent++; drop(r); })
                      .catch(function () { /* stays queued */ });
      });
    }, Promise.resolve()).then(function () {
      announce();
      flushing = null;
      return { sent: sent, left: queue().length };
    });
    return flushing;
  }

  window.addEventListener("online", function () { flush(); announce(); });
  window.addEventListener("offline", announce);

  /* ---------- read (coordination side, needs a signed-in user) -------- */
  function watch(cb, onErr) {
    if (onErr) onErr("incomplete: unscoped register reads disabled; use watchKind");
    return function () {};
  }

  /* watchKind -- the scoped query every reader has to use.
     Rules v3 opens one kind of record and only that kind, and Firestore
     evaluates a query against its POTENTIAL result set: "security rules are
     not filters ... queries are all or nothing". So an anonymous reader must
     name the kind in the query itself; watch() above, which names nothing, is
     refused outright even when every document in the collection would pass.

     Enumeration orders by document ID, not an optional timestamp; every page
     retains the exact same kind filter. Missing indexes/permission/network
     errors refuse the complete view, never fall back to a partial subset. */
  // Authorized, server-only, bounded enumeration. Document-ID ordering includes
  // documents without server_ts and needs no new composite-index grant.
  // Two identical scans detect observed drift, NOT an atomic Firestore snapshot.
  async function readKindComplete(kind, options) {
    options = options || {};
    if (!state.ready || !navigator.onLine) throw new Error("incomplete: server unavailable");
    if (!state.user || typeof state.user.uid !== "string" || !state.user.uid) throw new Error("incomplete: authenticated identity required");
    if (typeof kind !== "string" || !kind) throw new Error("incomplete: explicit kind required");
    var maxRows = options.maxRows === undefined ? 10000 : options.maxRows;
    if (!Number.isInteger(maxRows) || maxRows < 1 || maxRows > 10000) throw new Error("invalid row bound");
    var user = state.user && state.user.uid, deadline = Date.now() + 30000;
    async function scan() {
      var rows = [], cursor = null, seen = new Set();
      while (true) {
        if ((state.user && state.user.uid) !== user) throw new Error("incomplete: session changed");
        var terms = [api.where("kind", "==", kind), api.orderBy(api.documentId()), api.limit(500)];
        if (cursor) terms.push(api.startAfter(cursor));
        var remaining = deadline - Date.now(), timeout;
        if (remaining <= 0) throw new Error("incomplete: read deadline exceeded");
        var snap;
        try {
          snap = await Promise.race([
            api.getDocsFromServer(api.query(api.collection(db, COLL), ...terms)),
            new Promise(function (_, reject) { timeout = setTimeout(function () { reject(new Error("incomplete: read deadline exceeded")); }, remaining); })
          ]);
        } finally { clearTimeout(timeout); }
        if (!snap.metadata || snap.metadata.fromCache || snap.metadata.hasPendingWrites) throw new Error("incomplete: unconfirmed server page");
        if (snap.size > 500) throw new Error("incomplete: invalid page size");
        for (var d of snap.docs) {
          if (seen.has(d.id) || (cursor && d.id <= cursor.id)) throw new Error("incomplete: cursor drift");
          var o = d.data();
          if (o.kind !== kind) throw new Error("incomplete: scope mismatch");
          seen.add(d.id); rows.push(Object.assign({}, o, { _id: d.id }));
          if (rows.length > maxRows) throw new Error("incomplete: row bound exceeded (" + maxRows + ")");
          cursor = d;
        }
        if (snap.size < 500) return rows;
      }
    }
    function canonical(value) {
      if (Array.isArray(value)) return value.map(canonical);
      if (value && typeof value === "object") {
        var out = {}; Object.keys(value).sort().forEach(function (key) { out[key] = canonical(value[key]); }); return out;
      }
      return value;
    }
    var first = await scan(), second = await scan();
    if (JSON.stringify(canonical(first)) !== JSON.stringify(canonical(second))) throw new Error("incomplete: register drift; retry a quiet interval");
    if ((state.user && state.user.uid) !== user) throw new Error("incomplete: session changed");
    return { rows: second, complete: true, count: second.length, maxRows: maxRows,
      consistency: "two matching server enumerations; not atomic", capturedAt: new Date().toISOString() };
  }

  function watchKind(kind, cb, onErr, onState) {
    var stopped = false, busy = false;
    async function refresh() {
      if (stopped || busy) return;
      busy = true;
      if (onState) onState({ complete: false, reason: "Reading and validating all authorized pages" });
      try {
        var result = await readKindComplete(kind);
        if (!stopped) { if (onState) onState(result); cb(result.rows, result); }
      } catch (e) {
        if (!stopped) {
          if (onState) onState({ complete: false, reason: e.message });
          if (onErr) onErr(e && e.message ? e.message : String(e));
        }
      } finally { busy = false; }
    }
    refresh();
    var timer = setInterval(refresh, 60000);
    return function () { stopped = true; clearInterval(timer); };
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
      if (!st.configured) {
        cls = "off";
        msg = "<b>Saving to this device only.</b> No database is connected yet, so records stay here " +
              "until you export them. Nothing is lost.";
      } else if (!st.ready) {
        cls = "warn";
        msg = "<b>Not connected to the database.</b> " +
              (st.online ? "Retrying. " : "No signal. ") +
              "Records are safe on this phone" + (st.pending ? " — " + st.pending + " waiting to send." : ".");
      } else if (st.pending) {
        cls = "warn";
        msg = "<b>" + st.pending + " record(s) still to send.</b> " +
              (st.online ? "Sending now." : "They go as soon as you have signal.");
      } else {
        msg = "<b>Connected.</b> Records reach coordination as you save them." +
              (st.user ? " Signed in as " + st.user.email + "." : "");
      }
      bar.className = cls;
      if (st.legacyQuarantined || st.queueError) {
        bar.className = "warn";
        msg += " <b>Legacy/invalid outbox quarantined unchanged.</b> It is NOT sent or counted as delivered. Private export and destination review are required.";
      }
      bar.innerHTML = '<span class="m">' + msg + "</span>";
      if (st.legacyQuarantined) {
        var ex = document.createElement("button");
        ex.type = "button"; ex.textContent = "Export private legacy outbox";
        ex.onclick = function () {
          var raw;
          try { raw = exportLegacyQueue(true); } catch (e) { return; }
          if (raw === null) return;
          var url = URL.createObjectURL(new Blob([raw], { type: "application/octet-stream" }));
          var link = document.createElement("a"); link.href = url; link.download = "mhpss-private-legacy-outbox.json";
          link.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        };
        bar.appendChild(ex);
      }
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
    submit: submit, flush: flush, queue: queue, rid: rid, legacyRid: legacyRid, exportLegacyQueue: exportLegacyQueue,
    readKindComplete: readKindComplete,
    watch: watch, watchKind: watchKind, signIn: signIn, signOut: signOutNow,
    clearQueue: function () { setQueue([]); announce(); }
  };
})();
