#!/usr/bin/env python3
"""Guard: the Layer 2 hub must read the register KIND-SCOPED, never unfiltered.

WHY THIS EXISTS
Firestore evaluates a *query* against its whole potential result set -- the rules
are not filters. Rules v4 scopes /submissions reads BY KIND, so an unfiltered
listen (fb.js `watch()`) is REFUSED for any restricted (non-admin) role, and the
dashboard shows an empty page (or, under an older ruleset, the whole register).
The hub must therefore ask for exactly the kind it renders, via `watchKind()`.

This guard fails if any hub surface reads the register without naming a kind, or
if the kinds it renders are not a subset of the kinds it asks for.

Run:      python3 tools/hub-live-read-scoping-check.py
Self-test: python3 tools/hub-live-read-scoping-check.py --break
           (removes the fix in a copy and asserts the guard GOES RED -- the
            broken-on-purpose proof that this guard actually bites)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent

# Surfaces that read the register, and the kind set each is expected to watch.
# index.html renders ONLY activity; forms.html renders the four instruments;
# field-output-home.html (the receiving surface for the field forms' output) reads
# ONLY activity and never writes.
#
# The set is explicit rather than discovered on purpose: a page that starts
# reading the register must be named here, so "every register read is
# kind-scoped" is a claim about a listed set and not about whatever files happen
# to be present.
SURFACES = {
    "index.html": {"declared": "Q_KINDS"},
    "forms.html": {"declared": "LIVE_KINDS"},
    "field-output-home.html": {"declared": "KINDS"},
}

# A listener that names no kind: FB.watch(fn, err). Matches `.watch(` followed by
# an identifier (the callback) -- a kind-scoped call uses `watchKind(` instead.
UNFILTERED = re.compile(r"\.watch\(\s*[A-Za-z_$]")


class GuardError(RuntimeError):
    pass


def _text(path: Path, broken: bool) -> str:
    t = path.read_text(encoding="utf-8")
    if broken:
        # Re-introduce the defect: an unfiltered listen.
        t = t.replace('window.FB.watchKind("activity", ok, err)',
                      'window.FB.watch(ok, err)')
        t = t.replace('window.FB.watchKind(k, function (rows) { mergeKind(k, rows); }, onErr);',
                      'window.FB.watch(function (rows) { mergeKind(k, rows); }, onErr);')
        t = t.replace('window.FB.watchKind(KINDS[0], function (rows) {',
                      'window.FB.watch(KINDS[0], function (rows) {')
    return t


def _declared_kinds(txt: str, var: str) -> list[str]:
    m = re.search(re.escape(var) + r"\s*=\s*\[([^\]]*)\]", txt)
    if not m:
        raise GuardError(f"no {var} declaration found")
    return re.findall(r'"([^"]+)"', m.group(1))


def _watched_kinds(txt: str, declared) -> set[str]:
    """Kinds the code asks the server for.

    Recognises both a literal (watchKind("activity", ...)) and the loop form
    (watchKind(k, ...) fed by the declared array). The loop form is only
    accepted when the declared array literally appears in the file -- a
    variable read of an undeclared kind set is not trusted.
    """
    literal = set(re.findall(r'watchKind\(\s*"([^"]+)"', txt))
    has_var_call = re.search(r"watchKind\(\s*[A-Za-z_$]", txt) is not None
    if has_var_call:
        return literal | set(declared)
    return literal


def check(broken: bool = False) -> int:
    failures = []
    for name, spec in SURFACES.items():
        p = HUB / name
        if not p.exists():
            failures.append(f"{name}: missing")
            continue
        txt = _text(p, broken)
        body = txt  # scan the whole file; both are single-page apps

        if UNFILTERED.search(body):
            failures.append(f"{name}: an UNFILTERED register listen (.watch() with no kind) is present")

        try:
            declared = set(_declared_kinds(body, spec["declared"]))
        except GuardError as e:
            failures.append(f"{name}: {e}")
            continue

        watched = _watched_kinds(body, declared)
        if not watched:
            failures.append(f"{name}: no kind-scoped register listen (watchKind) found")

        extra = watched - declared
        if extra:
            failures.append(
                f"{name}: watchKind asks for {sorted(extra)} but {spec['declared']} "
                f"does not declare them -- the read would send kinds the page does not render"
            )
        missing = declared - watched
        if missing:
            failures.append(
                f"{name}: {spec['declared']} declares {sorted(missing)} but no watchKind asks "
                f"for them -- a declared kind is never read"
            )

    if failures:
        print("HUB READ-SCOPING GUARD: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("HUB READ-SCOPING GUARD: PASS (every register read is kind-scoped)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--break", dest="broken", action="store_true",
                    help="self-test: re-introduce the defect and assert the guard GOES RED")
    args = ap.parse_args(argv)
    rc = check(broken=args.broken)
    if args.broken:
        if rc == 0:
            print("SELF-TEST FAILED: the guard did NOT go red when the defect was re-introduced.")
            return 1
        print("SELF-TEST OK: the guard went red exactly as it must.")
        return 0
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
