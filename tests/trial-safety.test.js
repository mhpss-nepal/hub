"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const QKEY = "mhpss-np-queue-v1";
const QVERSION = QKEY + "-version";
const QLOCK = QKEY + "-mutation";
const QCOMMIT = QKEY + "-commit-";
const L1_PREFIX = "mhpss-np-l1-";
const STORE_KEY = "mhpss-np-4ws-v1";
const SOURCE_LOCK_SUFFIX = "-mutation";
const SOURCE_COMMIT_SUFFIX = "-commit-";

function makeStorage(initial) {
  const data = new Map(Object.entries(initial || {}));
  const failSet = new Set();
  const failSetPrefix = new Set();
  const failSetPrefixAfter = new Map();
  const prefixSetCounts = new Map();
  const failRemove = new Set();
  const failSetAfter = new Map();
  const setCounts = new Map();
  const beforeGet = new Map();
  const beforeSet = new Map();
  const beforeSetPrefix = new Map();
  return {
    failSet,
    failSetPrefix,
    failSetPrefixAfter,
    failSetAfter,
    failRemove,
    beforeGet,
    beforeSet,
    beforeSetPrefix,
    get length() { return data.size; },
    key(index) { return Array.from(data.keys())[index] ?? null; },
    forceSet(key, value) { data.set(key, String(value)); },
    getItem(key) {
      if (beforeGet.has(key)) beforeGet.get(key)(key);
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      if (beforeSet.has(key)) beforeSet.get(key)(key, value);
      for (const [prefix, action] of beforeSetPrefix) {
        if (key.startsWith(prefix)) action(key, value);
      }
      const count = (setCounts.get(key) || 0) + 1;
      setCounts.set(key, count);
      if (failSet.has(key)) throw new Error("storage write blocked");
      if (failSetAfter.has(key) && count > failSetAfter.get(key)) throw new Error("storage write blocked");
      for (const prefix of failSetPrefix) {
        if (key.startsWith(prefix)) throw new Error("storage write blocked");
      }
      for (const [prefix, allowed] of failSetPrefixAfter) {
        if (!key.startsWith(prefix)) continue;
        const prefixCount = (prefixSetCounts.get(prefix) || 0) + 1;
        prefixSetCounts.set(prefix, prefixCount);
        if (prefixCount > allowed) throw new Error("storage write blocked");
      }
      data.set(key, String(value));
    },
    removeItem(key) {
      if (failRemove.has(key)) throw new Error("storage remove blocked");
      data.delete(key);
    },
  };
}

function fakeElement() {
  return {
    appendChild() {},
    insertBefore() {},
    removeChild() {},
    click() {},
    setAttribute() {},
    className: "",
    disabled: false,
    firstElementChild: null,
    href: "",
    id: "",
    innerHTML: "",
    querySelector() { return fakeElement(); },
    querySelectorAll() { return []; },
    scrollIntoView() {},
    style: {},
    textContent: "",
    type: "",
  };
}

function makeContext(storage, overrides) {
  let randomByte = 0;
  const elements = overrides && overrides.elements;
  const document = {
    body: fakeElement(),
    createElement: fakeElement,
    head: fakeElement(),
    readyState: "complete",
    title: "test",
    addEventListener() {},
    dispatchEvent() {},
    getElementById(id) {
      if (!elements) return null;
      if (!elements[id]) elements[id] = fakeElement();
      return elements[id];
    },
    querySelectorAll() { return []; },
  };
  const window = {
    FB_CONFIG: {},
    addEventListener() {},
    crypto: {
      getRandomValues(bytes) {
        for (let i = 0; i < bytes.length; i += 1) {
          randomByte = (randomByte + 1) & 255;
          bytes[i] = randomByte;
        }
        return bytes;
      },
    },
    document,
    history: { replaceState() {} },
    location: {
      href: "https://example.test/form.html",
      origin: "https://example.test",
      pathname: "/form.html",
      search: "",
    },
    prompt() { return ""; },
  };
  Object.assign(window, overrides || {});
  const context = vm.createContext({
    Blob: class Blob {},
    URL: { createObjectURL() { return "blob:test"; }, revokeObjectURL() {} },
    console: {
      error: console.error,
      info: console.info,
      log: console.log,
      warn() {},
    },
    Date: (overrides && overrides.Date) || Date,
    document,
    localStorage: storage,
    navigator: (overrides && overrides.navigator) || { geolocation: null, onLine: false },
    setTimeout,
    clearTimeout,
    window,
  });
  window.window = window;
  window.localStorage = storage;
  window.navigator = context.navigator;
  window.setTimeout = setTimeout;
  window.clearTimeout = clearTimeout;
  return context;
}

function load(context, relativePath) {
  const filename = path.join(ROOT, relativePath);
  vm.runInContext(fs.readFileSync(filename, "utf8"), context, { filename });
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function durableQueue(storage) {
  const commits = [];
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i);
    if (!key || !key.startsWith(QCOMMIT)) continue;
    commits.push({ key, ...JSON.parse(storage.getItem(key)) });
  }
  commits.sort((a, b) => a.fence - b.fence || a.key.localeCompare(b.key));
  if (commits.length) return commits.at(-1).queue;
  return JSON.parse(storage.getItem(QKEY) || "[]");
}

function durableSource(storage, baseKey) {
  const prefix = baseKey + SOURCE_COMMIT_SUFFIX;
  const commits = [];
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i);
    if (!key || !key.startsWith(prefix)) continue;
    commits.push({ key, ...JSON.parse(storage.getItem(key)) });
  }
  commits.sort((a, b) => a.fence - b.fence || a.key.localeCompare(b.key));
  if (commits.length) return commits.at(-1).records;
  return JSON.parse(storage.getItem(baseKey) || "[]");
}

function loadCoordinationImporter(context) {
  const html = fs.readFileSync(path.join(ROOT, "forms.html"), "utf8");
  const scripts = Array.from(html.matchAll(/<script>([\s\S]*?)<\/script>/g), (match) => match[1]);
  const source = scripts.find((script) => script.includes('var KEY = "mhpss-np-inbox-v1"'));
  assert.ok(source, "coordination importer script not found");
  const boot = source.indexOf("  render();\n  tabFromHash();");
  assert.notEqual(boot, -1, "coordination importer boot marker not found");
  const instrumented = source.slice(0, boot) + [
    "  window.__coordTest = {",
    "    ingest: ingest, mergeLive: mergeLive, viewRows: viewRows,",
    "    exportCSV: function (kind) { return L.toCSV(ofKind(kind), COLS); }",
    "  };",
    "})();",
  ].join("\n");
  vm.runInContext(instrumented, context, { filename: path.join(ROOT, "forms.html#coordination-importer") });
  return context.window.__coordTest;
}

function loadActivityCSVParser(context) {
  const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  const scripts = Array.from(html.matchAll(/<script>([\s\S]*?)<\/script>/g), (match) => match[1]);
  const source = scripts.find((script) => script.includes("function parseCSV(text)"));
  assert.ok(source, "activity CSV parser script not found");
  const start = source.indexOf("  function parseCSV(text)");
  const end = source.indexOf("  /* ---------- synthetic demonstration data", start);
  assert.notEqual(end, -1, "activity CSV parser end marker not found");
  vm.runInContext(source.slice(start, end) + "\nwindow.__parseActivityCSV = parseCSV;", context, {
    filename: path.join(ROOT, "index.html#activity-csv-parser"),
  });
  return context.window.__parseActivityCSV;
}

function activityRecord() {
  return {
    org: "ORG",
    site: "SITE",
    palika: "NP0000001",
    dateAD: "2026-09-19",
    activity: "1.1",
    modality: "FAC",
  };
}

function interleaveAtMutationLock(storage, action) {
  storage.beforeSet.set(QLOCK, () => {
    storage.beforeSet.delete(QLOCK);
    action();
  });
}

function interleaveAtSourceLock(storage, sourceKey, action) {
  const lockKey = sourceKey + SOURCE_LOCK_SUFFIX;
  storage.beforeSet.set(lockKey, () => {
    storage.beforeSet.delete(lockKey);
    action();
  });
}

test("new submissions get unique event ids that remain stable on retry", async () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const first = { kind: "referral", org: "ORG", date_ad: "2026-09-19" };
  const firstResult = await context.window.FB.submit(first);
  const retryResult = await context.window.FB.submit(first);
  const sameContent = { kind: "referral", org: "ORG", date_ad: "2026-09-19" };
  const secondResult = await context.window.FB.submit(sameContent);

  assert.match(first._rid, /^referral_evt_[0-9a-f]{32}$/);
  assert.equal(retryResult.rid, firstResult.rid);
  assert.equal(first._rid, firstResult.rid);
  assert.notEqual(secondResult.rid, firstResult.rid);
  assert.equal(plain(context.window.FB.queue()).length, 2);
});

test("a supplied legacy _rid is preserved exactly", async () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const result = await context.window.FB.submit({
    _rid: "legacy_activity_00ABC",
    kind: "activity",
    org: "ORG",
  });

  assert.equal(result.rid, "legacy_activity_00ABC");
  assert.equal(context.window.FB.queue()[0]._rid, "legacy_activity_00ABC");
});

test("L1 persists the event id in its local record before queueing", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  const result = context.window.L1.save("referral", { kind: "referral", org: "ORG" });
  const local = durableSource(storage, L1_PREFIX + "referral-v1");
  const queued = context.window.FB.queue();

  assert.equal(result.persisted, true);
  assert.match(local[0]._rid, /^referral_evt_[0-9a-f]{32}$/);
  assert.equal(local[0]._rid, queued[0]._rid);
});

test("STORE persists the event id in its local activity record before queueing", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/store.js");

  const result = context.window.STORE.save({
    org: "ORG",
    site: "SITE",
    palika: "NP0000001",
    dateAD: "2026-09-19",
    activity: "1.1",
    modality: "FAC",
  });
  const local = durableSource(storage, STORE_KEY);
  const queued = context.window.FB.queue();

  assert.equal(result.persisted, true);
  assert.match(local[0]._rid, /^activity_evt_[0-9a-f]{32}$/);
  assert.equal(local[0]._rid, queued[0]._rid);
});

test("L1.save distinguishes durable source storage from failed durable queueing", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage();
  storage.failSetPrefix.add(QCOMMIT);
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  const result = context.window.L1.save("referral", { kind: "referral", org: "ORG" });

  assert.equal(result.sourcePersisted, true);
  assert.equal(result.queuePersisted, false);
  assert.equal(result.acknowledged, false);
  assert.equal(result.deliveryState, "not-queued");
  assert.equal(result.recoveryRequired, true);
  assert.equal(durableSource(storage, sourceKey).length, 1);
  assert.match(context.window.L1.toCSV(context.window.L1.all("referral"), ["org"]), /ORG/);
});

test("STORE.save distinguishes durable source storage from failed durable queueing", () => {
  const storage = makeStorage();
  storage.failSetPrefix.add(QCOMMIT);
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/store.js");

  const result = context.window.STORE.save(activityRecord());

  assert.equal(result.sourcePersisted, true);
  assert.equal(result.queuePersisted, false);
  assert.equal(result.acknowledged, false);
  assert.equal(result.deliveryState, "not-queued");
  assert.equal(result.recoveryRequired, true);
  assert.equal(durableSource(storage, STORE_KEY).length, 1);
  assert.match(context.window.STORE.toCSV(context.window.STORE.all()), /ORG/);
});

test("offline saves report durable queueing without claiming acknowledgement", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  const result = context.window.L1.save("referral", { kind: "referral", org: "ORG" });

  assert.equal(result.sourcePersisted, true);
  assert.equal(result.queuePersisted, true);
  assert.equal(result.acknowledged, false);
  assert.equal(result.deliveryState, "queued");
  assert.equal(result.recoveryRequired, false);
});

test("L1 concurrent saves cannot both claim source persistence", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage();
  const first = makeContext(storage, {
    FB: {
      ensureEventId(record) { record._rid = "first"; return record._rid; },
      submit() { throw new Error("conflicted source must not queue"); },
      reportPersistenceFailure() {},
    },
  });
  const second = makeContext(storage, {
    FB: {
      ensureEventId(record) { record._rid = "second"; return record._rid; },
      submit() { return { result: { queuePersisted: true, deliveryState: "queued" } }; },
      reportPersistenceFailure() {},
    },
  });
  load(first, "assets/l1.js");
  load(second, "assets/l1.js");
  let concurrent;
  interleaveAtSourceLock(storage, sourceKey, () => {
    concurrent = second.window.L1.save("referral", { kind: "referral", marker: "second" });
  });

  const stale = first.window.L1.save("referral", { kind: "referral", marker: "first" });

  assert.equal(concurrent.sourcePersisted, true);
  assert.equal(stale.sourcePersisted, false);
  assert.equal(stale.queuePersisted, false);
  assert.match(stale.error, /changed|concurrent|busy/i);
  assert.deepEqual(plain(second.window.L1.all("referral")).map((r) => r.marker), ["second"]);
  assert.match(first.window.L1.toCSV(first.window.L1.all("referral"), ["marker"]), /first/);
});

test("STORE concurrent revisions cannot both claim source persistence", () => {
  const base = activityRecord();
  const seedStorage = makeStorage();
  const seed = makeContext(seedStorage);
  load(seed, "assets/store.js");
  const initial = {
    ...base,
    id: seed.window.STORE.recordId(base),
    _rid: "activity-existing",
    marker: "base",
    createdAt: "2026-09-18T00:00:00.000Z",
    revision: 0,
  };
  const storage = makeStorage({ [STORE_KEY]: JSON.stringify([initial]) });
  const fb = (rid) => ({
    ensureEventId(record) { record._rid = record._rid || rid; return record._rid; },
    submit() { return { result: { queuePersisted: true, deliveryState: "queued" } }; },
    reportPersistenceFailure() {},
  });
  const first = makeContext(storage, { FB: fb("first") });
  const second = makeContext(storage, { FB: fb("second") });
  load(first, "assets/store.js");
  load(second, "assets/store.js");
  let concurrent;
  interleaveAtSourceLock(storage, STORE_KEY, () => {
    concurrent = second.window.STORE.save({ ...base, description: "second revision" });
  });

  const stale = first.window.STORE.save({ ...base, description: "first revision" });

  assert.equal(concurrent.sourcePersisted, true);
  assert.equal(stale.sourcePersisted, false);
  assert.equal(stale.queuePersisted, false);
  assert.equal(second.window.STORE.all()[0].description, "second revision");
  assert.match(first.window.STORE.toCSV(first.window.STORE.all()), /first revision/);
});

test("L1 clear loses a source race instead of deleting a concurrent save", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage({
    [sourceKey]: JSON.stringify([{ _rid: "old", kind: "referral", marker: "old" }]),
  });
  const queueOps = () => ({
    clearQueue() { return { queueCleared: 0, originalQueue: [], queueVersion: 0 }; },
    restoreQueue() { return { restored: true }; },
    ensureEventId(record) { record._rid = "new"; return record._rid; },
    submit() { return { result: { queuePersisted: true, deliveryState: "queued" } }; },
    reportPersistenceFailure() {},
  });
  const clearing = makeContext(storage, { FB: queueOps() });
  const saving = makeContext(storage, { FB: queueOps() });
  load(clearing, "assets/l1.js");
  load(saving, "assets/l1.js");
  interleaveAtSourceLock(storage, sourceKey, () => {
    const saved = saving.window.L1.save("referral", { kind: "referral", marker: "new" });
    assert.equal(saved.sourcePersisted, true);
  });

  assert.throws(
    () => clearing.window.L1.clear("referral"),
    (error) => error && error.code === "SOURCE_CONFLICT",
  );
  assert.deepEqual(plain(saving.window.L1.all("referral")).map((r) => r.marker), ["old", "new"]);
});

test("STORE clear loses a source race instead of deleting a concurrent revision", () => {
  const base = activityRecord();
  const seedStorage = makeStorage();
  const seed = makeContext(seedStorage);
  load(seed, "assets/store.js");
  const initial = {
    ...base,
    id: seed.window.STORE.recordId(base),
    _rid: "activity-existing",
    createdAt: "2026-09-18T00:00:00.000Z",
    revision: 0,
  };
  const storage = makeStorage({ [STORE_KEY]: JSON.stringify([initial]) });
  const queueOps = () => ({
    clearQueue() { return { queueCleared: 0, originalQueue: [], queueVersion: 0 }; },
    restoreQueue() { return { restored: true }; },
    ensureEventId(record) { return record._rid; },
    submit() { return { result: { queuePersisted: true, deliveryState: "queued" } }; },
    reportPersistenceFailure() {},
  });
  const clearing = makeContext(storage, { FB: queueOps() });
  const saving = makeContext(storage, { FB: queueOps() });
  load(clearing, "assets/store.js");
  load(saving, "assets/store.js");
  interleaveAtSourceLock(storage, STORE_KEY, () => {
    const saved = saving.window.STORE.save({ ...base, description: "concurrent revision" });
    assert.equal(saved.sourcePersisted, true);
  });

  assert.throws(
    () => clearing.window.STORE.clearAll(),
    (error) => error && error.code === "SOURCE_CONFLICT",
  );
  assert.equal(saving.window.STORE.all()[0].description, "concurrent revision");
});

test("submit fails closed instead of overwriting a concurrent tab submission", () => {
  const storage = makeStorage();
  const first = makeContext(storage);
  const second = makeContext(storage);
  load(first, "assets/fb.js");
  load(second, "assets/fb.js");
  interleaveAtMutationLock(storage, () => {
    const concurrent = second.window.FB.submit({ _rid: "second", kind: "phq9" });
    assert.equal(concurrent.queuePersisted, true);
  });

  const result = first.window.FB.submit({ _rid: "first", kind: "referral" });

  assert.equal(result.queuePersisted, false);
  assert.equal(result.deliveryState, "not-queued");
  assert.match(result.error, /changed|concurrent|busy/i);
  assert.deepEqual(durableQueue(storage).map((r) => r._rid), ["second"]);
});

test("an expired queue writer cannot corrupt a newer tab's committed payload and metadata", () => {
  let now = 1000;
  class FakeDate extends Date {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  }
  const storage = makeStorage();
  const stale = makeContext(storage, { Date: FakeDate });
  const current = makeContext(storage, { Date: FakeDate });
  load(stale, "assets/fb.js");
  load(current, "assets/fb.js");
  let committed;
  storage.beforeSetPrefix.set(QCOMMIT, () => {
    storage.beforeSetPrefix.delete(QCOMMIT);
    now = 7001;
    committed = current.window.FB.submit({ _rid: "current", kind: "phq9", marker: "new owner" });
    assert.equal(committed.queuePersisted, true);
  });

  const staleResult = stale.window.FB.submit({ _rid: "stale", kind: "referral", marker: "expired owner" });
  const reader = makeContext(storage, { Date: FakeDate });
  load(reader, "assets/fb.js");

  assert.equal(staleResult.queuePersisted, false);
  assert.match(staleResult.error, /newer|changed|token|concurrent|busy/i);
  assert.deepEqual(plain(reader.window.FB.queue()).map((r) => r._rid), ["current"]);
  assert.equal(reader.window.FB.status().persistenceError, "");
});

test("clear fails closed instead of overwriting a concurrent queue update", () => {
  const storage = makeStorage({
    [QKEY]: JSON.stringify([{ _rid: "old", kind: "referral" }]),
  });
  const first = makeContext(storage);
  const second = makeContext(storage);
  load(first, "assets/fb.js");
  load(second, "assets/fb.js");
  interleaveAtMutationLock(storage, () => {
    second.window.FB.submit({ _rid: "second", kind: "phq9" });
  });

  assert.throws(
    () => first.window.FB.clearQueue({ kinds: ["referral"] }),
    (error) => error && error.code === "QUEUE_CONFLICT",
  );
  assert.deepEqual(durableQueue(storage).map((r) => r._rid), ["old", "second"]);
});

test("acknowledged drop fails closed instead of overwriting a concurrent queue update", () => {
  const storage = makeStorage({
    [QKEY]: JSON.stringify([{ _rid: "acked", kind: "referral" }]),
  });
  const first = makeContext(storage);
  const second = makeContext(storage);
  load(first, "assets/fb.js");
  load(second, "assets/fb.js");
  interleaveAtMutationLock(storage, () => {
    second.window.FB.submit({ _rid: "second", kind: "phq9" });
  });

  assert.throws(
    () => first.window.FB.dropAcknowledged({ _rid: "acked", kind: "referral" }),
    (error) => error && error.code === "QUEUE_CONFLICT",
  );
  assert.deepEqual(durableQueue(storage).map((r) => r._rid), ["acked", "second"]);
});

test("rollback fails closed instead of overwriting a post-clear queue update", () => {
  const storage = makeStorage({
    [QKEY]: JSON.stringify([{ _rid: "old", kind: "referral" }]),
  });
  const first = makeContext(storage);
  const second = makeContext(storage);
  load(first, "assets/fb.js");
  load(second, "assets/fb.js");
  const cleared = first.window.FB.clearQueue({ kinds: ["referral"] });
  interleaveAtMutationLock(storage, () => {
    second.window.FB.submit({ _rid: "second", kind: "phq9" });
  });

  assert.throws(
    () => first.window.FB.restoreQueue(cleared),
    (error) => error && error.code === "QUEUE_CONFLICT",
  );
  assert.deepEqual(durableQueue(storage).map((r) => r._rid), ["second"]);
});

test("rollback refuses a versionless legacy snapshot rather than overwriting newer data", () => {
  const storage = makeStorage({
    [QKEY]: JSON.stringify([{ _rid: "newer", kind: "phq9" }]),
  });
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  assert.throws(
    () => context.window.FB.restoreQueue([{ _rid: "older", kind: "referral" }]),
    (error) => error && error.code === "QUEUE_CONFLICT",
  );
  assert.deepEqual(durableQueue(storage).map((r) => r._rid), ["newer"]);
});

test("flush keeps an acknowledged row when a concurrent update races its drop", async () => {
  const storage = makeStorage({
    [QKEY]: JSON.stringify([{ _rid: "acked", kind: "referral" }]),
  });
  const first = makeContext(storage, { navigator: { geolocation: null, onLine: true } });
  const second = makeContext(storage);
  load(first, "assets/fb.js");
  load(second, "assets/fb.js");
  interleaveAtMutationLock(storage, () => {
    second.window.FB.submit({ _rid: "second", kind: "phq9" });
  });

  const result = await first.window.FB.flush(() => Promise.resolve());

  assert.equal(result.sent, 1);
  assert.equal(result.conflicts, 1);
  assert.deepEqual(durableQueue(storage).map((r) => r._rid), ["acked", "second"]);
});

test("flush never drops newer content that reused the acknowledged _rid", async () => {
  const oldBody = { _rid: "same", kind: "activity", revision: 1, marker: "sent" };
  const newerBody = { _rid: "same", kind: "activity", revision: 2, marker: "newer" };
  const storage = makeStorage({ [QKEY]: JSON.stringify([oldBody]) });
  const flushing = makeContext(storage, { navigator: { geolocation: null, onLine: true } });
  const revising = makeContext(storage);
  load(flushing, "assets/fb.js");
  load(revising, "assets/fb.js");

  const result = await flushing.window.FB.flush((sent) => {
    assert.deepEqual(plain(sent), oldBody);
    const revised = revising.window.FB.submit(newerBody);
    assert.equal(revised.queuePersisted, true);
    return Promise.resolve();
  });

  assert.equal(result.sent, 1);
  assert.equal(result.conflicts, 1);
  assert.equal(result.left, 1);
  assert.deepEqual(plain(flushing.window.FB.queue()), [
    { ...newerBody, _device_ts: flushing.window.FB.queue()[0]._device_ts },
  ]);
});

test("L1.clear maps the contact storage kind to service_contact queue entries only", () => {
  const storage = makeStorage({
    [L1_PREFIX + "contact-v1"]: JSON.stringify([{ _rid: "shared-id" }]),
    [QKEY]: JSON.stringify([
      { _rid: "contact-1", kind: "service_contact" },
      { _rid: "contact-legacy", kind: "contact" },
      { _rid: "shared-id", kind: "referral" },
      { _rid: "self-1", kind: "self_report" },
    ]),
  });
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  const result = context.window.L1.clear("contact");

  assert.equal(result.cleared, true);
  assert.equal(result.queueCleared, 2);
  assert.deepEqual(durableSource(storage, L1_PREFIX + "contact-v1"), []);
  assert.deepEqual(plain(context.window.FB.queue()), [
    { _rid: "shared-id", kind: "referral" },
    { _rid: "self-1", kind: "self_report" },
  ]);
});

test("L1.clear maps selfreport to self_report without clearing other forms", () => {
  const storage = makeStorage({
    [L1_PREFIX + "selfreport-v1"]: JSON.stringify([{ _rid: "self-1" }]),
    [QKEY]: JSON.stringify([
      { _rid: "self-1", kind: "self_report" },
      { _rid: "contact-1", kind: "service_contact" },
    ]),
  });
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  const result = context.window.L1.clear("selfreport");

  assert.equal(result.queueCleared, 1);
  assert.deepEqual(durableSource(storage, L1_PREFIX + "selfreport-v1"), []);
  assert.deepEqual(plain(context.window.FB.queue()), [
    { _rid: "contact-1", kind: "service_contact" },
  ]);
});

for (const kind of ["referral", "phq9"]) {
  test(`L1.clear uses the real ${kind} storage and queue kind`, () => {
    const storage = makeStorage({
      [L1_PREFIX + kind + "-v1"]: JSON.stringify([{ _rid: `${kind}-1` }]),
      [QKEY]: JSON.stringify([
        { _rid: `${kind}-1`, kind },
        { _rid: "other-1", kind: kind === "referral" ? "phq9" : "referral" },
      ]),
    });
    const context = makeContext(storage);
    load(context, "assets/fb.js");
    load(context, "assets/l1.js");

    const result = context.window.L1.clear(kind);

    assert.equal(result.queueCleared, 1);
    assert.deepEqual(durableSource(storage, L1_PREFIX + kind + "-v1"), []);
    assert.equal(context.window.FB.queue().length, 1);
  });
}

test("STORE.clearAll removes activity submissions without clearing other queued forms", () => {
  const storage = makeStorage({
    [STORE_KEY]: JSON.stringify([{ _rid: "activity-1", id: "R1" }]),
    [QKEY]: JSON.stringify([
      { _rid: "activity-1", kind: "activity" },
      { _rid: "activity-1", kind: "referral" },
    ]),
  });
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/store.js");

  const result = context.window.STORE.clearAll();

  assert.equal(result.cleared, true);
  assert.equal(result.queueCleared, 1);
  assert.deepEqual(durableSource(storage, STORE_KEY), []);
  assert.deepEqual(plain(context.window.FB.queue()), [
    { _rid: "activity-1", kind: "referral" },
  ]);
});

test("STORE.clearAll restores the exact queue when source removal fails", () => {
  const originalQueue = [
    { _rid: "activity-1", kind: "activity", marker: "restore me" },
    { _rid: "referral-1", kind: "referral", marker: "leave me" },
  ];
  const storage = makeStorage({
    [STORE_KEY]: JSON.stringify([{ _rid: "activity-1", id: "R1" }]),
    [QKEY]: JSON.stringify(originalQueue),
  });
  storage.failSetPrefix.add(STORE_KEY + SOURCE_COMMIT_SUFFIX);
  let warning = "";
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  context.window.FB.reportPersistenceFailure = (message) => { warning = message; };
  load(context, "assets/store.js");

  assert.throws(
    () => context.window.STORE.clearAll(),
    (error) => error && error.code === "PERSISTENCE_FAILED",
  );
  assert.equal(storage.getItem(QKEY), JSON.stringify(originalQueue));
  assert.deepEqual(plain(context.window.FB.queue()), originalQueue);
  assert.match(warning, /queue (?:was )?restored/i);
  assert.notEqual(storage.getItem(STORE_KEY), null);
});

test("clear fails closed when the related queue cannot be persisted", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage({
    [sourceKey]: JSON.stringify([{ _rid: "referral-1" }]),
    [QKEY]: JSON.stringify([{ _rid: "referral-1", kind: "referral" }]),
  });
  storage.failSetPrefix.add(QCOMMIT);
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  assert.throws(
    () => context.window.L1.clear("referral"),
    (error) => error && error.code === "PERSISTENCE_FAILED",
  );
  assert.notEqual(storage.getItem(sourceKey), null);
  assert.equal(JSON.parse(storage.getItem(QKEY))[0]._rid, "referral-1");
});

test("L1.clear restores the exact queue when source removal fails", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const originalQueue = [
    { _rid: "referral-1", kind: "referral", marker: "restore me" },
    { _rid: "contact-1", kind: "service_contact", marker: "leave me" },
  ];
  const storage = makeStorage({
    [sourceKey]: JSON.stringify([{ _rid: "referral-1" }]),
    [QKEY]: JSON.stringify(originalQueue),
  });
  storage.failSetPrefix.add(sourceKey + SOURCE_COMMIT_SUFFIX);
  let warning = "";
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  context.window.FB.reportPersistenceFailure = (message) => { warning = message; };
  load(context, "assets/l1.js");

  assert.throws(
    () => context.window.L1.clear("referral"),
    (error) => error && error.code === "PERSISTENCE_FAILED",
  );
  assert.equal(storage.getItem(QKEY), JSON.stringify(originalQueue));
  assert.deepEqual(plain(context.window.FB.queue()), originalQueue);
  assert.match(warning, /queue (?:was )?restored/i);
  assert.notEqual(storage.getItem(sourceKey), null);
});

test("L1.clear reports a high-severity warning when queue rollback fails", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const originalQueue = [{ _rid: "referral-1", kind: "referral" }];
  const storage = makeStorage({
    [sourceKey]: JSON.stringify([{ _rid: "referral-1" }]),
    [QKEY]: JSON.stringify(originalQueue),
  });
  storage.failSetPrefix.add(sourceKey + SOURCE_COMMIT_SUFFIX);
  storage.failSetPrefixAfter.set(QCOMMIT, 1);
  let warning = "";
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  context.window.FB.reportPersistenceFailure = (message) => { warning = message; };
  load(context, "assets/l1.js");

  assert.throws(
    () => context.window.L1.clear("referral"),
    (error) => error && error.code === "PERSISTENCE_FAILED" &&
      error.severity === "high" && error.rollbackFailed === true,
  );
  assert.match(warning, /HIGH-SEVERITY WARNING/);
  assert.match(warning, /could not be restored/i);
  assert.doesNotMatch(warning, /success|successfully cleared/i);
  assert.deepEqual(durableQueue(storage), []);
  assert.deepEqual(plain(context.window.FB.queue()), originalQueue);
  assert.notEqual(storage.getItem(sourceKey), null);
});

test("STORE.clearAll reports a high-severity warning when queue rollback fails", () => {
  const originalQueue = [{ _rid: "activity-1", kind: "activity" }];
  const storage = makeStorage({
    [STORE_KEY]: JSON.stringify([{ _rid: "activity-1", id: "R1" }]),
    [QKEY]: JSON.stringify(originalQueue),
  });
  storage.failSetPrefix.add(STORE_KEY + SOURCE_COMMIT_SUFFIX);
  storage.failSetPrefixAfter.set(QCOMMIT, 1);
  let warning = "";
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  context.window.FB.reportPersistenceFailure = (message) => { warning = message; };
  load(context, "assets/store.js");

  assert.throws(
    () => context.window.STORE.clearAll(),
    (error) => error && error.code === "PERSISTENCE_FAILED" &&
      error.severity === "high" && error.rollbackFailed === true,
  );
  assert.match(warning, /HIGH-SEVERITY WARNING/);
  assert.match(warning, /could not be restored/i);
  assert.doesNotMatch(warning, /success|successfully cleared/i);
  assert.deepEqual(durableQueue(storage), []);
  assert.deepEqual(plain(context.window.FB.queue()), originalQueue);
  assert.notEqual(storage.getItem(STORE_KEY), null);
});

test("clear fails closed when the existing queue cannot be read", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage({
    [sourceKey]: JSON.stringify([{ _rid: "referral-1" }]),
    [QKEY]: "not-json",
  });
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/l1.js");

  assert.throws(
    () => context.window.L1.clear("referral"),
    (error) => error && error.code === "PERSISTENCE_FAILED",
  );
  assert.notEqual(storage.getItem(sourceKey), null);
  assert.equal(storage.getItem(QKEY), "not-json");
});

test("a clear failure reports a visible warning before it prevents success messaging", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage({ [sourceKey]: JSON.stringify([{ _rid: "referral-1" }]) });
  let warning = "";
  let successMessageShown = false;
  const context = makeContext(storage, {
    FB: {
      queue() { return []; },
      restoreQueue() {},
      clearQueue() {
        const error = new Error("queue clear failed");
        error.code = "PERSISTENCE_FAILED";
        throw error;
      },
      reportPersistenceFailure(message) { warning = message; },
    },
  });
  load(context, "assets/l1.js");

  assert.throws(() => {
    context.window.L1.clear("referral");
    successMessageShown = true;
  }, (error) => error && error.code === "PERSISTENCE_FAILED");
  assert.match(warning, /clear|queue/i);
  assert.equal(successMessageShown, false);
  assert.notEqual(storage.getItem(sourceKey), null);
});

test("L1.clear alerts when its local record removal fails without a bridge reporter", () => {
  const sourceKey = L1_PREFIX + "referral-v1";
  const storage = makeStorage({ [sourceKey]: JSON.stringify([{ _rid: "referral-1" }]) });
  storage.failSetPrefix.add(sourceKey + SOURCE_COMMIT_SUFFIX);
  let warning = "";
  const context = makeContext(storage, {
    alert(message) { warning = message; },
    FB: {
      queue() { return []; },
      restoreQueue() {},
      clearQueue() { return { queueCleared: 0 }; },
    },
  });
  load(context, "assets/l1.js");

  assert.throws(
    () => context.window.L1.clear("referral"),
    (error) => error && error.code === "PERSISTENCE_FAILED",
  );
  assert.match(warning, /could not clear/i);
  assert.notEqual(storage.getItem(sourceKey), null);
});

test("STORE.clearAll warns visibly when queue verification is unavailable", () => {
  const storage = makeStorage({ [STORE_KEY]: JSON.stringify([activityRecord()]) });
  let warning = "";
  const context = makeContext(storage, { alert(message) { warning = message; } });
  load(context, "assets/store.js");

  assert.throws(
    () => context.window.STORE.clearAll(),
    (error) => error && error.code === "PERSISTENCE_FAILED",
  );
  assert.match(warning, /cannot verify/i);
  assert.notEqual(storage.getItem(STORE_KEY), null);
});

test("FB.submit reports queue persistence failure as not locally safe", async () => {
  const storage = makeStorage();
  storage.failSetPrefix.add(QCOMMIT);
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const result = await context.window.FB.submit({ kind: "referral", org: "ORG" });

  assert.equal(result.persisted, false);
  assert.equal(result.local, false);
  assert.match(result.error, /not safely stored/i);
});

test("FB.submit does not overwrite an unreadable existing queue", async () => {
  const storage = makeStorage({ [QKEY]: "not-json" });
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const result = await context.window.FB.submit({ kind: "referral", org: "ORG" });

  assert.equal(result.persisted, false);
  assert.equal(result.local, false);
  assert.match(result.error, /could not be read/i);
  assert.equal(storage.getItem(QKEY), "not-json");
});

test("status reports an unreadable queue on its first read", () => {
  const storage = makeStorage({ [QKEY]: "not-json" });
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  assert.match(context.window.FB.status().persistenceError, /could not be read/i);
});

test("FB.submit rejects a non-list queue without overwriting it", async () => {
  const storage = makeStorage({ [QKEY]: "{}" });
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const result = await context.window.FB.submit({ kind: "referral", org: "ORG" });

  assert.equal(result.persisted, false);
  assert.match(result.error, /could not be read/i);
  assert.equal(storage.getItem(QKEY), "{}");
});

test("a queue that failed to persist remains visible for this page", async () => {
  const storage = makeStorage();
  storage.failSetPrefix.add(QCOMMIT);
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const result = await context.window.FB.submit({ kind: "referral", org: "ORG" });

  assert.equal(context.window.FB.status().pending, 1);
  assert.equal(context.window.FB.queue()[0]._rid, result.rid);
});

test("L1.save returns persisted false, exposes the newer memory copy, and does not sync", () => {
  const key = L1_PREFIX + "referral-v1";
  const storage = makeStorage({
    [key]: JSON.stringify([{ kind: "referral", marker: "older" }]),
  });
  storage.failSetPrefix.add(key + SOURCE_COMMIT_SUFFIX);
  let submitted = 0;
  let warning = "";
  const context = makeContext(storage, {
    FB: {
      ensureEventId(record) { record._rid = "referral_evt_test"; return record._rid; },
      submit() { submitted += 1; },
      reportPersistenceFailure(message) { warning = message; },
    },
  });
  load(context, "assets/l1.js");

  const result = context.window.L1.save("referral", { kind: "referral", marker: "newer" });

  assert.equal(result.persisted, false);
  assert.equal(result.synced, null);
  assert.equal(submitted, 0);
  assert.match(warning, /only in memory/i);
  assert.deepEqual(plain(context.window.L1.all("referral")).map((r) => r.marker), ["older", "newer"]);
  assert.match(
    context.window.L1.toCSV(context.window.L1.all("referral"), ["marker"]),
    /newer/,
  );
});

test("STORE.save returns persisted false, exposes the newer memory copy, and does not sync", () => {
  const older = { ...activityRecord(), id: "R-OLDER", marker: "older", createdAt: "2026-09-18T00:00:00.000Z" };
  const storage = makeStorage({ [STORE_KEY]: JSON.stringify([older]) });
  storage.failSetPrefix.add(STORE_KEY + SOURCE_COMMIT_SUFFIX);
  let submitted = 0;
  let warning = "";
  const context = makeContext(storage, {
    FB: {
      ensureEventId(record) { record._rid = "activity_evt_test"; return record._rid; },
      submit() { submitted += 1; },
      reportPersistenceFailure(message) { warning = message; },
    },
  });
  load(context, "assets/store.js");

  const result = context.window.STORE.save({ ...activityRecord(), site: "NEW-SITE", marker: "newer" });

  assert.equal(result.persisted, false);
  assert.equal(submitted, 0);
  assert.match(warning, /only in memory/i);
  assert.deepEqual(plain(context.window.STORE.all()).map((r) => r.marker).sort(), ["newer", "older"]);
  assert.match(context.window.STORE.toCSV(context.window.STORE.all()), /NEW-SITE/);
});

test("a legacy activity revision reuses its matching queued remote id", () => {
  const seedStorage = makeStorage();
  const seedContext = makeContext(seedStorage);
  load(seedContext, "assets/store.js");
  const base = activityRecord();
  const id = seedContext.window.STORE.recordId(base);
  const legacy = { ...base, id, createdAt: "2026-09-18T00:00:00.000Z", revision: 0 };
  const storage = makeStorage({
    [STORE_KEY]: JSON.stringify([legacy]),
    [QKEY]: JSON.stringify([{
      ...legacy,
      kind: "activity",
      _rid: "activity_legacy_queue_id",
    }]),
  });
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/store.js");

  const result = context.window.STORE.save({ ...base, description: "corrected" });

  assert.equal(result.record._rid, "activity_legacy_queue_id");
  assert.equal(context.window.FB.queue().length, 1);
  assert.equal(context.window.FB.queue()[0]._rid, "activity_legacy_queue_id");
});

test("a legacy activity revision without a queue keeps its old deterministic remote id", () => {
  const seedStorage = makeStorage();
  const seedContext = makeContext(seedStorage);
  load(seedContext, "assets/store.js");
  const base = activityRecord();
  const id = seedContext.window.STORE.recordId(base);
  const legacy = { ...base, id, createdAt: "2026-09-18T00:00:00.000Z", revision: 0 };
  const storage = makeStorage({ [STORE_KEY]: JSON.stringify([legacy]) });
  const context = makeContext(storage);
  load(context, "assets/fb.js");
  load(context, "assets/store.js");

  const result = context.window.STORE.save({ ...base, description: "corrected" });
  const oldRemoteId = context.window.FB.rid(context.window.STORE.registerBody(result.record));

  assert.equal(result.record._rid, oldRemoteId);
  assert.doesNotMatch(result.record._rid, /_evt_/);
  assert.equal(context.window.FB.queue()[0]._rid, oldRemoteId);
});

test("coordination imports preserve a supplied event id", () => {
  const storage = makeStorage();
  const context = makeContext(storage, {
    CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
    L1: {
      today() { return "2026-09-19"; },
      toCSV(rows, columns) {
        return columns.join(",") + "\r\n" + rows.map((row) =>
          columns.map((column) => row[column] === undefined ? "" : row[column]).join(",")
        ).join("\r\n") + "\r\n";
      },
    },
  });
  const importer = loadCoordinationImporter(context);

  const result = importer.ingest("referrals.json", JSON.stringify([
    { _rid: "referral_evt_from_export", kind: "referral", org: "ORG" },
  ]));

  assert.equal(result.added, 1);
  assert.equal(importer.viewRows()[0]._rid, "referral_evt_from_export");
});

test("activity CSV export includes the immutable event id", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/store.js");
  const record = { ...activityRecord(), id: "R1", _rid: "activity_evt_export" };

  const csv = context.window.STORE.toCSV([record]).replace(/^﻿/, "");
  const [header, row] = csv.trim().split("\n");
  const columns = header.split(",");
  const cells = row.split(",");

  assert.equal(columns.includes("_rid"), true);
  assert.equal(cells[columns.indexOf("_rid")], "activity_evt_export");
});

test("activity CSV export/import/re-export preserves the immutable event id", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/store.js");
  const parseCSV = loadActivityCSVParser(context);
  const record = { ...activityRecord(), id: "R1", _rid: "activity_evt_round_trip" };

  const firstExport = context.window.STORE.toCSV([record]);
  const imported = parseCSV(firstExport);
  const secondExport = context.window.STORE.toCSV(imported);
  const reparsed = parseCSV(secondExport);

  assert.equal(imported[0]._rid, "activity_evt_round_trip");
  assert.equal(reparsed[0]._rid, "activity_evt_round_trip");
});

test("activity parser remains compatible with old CSVs without event ids", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  const parseCSV = loadActivityCSVParser(context);

  const imported = parseCSV("id,org,dateAD,activity,modality\r\nR1,ORG,2026-09-19,1.1,FAC\r\n");

  assert.equal(imported.length, 1);
  assert.equal(imported[0].id, "R1");
  assert.equal(Object.hasOwn(imported[0], "_rid"), false);
});

test("coordination CSV import and re-export preserve the exact event id", () => {
  const makeImporter = () => {
    const storage = makeStorage();
    const context = makeContext(storage, {
      CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
      L1: {
        today() { return "2026-09-19"; },
        toCSV(rows, columns) {
          return columns.join(",") + "\r\n" + rows.map((row) =>
            columns.map((column) => row[column] === undefined ? "" : row[column]).join(",")
          ).join("\r\n") + "\r\n";
        },
      },
    });
    return loadCoordinationImporter(context);
  };
  const first = makeImporter();
  first.ingest("referrals.csv", "_rid,kind,org,date_ad\r\nreferral_evt_round_trip,referral,ORG,2026-09-19\r\n");

  const exported = first.exportCSV("referral");
  assert.match(exported.split(/\r?\n/, 1)[0], /(?:^|,)_rid(?:,|$)/);
  assert.match(exported, /referral_evt_round_trip/);

  const second = makeImporter();
  const result = second.ingest("referrals-reexport.csv", exported);
  assert.equal(result.added, 1);
  assert.equal(second.viewRows()[0]._rid, "referral_evt_round_trip");
});

test("coordination still imports and re-exports old CSVs without event ids", () => {
  const storage = makeStorage();
  const context = makeContext(storage, {
    CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
    L1: {
      today() { return "2026-09-19"; },
      toCSV(rows, columns) {
        return columns.join(",") + "\r\n" + rows.map((row) =>
          columns.map((column) => row[column] === undefined ? "" : row[column]).join(",")
        ).join("\r\n") + "\r\n";
      },
    },
  });
  load(context, "assets/fb.js");
  const importer = loadCoordinationImporter(context);

  const result = importer.ingest(
    "legacy-referrals.csv",
    "kind,org,date_ad,reason\r\nreferral,ORG,2026-09-19,MH\r\n",
  );

  assert.equal(result.added, 1);
  assert.equal(importer.viewRows()[0]._rid, context.window.FB.rid({
    kind: "referral", org: "ORG", date_ad: "2026-09-19", reason: "MH",
  }));
  assert.match(importer.exportCSV("referral"), new RegExp(importer.viewRows()[0]._rid));
});

test("coordination imports dedupe supplied ids against live Firestore document ids", () => {
  const storage = makeStorage();
  const context = makeContext(storage, {
    elements: {},
    CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
    L1: { today() { return "2026-09-19"; } },
  });
  const importer = loadCoordinationImporter(context);
  importer.mergeLive([{ _id: "firestore-doc-1", kind: "referral", org: "ORG" }]);

  const result = importer.ingest("referrals.json", JSON.stringify([
    { _rid: "firestore-doc-1", kind: "referral", org: "ORG" },
  ]));

  assert.equal(result.added, 0);
  assert.equal(result.dupe, 1);
  assert.equal(importer.viewRows().length, 1);
  assert.equal(importer.viewRows()[0]._rid, "firestore-doc-1");
});

test("coordination imports still dedupe legacy records without event ids", () => {
  const storage = makeStorage();
  const context = makeContext(storage, {
    CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
    L1: { today() { return "2026-09-19"; } },
  });
  load(context, "assets/fb.js");
  const importer = loadCoordinationImporter(context);
  const legacy = JSON.stringify([{ kind: "phq9", org: "ORG", date_ad: "2026-09-19", total: 8 }]);

  const first = importer.ingest("legacy.csv.json", legacy);
  const second = importer.ingest("legacy-again.json", legacy);

  assert.equal(first.added, 1);
  assert.equal(second.dupe, 1);
  assert.equal(importer.viewRows().length, 1);
});

test("BOM-prefixed historical activity CSV matches its live FB.rid in every activity import path", () => {
  const historical = {
    kind: "activity",
    id: "R0000001",
    org: "ORG",
    dateAD: "2026-09-18",
    site: "SITE",
    palika: "NP0000001",
    activity: "1.1",
    modality: "FAC",
  };
  const storage = makeStorage();
  const context = makeContext(storage, {
    elements: {},
    CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
    L1: { today() { return "2026-09-19"; } },
  });
  load(context, "assets/fb.js");
  const liveId = context.window.FB.rid(historical);
  const columns = ["id", "org", "dateAD", "site", "palika", "activity", "modality"];
  const csv = "\uFEFF" + columns.join(",") + "\r\n" +
    columns.map((column) => historical[column]).join(",") + "\r\n";

  const activityRows = loadActivityCSVParser(context)(csv);
  assert.equal(activityRows[0].id, historical.id);
  assert.equal(Object.hasOwn(activityRows[0], "\uFEFFid"), false);

  const importer = loadCoordinationImporter(context);
  importer.mergeLive([{ ...historical, _id: liveId }]);
  const result = importer.ingest("historical-activity.csv", csv);
  assert.equal(result.added, 0);
  assert.equal(result.dupe, 1);
  assert.equal(importer.viewRows().length, 1);
  assert.equal(importer.viewRows()[0]._rid, liveId);
});

test("legacy CSV ids exactly match historical Firestore FB.rid for every supported kind", () => {
  const records = [
    { kind: "service_contact", org: "ORG", date_ad: "2026-09-18", site: "SITE", contact_code: "NP-AAAAA-BBBBB", service: "PFA", minutes: "30" },
    { kind: "activity", id: "R0000001", org: "ORG", dateAD: "2026-09-18", site: "SITE", palika: "NP0000001", activity: "1.1", modality: "FAC" },
    { kind: "referral", org: "ORG", date_ad: "2026-09-18", site: "SITE", contact_code: "NP-AAAAA-BBBBB", reason: "MH", direction: "OUT" },
    { kind: "phq9", org: "ORG", date_ad: "2026-09-18", contact_code: "NP-AAAAA-BBBBB", instrument: "PHQ-9", administration: "BASE", q1: "2", total: "11" },
    { kind: "self_report", site: "SITE", coping: "SOME", total: "" },
  ];

  for (const record of records) {
    const storage = makeStorage();
    const context = makeContext(storage, {
      elements: {},
      CODES: { orgByCode: {}, siteByCode: {}, palikaName() { return ""; } },
      L1: { today() { return "2026-09-19"; } },
    });
    load(context, "assets/fb.js");
    const importer = loadCoordinationImporter(context);
    const liveId = context.window.FB.rid(record);
    importer.mergeLive([{ ...record, _id: liveId }]);
    const columns = Object.keys(record);
    const csv = columns.join(",") + "\r\n" + columns.map((column) => record[column]).join(",") + "\r\n";

    const result = importer.ingest(`legacy-${record.kind}.csv`, csv);

    assert.equal(result.added, 0, record.kind);
    assert.equal(result.dupe, 1, record.kind);
    assert.equal(importer.viewRows().length, 1, record.kind);
    assert.equal(importer.viewRows()[0]._rid, liveId, record.kind);
  }
});

test("Firestore submission bodies strip every focal and referrer contact alias", () => {
  const storage = makeStorage();
  const context = makeContext(storage);
  load(context, "assets/fb.js");

  const body = context.window.FB.bodyForFirestore({
    kind: "referral",
    org: "ORG",
    focalName: "Name",
    focalPhone: "9800000000",
    focalEmail: "name@example.test",
    focal_name: "Name",
    focal_phone: "9800000000",
    focal_email: "name@example.test",
    referrerPhone: "9811111111",
    referrer_phone: "9811111111",
  });

  assert.equal(body.org, "ORG");
  for (const key of [
    "focalName", "focalPhone", "focalEmail",
    "focal_name", "focal_phone", "focal_email",
    "referrerPhone", "referrer_phone",
  ]) {
    assert.equal(Object.hasOwn(body, key), false, key + " entered the Firestore body");
  }
});
