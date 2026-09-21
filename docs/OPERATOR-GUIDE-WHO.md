# Operator guide — how to run the MHPSS Nepal coordination hub

For whoever holds the coordination role. Plain language, no code required for day-to-day work.

---

## 1. How to read the dashboard

Open **https://mhpss-nepal.github.io/hub/**.

The dashboard reads the register **live** — it is not a nightly copy. Each block shows a source and a
time, so you always know **what you are looking at and when it was checked**.

- **Activity reports** are coordination counts: who was reached, where, by whom, doing what.
- The board is **one dashboard with tiers inside it**, not several dashboards:
  - **T0 public** — published aggregates only (the public website).
  - **T1** — the coordination view for the TWG / MoH EDCD / WHO / cluster leads.
  - **T2** — admin plus the GBV and child-protection focal points.
  - **T3** — admin only: names, codes, audit, export.
- **What you see is decided by the server, not by the screen.** If your role may not read a kind of
  record, it is never sent to your device.

## 2. How to add a user

Access is granted **by email address, one person at a time, and every grant is recorded**.

1. Sign in as an admin and open **Access** (`/hub/access.html`).
2. Add the person's **email address** and choose the **role** that matches their tier (T1/T2/T3).
3. They sign in with **email-link sign-in** — there is no password to share or lose.
4. The grant is recorded with **who added it and when**; revoke it the same way, per person.

**Rules of thumb:** grant the *narrowest* role that does the job; never share a login; when a role is
wrong, it is a one-word change, not a rebuild. The person's name in the roles list should be the
**address**, never a free-text name.

## 3. How to publish to the public website

Publishing is **one deliberate act** and it is gated.

> ⚠️ **PUBLICATION IS CURRENTLY FROZEN.** The small-cell redaction fix is not yet live on the public
> site. **Do not publish real data to `public_stats` until that fix is deployed.** A published total
> minus a published part can currently reconstruct a suppressed small value, which could describe one
> person.

Once the fix is live, publishing works like this:

1. Sign in as a coordinator or admin and open the **publish** panel on the dashboard.
2. Choose what to publish and press **Publish**. The server refuses, by design, a document that is
   **not production mode**, declares a **suppression floor below 10**, contains **`referral_directory`**,
   or carries restricted or clinical content.
3. **Nothing publishes automatically.** A coordinator presses the button; that is the human gate.

## 4. What must NEVER be published

- Any **name, phone, email, NIK/NID, address, photo, or diagnosis** — ever, anywhere.
- Any **individual score** (for example a PHQ-9 item), and any **referral record** — a referral
  record **never** reaches `public_stats`.
- Any **count below the floor** (a row that could describe one person), and any figure from which a
  suppressed count could be worked out by subtraction.
- Any **unpublished operational figure**, or any **data-quality statement** that discloses that a
  case exists (for example *"3 records without a date in region X"*).

**If it is not already agreed for publication, it does not go to Layer 3.**

## 5. Where the field data comes from

Field officers record on a phone. Records are saved on the device first (so the form works with no
signal), then delivered to the register when the phone next connects. **A phone that never connects
and never signs in keeps its reports on the device — late is normal, absent is not.**

The **focal point** (the named person who filed a report) is deliberately removed before anything
crosses the network; it stays on the handset and in the CSV export. Someone must collect those
exports, because nothing sends them automatically.
