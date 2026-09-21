#!/usr/bin/env python3
"""Diagnose the Layer 2 homepage topology at the exact base and emit facts.

Reads the base commit out of git (never the working tree) and writes
topology.json. Every number quoted in the inventories and the QA report comes
from this file, so the documents cannot drift from the source they describe.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE = "42f308c33860987b56aadf0a5ab5e1a7be374633"
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "topology.json"


def show(path: str, ref: str = BASE) -> str:
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT, text=True)


def block(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else ""


def strip_comments(js: str) -> str:
    js = re.sub(r"/\*[\s\S]*?\*/", "", js)
    return re.sub(r"(?m)^\s*//.*$", "", js)


def main() -> None:
    index = show("index.html")
    forms = show("forms.html")
    access = show("access.html")
    redirects = {n: show(n) for n in ("coverage.html", "inbox.html")}
    fb = strip_comments(show("assets/fb.js"))
    store = strip_comments(show("assets/store.js"))
    hub = strip_comments(show("assets/hub.js"))

    rail = re.findall(r'<a[^>]+href="\./(#[\w-]+)"[^>]*>(.*?)</a>', index, re.S)
    rail_targets = [t for t, _ in rail]
    rail_labels = [re.sub(r"<[^>]+>", "", l).strip() for _, l in rail]
    tabs = re.findall(r'<button class="tab[^"]*" data-p="(\w+)">(.*?)</button>', index, re.S)
    panels = re.findall(r'<div class="panel[^"]*" id="(p-[\w-]+)">', index)
    tab_hashes = {"ov": "#overview", "who": "#who-is-where", "act": "#activities",
                  "raw": "#reports", "pub": "#publish"}
    tab_targets = [tab_hashes[t] for t, _ in tabs]

    stub_map = {}
    for name, html in redirects.items():
        m = re.search(r'location\.replace\(([^)]+)\)', html) or re.search(
            r'http-equiv="refresh" content="0; url=([^"]+)"', html)
        stub_map[name] = m.group(1) if m else "unknown"

    legacy = re.findall(r"(\w+):\s*\"(\w+)\",", block(r"var OLD_HASH = \{([\s\S]*?)\};", index))
    fb_exports = re.findall(r"(\w+):\s*[\w.]+", block(r"window\.FB = \{([\s\S]*?)\};", fb))
    store_exports = re.findall(r"(\w+)", block(r"window\.STORE = \{([\s\S]*?)\};", store).split(",")[0])
    csv_cols = re.findall(r'"([a-zA-Z0-9_]+)"', block(r"CSV_COLUMNS = \[([\s\S]*?)\];", store))

    facts = {
        "base_commit": BASE,
        "source_sha256": hashlib.sha256(index.encode()).hexdigest(),
        "homepage": {
            "sections": panels,
            "section_count": len(panels),
            "tabs": [t for t, _ in tabs],
            "tab_hashes": tab_targets,
            "rail_hash_links": rail_targets,
            "rail_hash_labels": rail_labels,
            "duplicate_rail_destinations": {k: v for k, v in collections.Counter(rail_targets).items() if v > 1},
            "destinations_reachable_from_two_controls": sorted(set(rail_targets) & set(tab_targets)),
            "ideas_inside_first_panel": [
                "coverage of the roster", "reported but not on the roster",
                "more than one organisation at one site on one day",
                "who was reached (age/sex)", "reports per day",
            ],
            "scripts_loaded": re.findall(r'<script[^>]+src="([^"]+)"', index),
            "tables_rendered": len(re.findall(r"<table", index)),
            "details_expanders": len(re.findall(r"<details", index)),
            "controls": {
                "buttons": len(re.findall(r"<button", index)),
                "selects": len(re.findall(r"<select", index)),
                "inputs": len(re.findall(r"<input", index)),
                "links": len(re.findall(r"<a\b", index)),
            },
            "endless_inline_style_blocks": len(re.findall(r'style="[^"]{20,}"', index)),
        },
        "sibling_pages": {
            "forms.html": {
                "purpose": "per-form home for the four non-5Ws instruments",
                "sections": re.findall(r'<div class="panel[^"]*" id="(p-[\w-]+)">', forms),
                "scripts_loaded": re.findall(r'<script[^>]+src="([^"]+)"', forms),
            },
            "access.html": {
                "purpose": "grant and revoke role documents; per-role sign-in",
                "scripts_loaded": re.findall(r'<script[^>]+src="([^"]+)"', access),
            },
            "redirect_stubs": stub_map,
            "legacy_hash_aliases": ["#" + a for a, _ in legacy],
        },
        "runtime_contracts": {
            "bridge_globals": fb_exports,
            "store_exports": store_exports,
            "collection": block(r'COLL = window\.FB_COLLECTION \|\| "(\w+)"', fb),
            "public_shelf_collection": "public_stats",
            "role_document_collection": "roles",
            "security_key_fields": ["kind", "schema", "server_ts", "computed_at", "basis", "published_by_role"],
            "never_sent_keys": re.findall(r'"(\w+)"', block(r"NEVER_SENT = \[([^\]]*)\]", fb)),
            "csv_columns_count": len(csv_cols),
            "csv_columns_include_ward": "ward" in csv_cols,
            "small_cell_floor_source": 10,
            "small_cell_floor_if_changed": 5,
        },
        "language": {
            "engine": ["assets/mark.js", "assets/i18n-strings.js", "assets/i18n.js"],
            "homepage_declared_default": "en",
            "effective_default": "ne",
            "note": "i18n keys are a contract; a redesign must carry every key it moves",
        },
    }
    OUT.write_text(json.dumps(facts, indent=2) + "\n")
    print(json.dumps({
        "wrote": str(OUT),
        "sections": panels,
        "duplicate_rail": facts["homepage"]["duplicate_rail_destinations"],
        "two_control_destinations": facts["homepage"]["destinations_reachable_from_two_controls"],
        "stub_pages": stub_map,
        "legacy_aliases": facts["sibling_pages"]["legacy_hash_aliases"],
        "bridge_globals": fb_exports,
        "csv_columns": len(csv_cols),
    }, indent=2))


if __name__ == "__main__":
    main()
