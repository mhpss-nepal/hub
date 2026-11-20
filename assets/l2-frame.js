/* =====================================================================
   MHPSS Nepal — one frame for every Layer 2 page (QC 20 Nov 2026)
   Wraps a stand-alone Layer 2 page (Referral Directory, Grief Mapping,
   Team and checking) in the same frame as the main dashboard, so the top
   bar, back bar and sidebar stay in the same place when moving between
   sections. Presentation only: no data, no storage. The menu mirrors
   assets/instrument-homes.js; links that belong to the main dashboard go
   back to index.html. Load right after the page content, before i18n.js.
   ===================================================================== */
(function () {
  "use strict";
  var page = (document.body.getAttribute("data-l2-page") || "").trim();
  var content = document.querySelector("main#dashboard-main") || document.querySelector(".tw");
  if (!page || !content) return;
  var ITEMS = [
    ["5ws", "5Ws Reports", "Activities by place and type", "index.html?view=dashboard&house=5ws"],
    ["directory", "Referral Directory", "Services on a map · gaps", "directory.html"],
    ["grief", "Grief Mapping", "By palika · totals only", "grief.html"],
    ["team", "Team and checking", "Who entered · records to check", "team.html"],
    ["training", "Training & orientation", "Sessions and participants", "index.html?view=dashboard&house=training"],
    ["providers", "Provider register", "Registrations for review", "index.html?view=dashboard&house=providers"],
    ["servicepoints", "Service points", "Registrations for review", "index.html?view=dashboard&house=servicepoints"],
    ["baseline", "Historical Baseline", "Available", "index.html?view=dashboard&house=baseline", true],
    ["sample", "Sample Data", "Available", "index.html?view=dashboard&house=sample", true]
  ];
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  var title = (content.querySelector("h1") || {}).textContent || document.title;

  /* the old per-page navigation goes; the frame replaces it */
  ["nav[aria-label='Home navigation']", ".l2-menu", ".l2-backdrop", "aside.rail"].forEach(function (s) {
    Array.prototype.forEach.call(document.querySelectorAll(s), function (n) { n.remove(); });
  });
  document.body.classList.remove("l2-shell");
  document.body.classList.add("l2-frame");

  var lang = el("div", "l2f-lang"); lang.setAttribute("data-i18n-toggle", "");
  var bar = el("div", "l2f-bar");
  var back = el("a", "l2f-back", "← Back to Home"); back.href = "./";
  bar.append(back, el("p", null, "Coordination dashboard"));
  var layout = el("div", "l2f-layout");
  var side = el("aside", "l2f-side"); side.id = "l2f-sidebar"; side.setAttribute("aria-label", "Dashboard sections");
  var scope = el("p", "l2f-scope", "");
  var nav = el("nav"); nav.setAttribute("aria-label", "Dashboard sections");
  var admins = [];
  ITEMS.forEach(function (it) {
    var a = el("a"); a.href = it[3]; a.dataset.house = it[0];
    a.append(el("span", null, it[1]), el("small", null, it[2]));
    if (it[0] === page) { a.className = "active"; a.setAttribute("aria-current", "page"); }
    if (it[4]) { a.hidden = true; admins.push(a); }
    nav.append(a);
  });
  var adm = el("div", "l2f-admin"); adm.hidden = true;
  var admA = el("a"); admA.href = "index.html?view=dashboard&house=5ws&open=admin";
  admA.append(el("span", null, "Administration"), el("small", null, "Server-authorized records only"));
  var admNav = el("nav"); admNav.append(admA); adm.append(admNav);
  side.append(el("h2", null, "MHPSS Nepal"), scope, el("div", "l2f-group", "Dashboard"), nav, adm);
  var main = el("div", "l2f-main");
  var ctx = el("div", "l2f-context");
  var left = el("div"); left.style.display = "flex"; left.style.gap = "8px"; left.style.flexWrap = "wrap";
  var refresh = el("button", null, "Refresh access"); refresh.type = "button"; refresh.onclick = function () { location.reload(); };
  var menu = el("button", "l2f-menu", "☰ Dashboard sections"); menu.type = "button";
  menu.setAttribute("aria-controls", "l2f-sidebar"); menu.setAttribute("aria-expanded", "false");
  menu.onclick = function () { var o = side.classList.toggle("open"); menu.setAttribute("aria-expanded", String(o)); };
  left.append(refresh, menu);
  var ctxScope = el("span", null, "");
  ctx.append(left, ctxScope);
  var holder = el("div", "l2f-content");
  content.parentNode.insertBefore(lang, content);
  content.parentNode.insertBefore(bar, content);
  content.parentNode.insertBefore(layout, content);
  holder.append(content); main.append(ctx, holder); layout.append(side, main);
  /* the page heading moves into the content so it sits where the main dashboard puts its heading */
  var head = document.querySelector("body > header.top");
  if (head) holder.insertBefore(head, content);

  /* who is signed in: the same line the main dashboard shows under the name */
  function who() {
    var A = window.AccessAPI;
    if (!A || !A.me || !(A.user && A.user())) return false;
    A.me().then(function (me) {
      if (!me || !me.role) return;
      var t = me.role + " · " + (me.org || "all organisations");
      scope.textContent = t; ctxScope.textContent = t;
      var isAdmin = me.role === "admin";
      admins.forEach(function (a) { a.hidden = !isAdmin; });
      adm.hidden = !isAdmin;
    }).catch(function () { /* offline: the menu still works */ });
    return true;
  }
  var tries = 0, timer = setInterval(function () { if (who() || ++tries > 40) clearInterval(timer); }, 250);
  if (window.BaselineAuth && BaselineAuth.onChange) try { BaselineAuth.onChange(function () { who(); }); } catch (e) { /* optional */ }
})();
