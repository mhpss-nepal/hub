# Layer 2 homepage — redundancy inventory

**Base commit:** `42f308c` (`git show 42f308c:index.html`, SHA-256
`8ce3ebfc77ed851161dacf20621c03cc0598a60a8b3478b9e72f7f71c84e1979`)
**Method:** `design-preview/diagnose.py` reads the base commit out of git and
writes `topology.json`; every count below is taken from that file. Run
`python3 design-preview/diagnose.py` to reproduce it.

The problem is not that the Hub has too much *data*. It is that the same
**destination, question and label** is served from several places at once, so a
coordinator has to work out which control is authoritative before reading a
single figure — and the first screen answers five different questions in one
panel.

## 1. Navigation: one destination, several controls

The homepage carries two navigations that write the **same five hashes**.

| Fact | Value |
|---|---|
| Homepage sections | `p-ov`, `p-who`, `p-act`, `p-raw`, `p-pub` (5) |
| Tab buttons above the panels | 5, writing `#overview #who-is-where #activities #reports #publish` |
| Left-rail hash links | 6, writing the same five hashes |
| Destinations reachable from **both** controls | `#overview`, `#who-is-where`, `#activities`, `#reports`, `#publish` — **all five** |
| Hash duplicated **within** the rail | `#reports` appears **twice** (`Reports received` and `Activity report (5Ws)`) |

Consequences, each observed in the source rather than inferred:

- **Two controls, one state.** A rail click and a tab click both call
  `history.replaceState` with the same hash, and both light themselves up via
  `window.__railMark`. Two controls compete to say "you are here".
- **The same page is named twice.** `Reports received` (tab + rail) and
  `Activity report (5Ws)` (rail, second occurrence) resolve to `#reports`. The
  `Activity report (5Ws)` entry is a *relabelling of a destination that already
  exists*, not a new destination.
- **Twelve legacy hash aliases** are kept on the page for links already sent:
  `#gaps #duplication #matrix #activity #records #publish #coverage #who #what
  #when #people #helpline`. Twelve old names now point at five sections, which
  is the history of this page reconverging written into the code.

## 2. Sibling pages that only forward

Two pages exist solely to redirect, and the homepage still names them in prose:

| Page | What it actually does | Where the content lives now |
|---|---|---|
| `coverage.html` | `location.replace("./" + hash-mapped)` + a `<meta refresh>` | a panel of the homepage |
| `inbox.html` | `location.replace("forms.html" + hash)` + a `<meta refresh>` | `forms.html` and the homepage |

They are correct as compatibility shims and must be **kept**; the point for the
redesign is that the *navigation* should have one home, and these should never be
the thing a coordinator is asked to remember.

## 3. One panel, five questions

`index.html` renders **11 tables, 7 expanders, 24 buttons, 11 selects, 12 inputs
and 16 links**, with **15 long inline `style="…"` blocks** used as one-off
layout. The first panel alone (`#overview`, `p-ov`) answers five separate
coordination questions in a single scroll:

1. coverage of the roster;
2. sites reported but not on the roster;
3. more than one organisation at one site on one day (duplication);
4. who was reached (age/sex disaggregation);
5. reports per day.

Each is a different decision with a different reader. Stacked, they make the
opening screen a memo rather than a dashboard, and the section's own method note
had to be pushed behind an expander to stop the panel reading as long-form prose.

## 4. Prose that repeats the figures

The same instruction is written out more than once on the same screen:

- **Three status notices** say the same thing about where the numbers come from
  (`#srcNote`, the `.livestrip`, and the loader's own paragraph). The source
  itself acknowledges this: *"Three stacked notices said the same thing three
  ways."*
- The roster caveat appears in the coverage lede, in the *How this is counted*
  expander, **and** in the page footer note.
- The attendances-are-not-people caveat appears in the stats strip, the activity
  table's expander, and the publication banner.

Any figure a reader has to be told three times to distrust is a figure that is
being presented in the wrong place.

## 5. What is *not* redundant (do not consolidate it away)

Recorded here so a later consolidation does not delete something load-bearing:

- **Five destinations is right.** `#overview`, `#who-is-where`, `#activities`,
  `#reports`, `#publish` are genuinely different jobs, and the Layer 2 access
  record maps them to different role rights. Reduce the *controls*, never the
  *destinations*.
- **`forms.html` and `access.html` are separate for a reason.** One is the
  per-instrument home; the other is the only place a role can be granted or
  revoked. Neither belongs on the homepage, and neither may be merged into it.
- **The redirect stubs stay.** They hold addresses already in circulation.
- **The legacy hash aliases stay.** They are contract, not clutter.

## 6. Consolidation levers the concepts use

| Lever | Conservative (A) | Recommended (B) | Divergent (C) |
|---|---|---|---|
| Controls writing one state | one left rail, hash links kept | one app bar + section blocks, hash links kept | one app bar + question router |
| The five destinations | unchanged | unchanged | unchanged (behind questions) |
| Status notices | one freshness block | one freshness block + a state demo | one freshness block |
| Method prose | one expander per block, closed | one expander at the foot | one expander at the foot |
| First screen | KPI band | priority figure + KPI band | four questions |
| Filters | one bar, visible | one bar, prominent, chips visible | one bar, persistent across questions |
| Filters vs. figures | filters above the figures | filters above, drill-down from every bar | filters above, drill-down inside each question |

The recommended concept (B) removes no destination and no contract, and reduces
the *controls and notices* that say the same thing: one freshness/status block,
one method expander, one filter bar, and one place — the hero — that names the
priority.
