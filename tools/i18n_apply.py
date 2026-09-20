#!/usr/bin/env python3
"""Add the new page keys to the shared dictionary, English first.

Run from the hub repository root.

  python3 tools/i18n_apply.py --en FILE             English only
  python3 tools/i18n_apply.py --en FILE --ne FILE   Nepali drafts as well

This is deliberately APPEND-ONLY. It inserts new keys at the end of the
`en` block and the `ne` block and leaves every existing line exactly as it
was, so the diff for this change contains the new pages' text and nothing
else -- no reordered keys, no lost comments. A rewrite of the whole block
would have been a few lines shorter to write and impossible to review.

What it enforces rather than trusts:

  * an existing key whose English differs is REPORTED, not silently
    overwritten -- a page silently re-pointed at new wording is exactly
    the drift the bilingual gate exists to catch;
  * a key under a professionalOnly prefix gets NO Nepali entry, whatever
    the input file says: those render in English on the Nepali page;
  * every Nepali string written is listed in _meta.source.machine. This
    script has never seen a human translator and will not label its own
    output as human.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRINGS = ROOT / "assets" / "i18n-strings.js"
PROTECTED = ["phq9.item", "phq9.scale", "phq9.cutoff", "consent.", "safeguard.", "clinical."]


def js(value):
    return json.dumps(value, ensure_ascii=False)


def find_block(source, name):
    """Return the match for `\n  <name>: {` .. the matching `\n  },`/`\n  }`."""
    return re.search(r"\n  " + name + r":\s*\{(.*?)\n  \}[,;]?\n", source, re.S)


def keys_in(source, name):
    match = find_block(source, name)
    if not match:
        raise SystemExit(f"could not find the `{name}` block")
    body = re.sub(r"/\*.*?\*/", "", match.group(1), flags=re.S)
    body = re.sub(r"^\s*//.*$", "", body, flags=re.M)
    return {k: v for k, v in re.findall(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', body)}


def append_to_block(source, name, additions, comment):
    """Insert `additions` (list of (key, value)) just before the block closes."""
    match = find_block(source, name)
    if not match:
        raise SystemExit(f"could not find the `{name}` block")
    existing = keys_in(source, name)
    new = [(k, v) for k, v in additions if k not in existing]
    if not new:
        return source, []
    lines = "".join("    " + js(k) + ": " + js(v) + ",\n" for k, v in new)
    body = match.group(1)
    insertion = "\n" + (comment + "\n" if comment else "") + lines.rstrip("\n")
    close = match.end(1)
    # keep the closing newline + indentation the block already had
    return source[:close] + insertion + source[close:], [k for k, _ in new]


def append_to_meta_list(source, list_name, keys):
    """Append keys to a _meta array without disturbing what is already there."""
    match = re.search(r"(" + list_name + r":\s*\[)(.*?)(\]\s*,?\s*human|\]\s*\})", source, re.S)
    if not match:
        raise SystemExit(f"could not find _meta list `{list_name}`")
    body = match.group(2)
    present = set(re.findall(r'"((?:[^"\\]|\\.)*)"', body))
    add = [k for k in keys if k not in present]
    if not add:
        return source, []
    # one entry per line, same indentation as the surrounding entries; the
    # last existing entry may have no trailing comma, so add one.
    indent = re.search(r"\n(\s+)\"[^\"]+\"", body)
    indent = indent.group(1) if indent else "      "
    tail = body.rstrip()
    tail = tail + ("," if not tail.endswith(",") else "")
    addition = "".join("\n" + indent + js(k) + "," for k in add)
    return source[:match.start(2)] + tail + addition + source[match.end(2):], add


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--en", required=True)
    parser.add_argument("--ne")
    parser.add_argument("--revision", default="")
    args = parser.parse_args()

    source = STRINGS.read_text(encoding="utf-8")
    entries = json.loads(Path(args.en).read_text(encoding="utf-8"))

    existing_en = keys_in(source, "en")
    conflicts = sorted(e["key"] for e in entries
                       if e["key"] in existing_en and existing_en[e["key"]] != e["en"])
    additions = [(e["key"], e["en"]) for e in entries]
    source, added = append_to_block(source, "en", additions, "")
    print(f"en: +{len(added)} keys ({len(entries)} offered, {len(entries) - len(added)} already present)")
    if conflicts:
        print("  REPORTED, left as they were (English differs from the submitted value):")
        for key in conflicts:
            print(f"    {key}")

    if args.ne:
        drafts = json.loads(Path(args.ne).read_text(encoding="utf-8"))
        kept_out = sorted(k for k in drafts if k.startswith(tuple(PROTECTED)))
        additions = [(k, v) for k, v in sorted(drafts.items())
                     if not k.startswith(tuple(PROTECTED)) and v.strip()]
        comment = ("    /* ---- referral, PHQ-9 and service contact forms (machine drafts,\n"
                   "       20 Sep 2026 -- NOT checked by a Nepali speaker) ---- */\n"
                   "    /* Two independent machine translators, compared key by key, then\n"
                   "       back-translated to English. A key where the two disagreed, or where\n"
                   "       the back-translation shifted the meaning, was left in English on\n"
                   "       purpose rather than picked silently, and is not in this block. Terms\n"
                   "       that already exist in the response's own material were locked to\n"
                   "       those -- assets/codes.js and the pairs already in this file -- so the\n"
                   "       forms keep matching the national vocabulary. */")
        source, added = append_to_block(source, "ne", additions, comment)
        print(f"ne: +{len(added)} machine drafts "
              f"({len(kept_out)} protected keys deliberately given no Nepali: "
              f"{', '.join(kept_out) if kept_out else 'none'})")

    if args.revision:
        source, count = re.subn(r'(revision:\s*")[^"]*(")', r"\g<1>" + args.revision + r"\g<2>",
                                source, count=1)
        print(f"revision -> {args.revision}" if count else "revision NOT changed (pattern not found)")

    nepali = keys_in(source, "ne") if args.ne else keys_in(source, "ne")
    machine = sorted(k for k, v in nepali.items() if v.strip())
    source, added = append_to_meta_list(source, "machine", machine)
    print(f"_meta.source.machine: +{len(added)} keys, {len(machine)} listed in total")

    STRINGS.write_text(source, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
