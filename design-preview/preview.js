/* MHPSS Nepal — Layer 2 design-preview behaviour (synthetic only).
   Exploration artifact: the fixture below is generated in the page. There is no
   Firebase, no register read, no storage, no authentication, no export and no
   publication. Every figure on screen comes from this file. */
(function () {
  "use strict";

  /* ------------------------------------------------ synthetic fixture */
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var rnd = mulberry32(20260913);
  function pick(list) { return list[Math.floor(rnd() * list.length)]; }

  var ROSTER = [
    ["NP01", "Rasuwa", "Dhunche", 1], ["NP02", "Rasuwa", "Dhunche", 3],
    ["NP03", "Rasuwa", "Syafrubesi", 2, 1], ["NP04", "Rasuwa", "Syafrubesi", 4],
    ["NP05", "Rasuwa", "Uttargaya", 1, 1], ["NP06", "Rasuwa", "Uttargaya", 4],
    ["NP07", "Rasuwa", "Kalika", 2, 1], ["NP08", "Rasuwa", "Kalika", 5],
    ["NP09", "Rasuwa", "Aamachodingmo", 1], ["NP10", "Rasuwa", "Aamachodingmo", 3],
    ["NP11", "Rasuwa", "Naukunda", 2], ["NP12", "Rasuwa", "Gosaikunda", 1],
    ["NP13", "Nuwakot", "Bidur", 1], ["NP14", "Nuwakot", "Bidur", 4],
    ["NP15", "Nuwakot", "Trishuli", 2], ["NP16", "Nuwakot", "Trishuli", 6],
    ["NP17", "Nuwakot", "Dupcheshwar", 1, 1], ["NP18", "Nuwakot", "Kakani", 2, 1],
    ["NP19", "Nuwakot", "Likhu", 3, 1], ["NP20", "Nuwakot", "Belkotgadhi", 1],
    ["NP21", "Nuwakot", "Belkotgadhi", 5], ["NP22", "Nuwakot", "Kispang", 2],
    ["NP23", "Nuwakot", "Myagang", 1]
  ].map(function (r) {
    return { code: r[0], district: r[1], palika: r[2], ward: r[3], gap: !!r[4] };
  });

  var ORGS = ["TPO Nepal", "CMC-Nepal", "CWIN Nepal", "Nepal Red Cross",
              "KOSHISH", "SaMi", "Vidushi", "Government PSC", "NGO Federation"];
  var ACTS = [
    ["PFA", "Psychological first aid", "2", "2"],
    ["COMM", "Community support & awareness", "3", "3"],
    ["CNS", "Counselling", "2", "3"],
    ["REF", "Referral support", "2", "2"],
    ["PSED", "Psychoeducation", "3", "3"],
    ["REM", "Remote & helpline support", "2", "2"],
    ["SPEC", "Specialised care", "4", "4"]
  ];
  var MODS = ["In person · holding centre", "Community setting", "Remote / phone", "Static facility"];
  var TGS = ["Affected population", "Children", "Older people",
             "People with disability", "Pregnant / lactating", "Bereaved"];

  var DATA = [], seq = 0;
  ROSTER.forEach(function (site) {
    if (site.gap) return;                            /* the six intentional gaps */
    for (var d = 0; d < 12; d++) {
      var n = rnd() < 0.42 ? 0 : (rnd() < 0.72 ? 1 : 2);
      for (var j = 0; j < n; j++) {
        seq++;
        var a = pick(ACTS), st = rnd() < 0.78 ? "Completed" : (rnd() < 0.5 ? "Ongoing" : "Planned");
        DATA.push({
          id: "S" + String(seq).padStart(3, "0"),
          date: rnd() < 0.05 ? "" : "2026-09-" + String(2 + d).padStart(2, "0"),
          district: site.district, palika: site.palika, ward: "Ward " + site.ward,
          site: site.code, roster: true, org: pick(ORGS),
          activity: a[0], activityName: a[1], layer: "Layer " + a[2],
          modality: pick(MODS), status: st,
          target: pick(TGS), attendance: 4 + Math.floor(rnd() * 46),
          corrected: rnd() < 0.07
        });
      }
    }
  });
  /* Reported from places on neither list: kept separate from the denominator. */
  [["Rasuwa", "Off-roster · roadside", 2], ["Nuwakot", "Off-roster · school hall", 1],
   ["Rasuwa", "Off-roster · health post", 2], ["Nuwakot", "Off-roster · ward office", 3],
   ["Rasuwa", "Off-roster · camp", 1], ["Nuwakot", "Off-roster · outreach", 2]]
    .forEach(function (o) {
      seq++;
      var a = pick(ACTS);
      DATA.push({
        id: "O" + String(seq).padStart(3, "0"),
        date: "2026-09-" + String(2 + Math.floor(rnd() * 12)).padStart(2, "0"),
        district: o[0], palika: "Not on the roster", ward: "Not on the roster",
        site: o[1], roster: false, org: pick(ORGS),
        activity: a[0], activityName: a[1], layer: "Layer " + a[2],
        modality: pick(MODS), status: rnd() < 0.8 ? "Completed" : "Ongoing",
        target: pick(TGS), attendance: 5 + Math.floor(rnd() * 30), corrected: false
      });
    });

  var FLOOR = 5;               /* small-cell floor, printed on the page */
  var STATES = {
    fresh: { cls: "ok", title: "Synthetic fixture loaded",
      body: "Last successful refresh 13 Sep 2026, 14:20 · data date 13 Sep 2026 · source: synthetic review fixture (period 2–13 Sep 2026). Not a live register." },
    stale: { cls: "warn", title: "Showing the last successful refresh",
      body: "The most recent refresh did not complete. These figures are from 13 Sep 2026 and may be out of date — nothing has been silently replaced, and no partial refresh has been merged in." },
    failed: { cls: "stop", title: "This view could not be refreshed",
      body: "The refresh failed. The best last-known contribution is shown, labelled with its own date. Nothing is hidden and no zero is shown in place of a missing value." }
  };
  window.__PREVIEW_STATE = "fresh";

  /* ---------------------------------------------------- filter model */
  var DIMENSIONS = [
    { key: "period", label: "Reporting period",
      values: [["", "All dates in the fixture"], ["7d", "Last 7 days (7–13 Sep)"], ["30d", "Whole fixture period"]] },
    { key: "district", label: "District", of: function (r) { return r.district; } },
    { key: "palika", label: "Palika", of: function (r) { return r.palika; } },
    { key: "ward", label: "Ward", of: function (r) { return r.ward; } },
    { key: "org", label: "Organisation", of: function (r) { return r.org; } },
    { key: "activity", label: "Activity", of: function (r) { return r.activityName; } },
    { key: "layer", label: "IASC layer", of: function (r) { return r.layer; } },
    { key: "modality", label: "Modality", of: function (r) { return r.modality; } },
    { key: "status", label: "Status", of: function (r) { return r.status; } },
    { key: "target", label: "Target group", of: function (r) { return r.target; } },
    { key: "quality", label: "Data-quality state", of: function (r) {
        if (!r.date) return "No activity date";
        if (!r.roster) return "Off-roster site";
        if (r.corrected) return "Carries a correction";
        return "No flag";
      }, values: null }
  ];
  var FILTER = {}, QUERY = "";
  DIMENSIONS.forEach(function (d) { FILTER[d.key] = ""; });

  /* Presentation-only shareable state. The filter selection lives in the URL
     fragment under a distinct `#flt=` prefix, so it never collides with the
     section anchors (#coverage, #reports …) the concepts also use. It holds a
     filter name and value and the search text — never record data, never an
     identifier, never a credential, and it never travels to a server. */
  var HASH_PREFIX = "flt=";
  function readHash() {
    var h = (location.hash || "").replace(/^#/, "");
    if (h.indexOf(HASH_PREFIX) !== 0) return false;
    h.slice(HASH_PREFIX.length).split("&").forEach(function (pair) {
      var i = pair.indexOf("=");
      if (i < 0) return;
      var k = decodeURIComponent(pair.slice(0, i)), v = decodeURIComponent(pair.slice(i + 1));
      if (k === "q") { QUERY = v; return; }
      if (Object.prototype.hasOwnProperty.call(FILTER, k)) FILTER[k] = v;
    });
    return true;
  }
  function writeHash() {
    var parts = [];
    DIMENSIONS.forEach(function (d) {
      if (FILTER[d.key]) parts.push(encodeURIComponent(d.key) + "=" + encodeURIComponent(FILTER[d.key]));
    });
    if (QUERY) parts.push("q=" + encodeURIComponent(QUERY));
    try {
      var owns = (location.hash || "").indexOf("#" + HASH_PREFIX) === 0;
      if (!parts.length && !owns) return;        /* leave section anchors alone */
      var h = parts.length ? "#" + HASH_PREFIX + parts.join("&") : location.pathname;
      if (history.replaceState) history.replaceState(null, "", h);
    } catch (e) { /* a sandboxed or file:// context: the view still works */ }
  }

  function matches(r) {
    if (!QUERY) return true;
    var hay = (r.site + " " + r.org + " " + r.palika + " " + r.district + " " + r.activityName + " " + r.ward + " " + r.status).toLowerCase();
    return QUERY.toLowerCase().split(/\s+/).filter(Boolean).every(function (term) { return hay.indexOf(term) >= 0; });
  }
  function inPeriod(r, key) {
    if (key === "30d" || !key) return true;
    if (!r.date) return false;                 /* undated never folds into a period */
    return key === "7d" ? parseInt(r.date.slice(8), 10) >= 7 : true;
  }
  function passes(r, skip) {
    if (!matches(r)) return false;
    if (skip !== "period" && !inPeriod(r, FILTER.period)) return false;
    for (var i = 0; i < DIMENSIONS.length; i++) {
      var d = DIMENSIONS[i];
      if (!d.of || d.key === skip) continue;
      if (FILTER[d.key] && d.of(r) !== FILTER[d.key]) return false;
    }
    return true;
  }
  function selected() { return DATA.filter(function (r) { return passes(r, null); }); }
  function activeCount() {
    return DIMENSIONS.filter(function (d) { return FILTER[d.key]; }).length + (QUERY ? 1 : 0);
  }

  /* ----------------------------------------------------- aggregation */
  function agg() {
    var rows = selected();
    var bySite = {}, offsite = {}, byOrg = {}, byAct = {}, byLayer = {}, byDist = {}, byPalika = {};
    var flags = { undated: 0, offroster: 0, overlap: 0, corrected: 0 };
    var seen = {};
    rows.forEach(function (r) {
      var s = bySite[r.site] || (bySite[r.site] = { code: r.site, district: r.district, palika: r.palika, ward: r.ward, roster: r.roster, reports: 0, people: 0, orgs: {}, last: "" });
      s.reports++; s.people += r.attendance; s.orgs[r.org] = 1;
      if (r.date && r.date > s.last) s.last = r.date;
      if (!r.roster) {
        var o = offsite[r.site] || (offsite[r.site] = { site: r.site, district: r.district, reports: 0, people: 0 });
        o.reports++; o.people += r.attendance;
      }
      byOrg[r.org] = (byOrg[r.org] || 0) + 1;
      byAct[r.activityName] = (byAct[r.activityName] || 0) + 1;
      byLayer[r.layer] = (byLayer[r.layer] || 0) + 1;
      byDist[r.district] = (byDist[r.district] || 0) + 1;
      byPalika[r.palika] = (byPalika[r.palika] || 0) + 1;
      if (!r.date) flags.undated++;
      if (!r.roster) flags.offroster++;
      if (r.corrected) flags.corrected++;
      var k = r.site + "|" + r.date + "|" + r.org;
      if (seen[k]) flags.overlap++; else seen[k] = 1;
    });
    var covered = {};
    rows.forEach(function (r) { if (r.roster) covered[r.site] = 1; });
    var days = [];
    rows.forEach(function (r) { if (r.date && days.indexOf(r.date) < 0) days.push(r.date); });
    days.sort();
    var rosterInScope = ROSTER.filter(function (s) {
      if (FILTER.district && s.district !== FILTER.district) return false;
      if (FILTER.palika && s.palika !== FILTER.palika) return false;
      if (FILTER.ward && "Ward " + s.ward !== FILTER.ward) return false;
      return true;
    });
    /* A report's organisation/activity filters do not change the denominator:
       a site with no PFA report is still a site with no PFA report. */
    var gaps = rosterInScope.filter(function (s) { return !covered[s.code]; });
    return {
      rows: rows, bySite: bySite, offsite: offsite, byOrg: byOrg, byAct: byAct,
      byLayer: byLayer, byDist: byDist, byPalika: byPalika, flags: flags,
      rosterInScope: rosterInScope, gaps: gaps, coveredCount: rosterInScope.length - gaps.length,
      people: rows.reduce(function (a, r) { return a + r.attendance; }, 0),
      dayList: days
    };
  }
  function ranked(obj, limit) {
    var rows = Object.keys(obj).map(function (k) { return { k: k, v: obj[k] }; })
      .sort(function (a, b) { return b.v - a.v; });
    return limit > 0 ? rows.slice(0, limit) : rows;
  }
  function fmt(n) { return Number(n).toLocaleString("en-GB"); }
  /* Small-cell floor applies to PEOPLE-based figures. A report count is not a
     person; it is printed exactly. */
  function people(n) { return n < FLOOR ? "fewer than " + FLOOR : fmt(n); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function byId(id) { return document.getElementById(id); }
  function setHTML(id, html) { var el = byId(id); if (el) el.innerHTML = html; }
  function setText(id, txt) { var el = byId(id); if (el) el.textContent = txt; }
  function bind(root, sel, ev, fn) {
    if (!root) return;
    root.querySelectorAll(sel).forEach(function (n) { n.addEventListener(ev, fn); });
  }

  /* ------------------------------------------------- cascade options */
  function optionValues(dim) {
    if (dim.values) return null;                     /* fixed period list */
    var counts = {};
    DATA.forEach(function (r) { if (passes(r, dim.key)) counts[dim.of(r)] = (counts[dim.of(r)] || 0) + 1; });
    return counts;
  }

  function buildFilters() {
    var host = byId("filterHost");
    if (!host) return;
    var html = '<div class="filter-head"><label class="search-cell"><span>Search — organisation, site, activity, palika</span>' +
      '<input type="search" id="filterSearch" placeholder="Type to narrow every block" value="' + esc(QUERY) + '"></label>' +
      '<div class="filter-head-btns"><button type="button" class="quiet" data-clear>Clear all</button>' +
      '<button type="button" class="secondary sheet-close" data-close-hidden aria-label="Close filters">Close</button></div></div><div class="filter-grid">';
    DIMENSIONS.forEach(function (d) {
      var inner;
      if (d.values) {
        inner = d.values.map(function (v) {
          return '<option value="' + esc(v[0]) + '">' + esc(v[1]) + "</option>";
        }).join("");
      } else {
        var counts = optionValues(d);
        var vals = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
        if (vals.length < 2) return;        /* a dimension that cannot slice is not offered */
        inner = '<option value="">All (' + vals.length + ")</option>" + vals.map(function (v) {
          return '<option value="' + esc(v) + '">' + esc(v) + " (" + counts[v] + ")</option>";
        }).join("");
      }
      html += '<label class="filter-cell"><span>' + esc(d.label) + "</span>" +
        '<select data-dim="' + d.key + '">' + inner + "</select></label>";
    });
    html += '</div><p>Each list offers only the values that survive the other filters, so no choice empties the page by surprise. ' +
      'The selection is written to the address bar as a shareable, presentation-only link: it carries filter names, never record data. ' +
      'Period never folds in a report with no date.</p>';
    host.innerHTML = html;
    host.querySelectorAll("select[data-dim]").forEach(function (sel) {
      sel.value = FILTER[sel.getAttribute("data-dim")] || "";
      sel.addEventListener("change", function () {
        FILTER[this.getAttribute("data-dim")] = this.value;
        render();
      });
    });
    var search = byId("filterSearch");
    if (search) {
      var t = null;
      search.addEventListener("input", function () {
        var v = this.value;
        clearTimeout(t);
        t = setTimeout(function () { QUERY = v.trim(); render(); }, 180);
      });
    }
    bind(host, "[data-clear]", "click", clearFilters);
  }
  function clearFilters() { DIMENSIONS.forEach(function (d) { FILTER[d.key] = ""; }); QUERY = ""; render(); }

  function renderStrip(a) {
    var chips = DIMENSIONS.filter(function (d) { return FILTER[d.key]; }).map(function (d) {
      var label = FILTER[d.key];
      if (d.key === "period") {
        var m = (d.values || []).filter(function (v) { return v[0] === FILTER[d.key]; })[0];
        label = m ? m[1] : FILTER[d.key];
      }
      return '<button type="button" class="chip" data-clear-dim="' + d.key + '">' + esc(d.label) + ": " +
        esc(label) + ' <span aria-hidden="true">×</span><span class="sr">Remove this filter</span></button>';
    });
    if (QUERY) {
      chips.push('<button type="button" class="chip" data-clear-dim="q">Search: ' + esc(QUERY) +
        ' <span aria-hidden="true">×</span><span class="sr">Remove this filter</span></button>');
    }
    setHTML("activeChips", chips.join("") || '<span class="chip empty">No filters active — showing all ' +
      fmt(DATA.length) + ' synthetic reports</span>');
    bind(byId("activeChips"), "[data-clear-dim]", "click", function () {
      var k = this.getAttribute("data-clear-dim");
      if (k === "q") QUERY = ""; else FILTER[k] = "";
      render();
    });
    setHTML("resultCount", "<b>" + fmt(a.rows.length) + "</b> of " + fmt(DATA.length) + " reports · <b>" +
      activeCount() + "</b> filter" + (activeCount() === 1 ? "" : "s") + " active" +
      (DIMENSIONS.filter(function (d) { return FILTER[d.key]; }).length > 3 ? " · narrow the view for detail" : ""));
    var t = byId("filterToggle");
    if (t) {
      var p = byId("filterPanel");
      t.setAttribute("aria-expanded", String(!!p && !p.hidden));
      var c = t.querySelector(".count");
      if (c) c.textContent = String(activeCount());
    }
    writeHash();
  }

  /* --------------------------------------------------------- views */
  function kpiCard(v, l, n, cls) {
    return '<article class="kpi ' + (cls || "") + '"><strong>' + esc(v) + "</strong><span>" + esc(l) +
      "</span>" + (n ? "<small>" + esc(n) + "</small>" : "") + "</article>";
  }
  function viewKpis(a) {
    var last = a.dayList.length ? a.dayList[a.dayList.length - 1] : "—";
    var pct = a.rosterInScope.length ? Math.round(100 * a.coveredCount / a.rosterInScope.length) : 0;
    setHTML("kpiRow",
      kpiCard(a.coveredCount + " / " + a.rosterInScope.length, "Roster sites reporting",
        pct + "% of the roster in this selection", pct < 80 ? "bad" : "ok") +
      kpiCard(a.gaps.length + "", "Roster sites with no report",
        "The gap is the point, not the total", a.gaps.length ? "bad" : "ok") +
      kpiCard(fmt(a.rows.length), "Activity reports",
        "One row is one session, on one day, at one place") +
      kpiCard(people(a.people), "Attendances",
        "Sessions, not unique people — never added to people") +
      kpiCard(fmt(a.flags.undated), "Reports with no activity date",
        "Outside every period, counted not folded in", a.flags.undated ? "warn" : "ok") +
      kpiCard(last, "Latest activity date",
        "Newest date among the selected reports"));
    setText("heroGap", String(a.gaps.length));
    setText("heroOrgs", String(Object.keys(a.byOrg).length));
    setText("heroReports", fmt(a.rows.length));
    setText("heroDate", last);
    var sub = byId("heroSub");
    if (sub) {
      sub.textContent = a.gaps.length
        ? a.gaps.length + " of " + a.rosterInScope.length + " roster sites in this selection have no activity report. " +
          "Coverage against the roster is the headline, not the total: an aggregate can look healthy while a whole site has nobody reporting."
        : "Every roster site in this selection has at least one report. A site with one report is covered, not necessarily served — coverage is not reach.";
    }
  }

  function viewFreshness() {
    var host = byId("freshness");
    if (!host) return;
    var s = STATES[window.__PREVIEW_STATE] || STATES.fresh;
    host.className = "freshness " + s.cls;
    host.innerHTML =
      '<span class="dot" aria-hidden="true"></span>' +
      '<span class="freshline"><b>' + esc(s.title) + "</b>" +
      '<span class="sep">·</span>data date 13 Sep 2026' +
      '<span class="sep">·</span>refresh 14:20' +
      '<span class="sep">·</span>source: synthetic review fixture</span>' +
      '<details class="freshmore"><summary>Status &amp; method</summary><p>' + esc(s.body) +
      "</p><p>Source, data date, capture state and the small-cell floor (" + FLOOR +
      ") are printed on the page, not hidden in a note. A failed refresh shows the last good snapshot with a " +
      "warning, never a blank page or a page of zeros. This fixture is not a live register.</p></details>";
  }

  function viewCoverage(a) {
    var root = byId("coverageHost");
    if (!root) return;
    var cards = a.rosterInScope.map(function (s) {
      var d = a.bySite[s.code];
      var orgs = d ? Object.keys(d.orgs).length : 0;
      var st = !d ? "none" : (orgs <= 1 ? "thin" : "ok");
      var label = !d ? "No report" : (orgs === 1 ? "1 organisation" : orgs + " organisations");
      var names = d ? ranked(d.orgs, 3).map(function (o) { return o.k; }).join(", ") : "—";
      return '<article class="site ' + st + '" role="listitem"><header><b>' + esc(s.code) + " · " + esc(s.palika) +
        "</b><span>" + esc(s.district) + " · " + esc(s.ward) + "</span></header><strong>" + esc(label) +
        '</strong><p class="site-meta">Reports: ' + fmt(d ? d.reports : 0) + " · Attendances: " + people(d ? d.people : 0) +
        " · Last: " + esc(d && d.last ? d.last : "—") + "</p><details><summary>Detail &amp; methods</summary><p>Organisations here: " +
        esc(names) + ". Attendance below " + FLOOR + " reads “fewer than " + FLOOR + "”, so no cell can point to one session. " +
        "Roster membership is a separate question this fixture does not settle.</p></details></article>";
    }).join("");
    var off = ranked(a.offsite, 30).map(function (o) {
      var x = a.offsite[o.k];
      return "<li><b>" + esc(x.site) + "</b><span>" + esc(x.district) + " · " + fmt(x.reports) +
        " reports · " + people(x.people) + " attendances</span></li>";
    }).join("");
    root.innerHTML = '<div class="site-grid" role="list" aria-label="Roster sites and their reporting status">' +
      (cards || '<p class="muted">No roster site matches the current filter.</p>') + "</div>" +
      '<div class="offroster"><h3>Reported, but not on the roster</h3><p class="muted">Shown separately: never counted as a covered site, never counted as a gap.</p>' +
      (off ? "<ul>" + off + "</ul>" : '<p class="muted">None in this selection.</p>') + "</div>";
  }

  function bars(hostId, obj, dimKey, limit, note) {
    var all = ranked(obj, 0), rows = all.slice(0, limit);
    var max = rows.length ? rows[0].v : 1;
    var total = all.reduce(function (a, r) { return a + r.v; }, 0);
    var rest = total - rows.reduce(function (a, r) { return a + r.v; }, 0);
    var restNote = (rest > 0 && all.length > rows.length)
      ? '<p class="muted remainder">Top ' + rows.length + " of " + all.length + " shown. The other " +
        (all.length - rows.length) + " account for the remaining " + fmt(rest) + " reports; " +
        "the bars above are a ranking, not a sum of the selection.</p>"
      : "";
    setHTML(hostId, (rows.map(function (r) {
      return '<button type="button" class="bar-row" data-set-dim="' + dimKey + '" data-set-val="' + esc(r.k) +
        '" aria-pressed="' + (FILTER[dimKey] === r.k) + '" aria-label="Filter by ' + esc(r.k) + ", " + r.v +
        ' reports"><span class="bar-label">' + esc(r.k) +
        '</span><span class="bar-track" aria-hidden="true"><i style="width:' + Math.round(100 * r.v / max) +
        '%"></i></span><span class="bar-value">' + fmt(r.v) + "</span></button>";
    }).join("") || '<p class="muted">Nothing matches the current filter — clear a filter to widen the view.</p>') +
      restNote + (note ? '<p class="muted">' + note + "</p>" : ""));
    bind(byId(hostId), "[data-set-dim]", "click", function () {
      var d = this.getAttribute("data-set-dim"), v = this.getAttribute("data-set-val");
      FILTER[d] = FILTER[d] === v ? "" : v;
      render();
    });
  }

  function viewMix(a) {
    bars("orgHost", a.byOrg, "org", 6, "Report counts per organisation; clicking a bar filters the whole page.");
    bars("actHost", a.byAct, "activity", 7, "One row is one report: these rows are not additive across target groups.");
    bars("layerHost", a.byLayer, "layer", 4, "The IASC layer is read from the activity code, never typed.");
    var total = a.rows.length || 1, dist = ranked(a.byDist, 6), maxD = dist.length ? dist[0].v : 1;
    setHTML("distHost", (dist.map(function (r) {
      return '<button type="button" class="dist-row" data-set-dim="district" data-set-val="' + esc(r.k) +
        '" aria-pressed="' + (FILTER.district === r.k) + '"><span class="dist-name">' + esc(r.k) +
        '</span><span class="dist-track" aria-hidden="true"><i style="width:' + Math.round(100 * r.v / maxD) +
        '%"></i></span><span class="dist-val">' + fmt(r.v) + " · " + Math.round(100 * r.v / total) + "%</span></button>";
    }).join("") || '<p class="muted">Nothing matches the current filter.</p>'));
    bind(byId("distHost"), "[data-set-dim]", "click", function () {
      var v = this.getAttribute("data-set-val");
      FILTER.district = FILTER.district === v ? "" : v;
      render();
    });
    setHTML("palikaList", ranked(a.byPalika, 6).map(function (r) {
      return "<li><b>" + esc(r.k) + "</b><span>" + fmt(r.v) + " reports</span></li>";
    }).join("") || '<li class="muted">Nothing matches the current filter.</li>');
  }

  function viewQuality(a) {
    var f = a.flags;
    function flag(v, l, n, cls) {
      return '<article class="flag ' + cls + '"><strong>' + esc(v) + "</strong><span>" + esc(l) +
        "</span><small>" + esc(n) + "</small></article>";
    }
    var pending = f.undated + f.offroster + f.overlap;
    setHTML("qualityHost",
      flag(pending ? "Action needed" : "Clear", "Priority signals", pending + " of " + a.rows.length + " selected reports carry a flag", pending ? "warn" : "ok") +
      flag(fmt(f.undated), "Reports with no activity date", "Outside every period; counted in the strip, never folded in", f.undated ? "warn" : "ok") +
      flag(fmt(f.offroster), "Reports from off-roster places", "Kept out of the coverage denominator", f.offroster ? "warn" : "ok") +
      flag(fmt(f.overlap), "Possible same-site, same-day overlap", "Two reports of one activity at one site on one day: a flag to check, not a finding", f.overlap ? "warn" : "ok") +
      flag(fmt(f.corrected), "Records carrying a correction", "Correction status travels with the record; nothing is edited in place silently", f.corrected ? "warn" : "ok"));
  }

  function viewEmpty(a) {
    var el = byId("emptyState");
    if (!el) return;
    var empty = a.rows.length === 0;
    el.hidden = !empty;
    if (empty) {
      el.innerHTML = "<h2>No report matches these filters</h2><p>The selection is empty. That is a true state, not an error, and not a page of zeros dressed up as figures — the freshness line above still says what the source is and how current it is.</p>" +
        '<button type="button" class="primary" data-clear>Clear all filters</button>';
      bind(el, "[data-clear]", "click", clearFilters);
    }
    ["coverageHost", "orgHost", "actHost", "layerHost", "distHost", "palikaList", "qualityHost", "kpiRow"]
      .forEach(function (id) {
        var x = byId(id);
        if (x) x.classList.toggle("hidden-when-empty", empty);
      });
  }

  function viewFocus(a) {
    var grid = document.querySelector(".question-grid");
    if (!grid) return;
    var top = ranked(a.byAct, 1)[0];
    /* Deliberately not "days since the last report": that would read as a gap
       duration, and this fixture cannot support a claim about how long a site
       has been uncovered. The latest activity date is what the data says. */
    var latest = a.dayList.length ? a.dayList[a.dayList.length - 1] : "no dated report";
    var summary = {
      coverage: a.gaps.length + " roster sites · newest report " + latest,
      presence: Object.keys(a.byOrg).length + " organisations · " + Object.keys(a.byDist).length + " districts",
      activity: fmt(a.rows.length) + " reports · " + (top ? top.k : "—") + " leads",
      records: (a.flags.undated + a.flags.offroster + a.flags.overlap) + " data-quality flags"
    };
    grid.querySelectorAll("[data-focus]").forEach(function (b) {
      var s = b.querySelector("small");
      if (s) s.textContent = summary[b.getAttribute("data-focus")] || "—";
    });
    var m = {
      coverage: a.gaps.length + " roster sites have no activity report",
      presence: Object.keys(a.byOrg).length + " organisations report across " + Object.keys(a.byDist).length + " districts",
      activity: (top ? top.k : "—") + " is reported most often in this selection",
      records: (a.flags.undated + a.flags.offroster + a.flags.overlap) + " records carry a data-quality flag"
    };
    Object.keys(m).forEach(function (k) {
      var el = document.querySelector("#" + k + " .focus-summary");
      if (el) el.textContent = m[k];
    });
  }

  /* -------------------------------------------------------- render */
  function render() {
    buildFilters();
    var a = agg();
    renderStrip(a);
    viewKpis(a); viewFreshness(); viewCoverage(a); viewMix(a); viewQuality(a); viewEmpty(a); viewFocus(a);
  }

  /* --------------------------------------------------------- wiring */
  function wire() {
    var t = byId("filterToggle"), p = byId("filterPanel");
    if (t && p) {
      t.addEventListener("click", function () {
        p.hidden = !p.hidden;
        t.setAttribute("aria-expanded", String(!p.hidden));
        if (!p.hidden) { var f = p.querySelector("select"); if (f) f.focus(); }
      });
    }
    var sd = byId("stateDemo");
    if (sd) {
      bind(sd, "button[data-state]", "click", function () {
        window.__PREVIEW_STATE = this.getAttribute("data-state");
        sd.querySelectorAll("button").forEach(function (x) { x.classList.toggle("on", x === this); }, this);
        render();
      });
    }
    bind(document, "[data-preview]", "click", function () {
      var m = byId("previewModal");
      if (!m) return;
      m.hidden = false;
      var c = m.querySelector(".modal-close");
      if (c) c.focus();
    });
    bind(document, ".modal-close", "click", function () { var m = byId("previewModal"); if (m) m.hidden = true; });
    bind(document, "[data-close-hidden]", "click", closeFilters);
    bind(document, "[data-back]", "click", function () {
      document.querySelectorAll(".focus-panel").forEach(function (x) { x.hidden = true; });
      var g = document.querySelector(".question-grid");
      if (g) g.hidden = false;
      scrollTop();
    });
    bind(document, "[data-focus]", "click", function () {
      var id = this.getAttribute("data-focus");
      document.querySelectorAll(".focus-panel").forEach(function (x) { x.hidden = x.id !== id; });
      var g = document.querySelector(".question-grid");
      if (g) g.hidden = true;
      var panel = byId(id);
      if (panel) { var b = panel.querySelector("[data-back]"); if (b) b.focus(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      var m = byId("previewModal");
      if (m && !m.hidden) { m.hidden = true; return; }
      var pp = byId("filterPanel"), tt = byId("filterToggle");
      if (pp && !pp.hidden) { pp.hidden = true; if (tt) { tt.setAttribute("aria-expanded", "false"); tt.focus(); } }
    });
  }

  var REDUCE = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function scrollTop() {
    if (window.scrollTo) window.scrollTo({ top: 0, behavior: REDUCE ? "auto" : "smooth" });
  }
  function closeFilters() {
    var pp = byId("filterPanel"), tt = byId("filterToggle");
    if (pp) pp.hidden = true;
    if (tt) { tt.setAttribute("aria-expanded", "false"); tt.focus(); }
  }

  function boot() {
    readHash();
    wire();
    /* The filter set is the prominent control on a coordination screen, so it
       starts open on a desktop. On a phone it is a bottom sheet and starts
       closed, so the first viewport stays the infographic. */
    var p = byId("filterPanel"), t = byId("filterToggle");
    if (p && window.innerWidth >= 760) { p.hidden = false; if (t) t.setAttribute("aria-expanded", "true"); }
    render();
    window.addEventListener("hashchange", function () {
      /* A shared link (`#flt=…`) re-applies its own filter selection. Section
         anchors used by other concepts are ignored here. */
      if (readHash()) render();
    });
    window.addEventListener("resize", function () {
      var q = byId("filterPanel"), b = byId("filterToggle");
      if (!q || !b) return;
      if (window.innerWidth >= 760 && !q.hidden) b.setAttribute("aria-expanded", "true");
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
