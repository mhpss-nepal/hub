#!/usr/bin/env python3
"""The coordination dashboard follows the field forms. This checks that it still does.

23 September 2026. The Coordinator's decision: the forms are built, reviewed and
in people's hands, so the dashboard is the surface that moves. `assets/hub-shell.css`
therefore adopts the `--fx-*` tokens declared in `assets/form.css`.

Adopting means copying the values, because a stylesheet cannot read a custom
property that was declared inside a selector it does not match — form.css declares
them on `body.fx`, and the hub is `body.hub`. Two copies of a palette is precisely
how the form and the coordination view come to disagree, which this project has
already written down once. So the copy is not left to anyone remembering: this
gate reads both files and refuses the deploy the moment one of them moves.

It checks only the tokens the hub actually adopted. A token the hub does not use
is not the hub's business, and failing on it would teach people to ignore the gate.

Exit 0 when every adopted token matches. Exit 1, naming the token and both values,
when one does not.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
FORM = HERE / "assets" / "form.css"
SHELL = HERE / "assets" / "hub-shell.css"

# The tokens hub-shell.css adopts, and the hub token each one is mapped onto.
# Left: the name as form.css declares it. Right: how hub-shell.css spells it.
ADOPTED = {
    "--fx-bg": "--bg",
    "--fx-line": "--line",
    "--fx-line-s": "--line-s",
    "--fx-r": "--r",
    "--fx-rs": "--fx-rs",
    "--fx-shadow": "--fx-shadow",
    "--fx-blue-d": "--fx-blue-d",
    "--fx-blue-dd": "--fx-blue-dd",
}

DECL = r"{name}\s*:\s*([^;}}]+)"


def read(path):
    if not path.is_file():
        sys.exit("MISSING {}".format(path.relative_to(HERE)))
    return path.read_text(encoding="utf-8")


def value(text, name):
    """The last declaration wins in CSS, so take the last one."""
    found = re.findall(DECL.format(name=re.escape(name)), text)
    return found[-1].strip() if found else None


def norm(v):
    """Compare what renders, not how it was typed: collapse whitespace, lowercase."""
    return re.sub(r"\s+", " ", v).strip().lower() if v else v


def main():
    form = read(FORM)
    shell = read(SHELL)

    print("The dashboard follows the field forms -- token parity")
    print("  source  assets/form.css        (body.fx)")
    print("  adopter assets/hub-shell.css   (body.hub)")
    print()

    bad = []
    for fx_name, hub_name in sorted(ADOPTED.items()):
        want = value(form, fx_name)
        got = value(shell, hub_name)
        if want is None:
            bad.append((fx_name, "not declared in form.css", "--"))
            continue
        if got is None:
            bad.append((hub_name, want, "not declared in hub-shell.css"))
            continue
        mark = "ok" if norm(want) == norm(got) else "DRIFTED"
        shown = want if len(want) < 46 else want[:43] + "..."
        print("  {:<16} -> {:<12} {:<48} {}".format(fx_name, hub_name, shown, mark))
        if norm(want) != norm(got):
            bad.append((hub_name, want, got))

    print()
    if bad:
        print("FX TOKEN PARITY: FAIL")
        for name, want, got in bad:
            print("  {}".format(name))
            print("      form.css      {}".format(want))
            print("      hub-shell.css {}".format(got))
        print()
        print("  form.css is the source. Make hub-shell.css follow it, or, if the")
        print("  dashboard is deliberately parting company with the forms, take the")
        print("  token out of ADOPTED in this file and say in the commit why.")
        return 1

    print("FX TOKEN PARITY: PASS ({} adopted tokens match)".format(len(ADOPTED)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
