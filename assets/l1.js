/* =====================================================================
   MHPSS Nepal — Layer 1 shared helpers
   ---------------------------------------------------------------------
   Global rather than an ES module for the same reason as codes.js: the
   forms must open straight from a file with no server, and browsers
   refuse module imports over file://.

   NOTHING HERE SENDS DATA ANYWHERE. There is no fetch, no XHR, no
   WebSocket, no form action. Records stay in the browser that made them
   until a person exports them deliberately.
   ===================================================================== */
(function () {
  "use strict";

  /* ---------- contact code -------------------------------------------
     Two FNV-1a passes over the same string with different offset bases,
     concatenated and cut to five base-36 characters each. That is about
     3.7e15 possible codes: at 200,000 records the chance of any collision
     is a few in a million, which is a curiosity rather than a data-quality
     problem.

     This is a PSEUDONYM, not an anonymous token. The inputs (initials,
     birth year, sex, municipality) vary little, so a person holding a
     candidate list could test names against a code. It is adequate for
     agreeing the questions. A live register needs the hash salted with
     a secret the handset never holds, which requires a server.
     ------------------------------------------------------------------ */
  function fnv(str, basis) {
    var h = basis >>> 0;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h >>> 0;
  }
  function pad(s, n) { while (s.length < n) s = "0" + s; return s; }

  function contactCode(parts) {
    var norm = parts
      .map(function (p) { return String(p == null ? "" : p).trim().toUpperCase().replace(/\s+/g, ""); })
      .join("|");
    if (!norm.replace(/\|/g, "")) return "";
    var a = pad(fnv(norm, 0x811c9dc5).toString(36), 7).toUpperCase().slice(-5);
    var b = pad(fnv(norm, 0x1000193).toString(36), 7).toUpperCase().slice(-5);
    return "NP-" + a + "-" + b;
  }

  /* ---------- storage ----------------------------------------------- */
  var mem = {};
  var KIND_ALIAS = {
    contact: { storage: "contact", queue: ["contact", "service_contact"] },
    service_contact: { storage: "contact", queue: ["contact", "service_contact"] },
    selfreport: { storage: "selfreport", queue: ["selfreport", "self_report"] },
    self_report: { storage: "selfreport", queue: ["selfreport", "self_report"] }
  };
  function storageKind(kind) {
    return KIND_ALIAS[kind] ? KIND_ALIAS[kind].storage : kind;
  }
  function queueKinds(kind) {
    return KIND_ALIAS[kind] ? KIND_ALIAS[kind].queue.slice() : [kind];
  }
  function key(kind) { return "mhpss-np-l1-" + storageKind(kind) + "-v1"; }

  function all(kind) {
    kind = storageKind(kind);
    if (Object.prototype.hasOwnProperty.call(mem, kind)) return mem[kind];
    try {
      var raw = localStorage.getItem(key(kind));
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return mem[kind] || [];
    }
  }
  function writeAll(kind, list) {
    kind = storageKind(kind);
    try {
      localStorage.setItem(key(kind), JSON.stringify(list));
      delete mem[kind];
      return true;
    } catch (e) {
      mem[kind] = list;
      return false;
    }
  }
  function save(kind, obj) {
    kind = storageKind(kind);
    if (window.FB && typeof window.FB.ensureEventId === "function") {
      window.FB.ensureEventId(obj);
    }
    var list = all(kind);
    obj._saved = new Date().toISOString();
    list.push(obj);
    var persisted = writeAll(kind, list);

    if (!persisted) {
      var message = "This record is only in memory because browser storage failed. Export it before closing this page.";
      if (window.FB && typeof window.FB.reportPersistenceFailure === "function") {
        window.FB.reportPersistenceFailure(message);
      }
      return {
        count: list.length,
        persisted: false,
        sourcePersisted: false,
        queuePersisted: false,
        acknowledged: false,
        ackState: "not-acknowledged",
        deliveryState: "volatile",
        recoveryRequired: true,
        synced: null
      };
    }

    /* The persisted device copy is written first. Only then is a push
       attempted, and a failed push leaves the record queued. */
    var synced = null;
    if (window.FB && typeof window.FB.submit === "function") {
      synced = window.FB.submit(obj);
    }
    var syncResult = synced && synced.result ? synced.result : synced;
    var queuePersisted = !!(syncResult && syncResult.queuePersisted);
    return {
      count: list.length,
      persisted: persisted, /* compatibility alias: source storage only */
      sourcePersisted: persisted,
      queuePersisted: queuePersisted,
      acknowledged: !!(syncResult && syncResult.acknowledged),
      ackState: syncResult && syncResult.ackState || "not-acknowledged",
      deliveryState: syncResult && syncResult.deliveryState || "not-queued",
      recoveryRequired: !queuePersisted,
      synced: synced
    };
  }
  function clear(kind) {
    var sourceKind = storageKind(kind);
    var list = all(kind);
    if (!window.FB || typeof window.FB.clearQueue !== "function" ||
        typeof window.FB.restoreQueue !== "function") {
      var unavailableMessage = "Cannot verify that this form's unsent queue was cleared.";
      if (typeof window.alert === "function") window.alert(unavailableMessage);
      var unavailable = new Error(unavailableMessage);
      unavailable.code = "PERSISTENCE_FAILED";
      throw unavailable;
    }
    var queueResult;
    try {
      queueResult = window.FB.clearQueue({
        kinds: queueKinds(kind),
        rids: list.map(function (r) { return r && r._rid; }).filter(Boolean)
      });
    } catch (e) {
      var queueMessage = e && e.message ? e.message : "Could not clear this form's unsent queue.";
      if (typeof window.FB.reportPersistenceFailure === "function") {
        window.FB.reportPersistenceFailure(queueMessage);
      } else if (typeof window.alert === "function") {
        window.alert(queueMessage);
      }
      throw e;
    }
    try { localStorage.removeItem(key(kind)); }
    catch (e) {
      var rollbackFailed = false;
      try { window.FB.restoreQueue(queueResult); }
      catch (rollbackError) { rollbackFailed = true; }
      var message = rollbackFailed
        ? "HIGH-SEVERITY WARNING: saved records could not be cleared, and the original send queue could not be restored to device storage. Do not close this page; export the records now and ask coordination to recover the send queue. Nothing was reported as cleared."
        : "Could not clear the saved records from this device. The original send queue was restored; nothing was cleared.";
      if (typeof window.FB.reportPersistenceFailure === "function") {
        window.FB.reportPersistenceFailure(message);
      } else if (typeof window.alert === "function") {
        window.alert(message);
      }
      var error = new Error(message);
      error.code = "PERSISTENCE_FAILED";
      error.severity = rollbackFailed ? "high" : "error";
      error.rollbackFailed = rollbackFailed;
      throw error;
    }
    mem[sourceKind] = [];
    return { cleared: true, queueCleared: queueResult.queueCleared };
  }
  function storageWorks() {
    try {
      var k = "mhpss-np-probe";
      localStorage.setItem(k, "1");
      localStorage.removeItem(k);
      return true;
    } catch (e) { return false; }
  }

  /* ---------- export ------------------------------------------------- */
  function stamp() {
    var d = new Date(), p = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + "_" + p(d.getHours()) + p(d.getMinutes());
  }
  function csvCell(v) {
    var s = v == null ? "" : String(v);
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function toCSV(list, columns) {
    var head = columns.join(",");
    var body = list.map(function (r) {
      return columns.map(function (c) { return csvCell(r[c]); }).join(",");
    });
    return [head].concat(body).join("\r\n") + "\r\n";
  }
  function download(filename, text, mime) {
    var blob = new Blob([text], { type: (mime || "text/plain") + ";charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
  }

  /* ---------- location ----------------------------------------------
     Rounded to 3 decimal places on purpose — about 110 m north–south and
     about 98 m east–west at Nepal's latitude. A precise pin on a shelter,
     combined with a small count and a target group, identifies people
     without ever recording a name. The coarse grid still puts a site on
     a map; it just stops the map from pointing at a household.
     ------------------------------------------------------------------ */
  var GEO_DP = 3;
  function geo(onOk, onErr) {
    if (!navigator.geolocation) { onErr("This browser cannot report a location."); return; }
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        var f = Math.pow(10, GEO_DP);
        onOk({
          lat: Math.round(pos.coords.latitude * f) / f,
          lon: Math.round(pos.coords.longitude * f) / f,
          accuracy_m: pos.coords.accuracy == null ? null : Math.round(pos.coords.accuracy),
          rounded_to_dp: GEO_DP
        });
      },
      function (err) {
        var m = { 1: "Permission for location was refused on this device.",
                  2: "Location is not available here — no signal or no GPS fix.",
                  3: "Finding the location took too long." };
        onErr(m[err.code] || "The location could not be read.");
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 }
    );
  }

  /* ---------- form plumbing ------------------------------------------ */
  function fillSelect(el, items, opts) {
    if (!el) return;
    opts = opts || {};
    var out = [];
    if (opts.placeholder !== false) {
      var phTxt = opts.placeholder || "— choose —";
      if (window.CODES && window.CODES.ph) phTxt = window.CODES.ph(phTxt);
      out.push('<option value="">' + phTxt + "</option>");
    }
    items.forEach(function (it) {
      var v, l;
      if (typeof it === "string") { v = it; l = it; }
      else {
        v = it[opts.value || "code"];
        /* Through CODES.label, so a list item that has a Nepali label shows
           it on the Nepali page. An explicit opts.label still wins, for the
           few places that want a specific field. */
        l = opts.label ? it[opts.label]
          : (window.CODES && window.CODES.label ? window.CODES.label(it) : it.name);
      }
      out.push('<option value="' + String(v).replace(/"/g, "&quot;") + '">' +
               String(l).replace(/</g, "&lt;") + "</option>");
    });
    el.innerHTML = out.join("");
    /* Remember how this select was filled, so switching language can refill
       it. Without this the dropdowns keep the language they were built in
       and the toggle appears to half-work. */
    el._refill = function () { fillSelect(el, items, opts); };
  }

  /* One listener per page: when the language changes, refill every select
     that fillSelect built, and put back whatever the user had chosen. A
     half-filled form must survive someone pressing NEP mid-entry. */
  document.addEventListener("i18n:changed", function () {
    var sels = document.querySelectorAll("select");
    for (var i = 0; i < sels.length; i++) {
      var el = sels[i];
      if (typeof el._refill !== "function") continue;
      var had = el.value;
      el._refill();
      if (had) el.value = had;
    }
    /* checkbox lists are rebuilt by the page that owns them */
    document.dispatchEvent(new CustomEvent("codes:relabel"));
  });
  function today() {
    var d = new Date(), p = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }
  function remember(id, value) {
    try { localStorage.setItem("mhpss-np-pref-" + id, value); } catch (e) { /* ignore */ }
  }
  function recall(id) {
    try { return localStorage.getItem("mhpss-np-pref-" + id) || ""; } catch (e) { return ""; }
  }

  window.L1 = {
    contactCode: contactCode,
    all: all, save: save, clear: clear, storageWorks: storageWorks,
    toCSV: toCSV, download: download, stamp: stamp,
    geo: geo, GEO_DP: GEO_DP,
    fillSelect: fillSelect, today: today, remember: remember, recall: recall
  };
})();
