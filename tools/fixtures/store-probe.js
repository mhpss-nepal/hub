/* Loads assets/store.js the way a page does -- as a plain script that
   assigns window.STORE -- and prints, for the records in a JSON file:

     columns   the export allow-list, as the file itself declares it
     head      the CSV header row toCSV() builds
     rows      the CSV data rows toCSV() builds
     bodies    registerBody() for each record (what is sent to the register)

   This exists so the export contract can be checked with no browser:
   `toCSV()` builds both the header and every row from CSV_COLUMNS, so a
   field missing from that allow-list is dropped silently. That is the
   defect `test_ward_field.py` pins.

   Usage:  node tools/fixtures/store-probe.js records.json
   Output: {"columns": [...], "head": "...", "rows": [...], "bodies": [...]}

   The file path is an argument, never stdin, so this can be run from any
   test harness without a pipe.
*/
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..", "..");
const src = fs.readFileSync(path.join(root, "assets", "store.js"), "utf8");

/* The minimal browser surface store.js touches at load and on the export
   path. Nothing here is a stand-in for the record store itself -- the real
   file is the one under test. */
const ctx = {
  window: {},
  document: { createElement() { return { style: {}, setAttribute() {}, click() {}, remove() {} }; },
              body: { appendChild() {}, removeChild() {} } },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  console: console,
};
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: "assets/store.js" });

const S = ctx.window.STORE;
const records = JSON.parse(fs.readFileSync(process.argv[2], "utf8") || "[]");
const csv = S.toCSV(records);
const lines = csv.replace(/^\ufeff/, "").trimEnd().split("\n");

process.stdout.write(JSON.stringify({
  columns: S.CSV_COLUMNS,
  head: lines[0],
  rows: lines.slice(1),
  bodies: records.map((r) => S.registerBody(r)),
}));
