# GENLAYER PROJECT EXPLORER — AegisWatch Submission Draft
**Prepared:** 2026-09-07 · **Status:** DO NOT SUBMIT YET — awaiting on-chain seed

## Pre-submit gate status

- Contract deployed on studionet: `TO_BE_FILLED_AFTER_DEPLOY` — verify with `gen_getContractSchema` before submitting.
- Live app: https://aegis-watch-app.vercel.app — MetaMask connect, chain auto-switch, Recent Reports browsable without a wallet.
- Seed data required before Submit: 1 HIGH_VERIFIED, 1 MEDIUM_VERIFIED, 1 DEBUNKED on Program 0. Run `scripts/seed.mjs` with the funded key (see README §8).
- Explorer URL after deploy: `https://explorer-studio.genlayer.com/address/<contract>` — open in a browser and confirm `convene_verifier` transactions show `GENVM RESULT: SUCCESS` and `CONSENSUS RESULT: Accepted` before hitting Submit.

---

## Project name
**AegisWatch**

## Primary category
**Dispute Resolution**

*Rationale:* GenLayer positions itself as the "adjudication layer" — AegisWatch is a literal adjudication use case: reporter and sponsor disagree on the severity (and therefore the payout) of a claim, and an on-chain AI Jury issues a binding verdict that the contract enforces via escrowed money. Chose this over `AI & Agents` deliberately: almost every project in the Explorer catalog is AI-powered, so that label would sink the listing in a shuffled catalog. Chose this over `DeFi` because the money movement is instrumental — the interesting mechanism is the adjudication.

## Category tags

- **Tag 1 — Evidence Assessment** *(what every reviewer sees first)*
  Implemented by `convene_verifier()` in `contracts/aegis_watch.py`. The nondet leader iterates over the `evidence` list, calls `gl.nondet.web.render(url, mode="text")` on each URL, and feeds the rendered content into the security-triage prompt. The verdict is grounded in what the evidence actually says, not in the reporter's own summary.

- **Tag 2 — Escrow Claims** *(the settlement side)*
  Implemented by `create_program` (payable — sponsor escrows the pool) → `submit_report` (payable — reporter escrows anti-spam bond) → `convene_verifier` (verdict decides the tier; contract enforces `payout == schedule[severity]` and `payout <= pool_balance`) → `withdraw_report` and `close_program` (pull-payment settlement, residual to sponsor).

*Rejected:* `Moderation Appeals` (no takedown mechanic), `License Claims` (no license terms), `Appeal Review` (single-round adjudication, no second-instance re-review), `Jury Selection` (the AI Jury is chosen by GenLayer's validator set, not by AegisWatch — using this tag would misrepresent the mechanism).

## Logo
`frontend/public/logo.png` — 1024×1024, ~1.1 MB, PNG. Shield frame around a forensic magnifier lens with a red alert chevron on the anomaly. SVG source at `frontend/public/logo.svg`. Verified readable at 128 px.

## One-liner (137 / 180)
AI validators triage bounty reports on-chain: they read the evidence URLs, assign a HIGH/MEDIUM/LOW severity tier, and settle the payout.

## Description (984 / 1000)
AegisWatch turns every bounty report into an on-chain AI Verifier verdict.

Sponsors fund a Program with a bounty pool and a HIGH/MEDIUM/LOW payout schedule plus a minimum reporter bond. Researchers file Reports with public evidence URLs (advisories, disclosed PRs, blog posts, on-chain traces, mirrored posts) and stake an anti-spam bond. Any caller runs convene_verifier: validators call gl.nondet.web.render on every URL, run a security-triage prompt inside the consensus block, and vote on the tier. The contract enforces payout == schedule[severity] and payout <= pool_balance.

For security teams tired of maintainer-graded bounties, and for whistleblowers filing against an entity that would never grade fairly against itself.

Solidity cannot read the evidence on-chain or triage severity. Validators agree on the MEANING of the verdict, not its wording: HIGH~MEDIUM within one tier passes, HIGH~LOW does not. Verified pays payout+bond; DEBUNKED forfeits the bond to the pool.

## How to try it

**Prerequisites**
- MetaMask installed. The app switches or adds the GenLayer Studio Network for you on connect (chain id 61999 / 0xF1EF).
- ~2 GEN on your MetaMask address on studionet. Fund it from Studio → Accounts panel (https://studio.genlayer.com) by transferring from a pre-funded account. There is no public faucet for studionet.
- No wallet needed just to browse existing verdicts.

**Step 1 — Browse existing reports (no wallet).**
Open the app → **Recent Reports** tab. You will see three seeded reports on Program 0: one HIGH_VERIFIED, one MEDIUM_VERIFIED, one DEBUNKED. Click any row to open the full verdict, including the AI Verifier's rationale citing which evidence source drove the tier.

**Step 2 — Connect a wallet.**
Click **Connect Wallet** (top right). MetaMask pops up, then auto-switches to the GenLayer Studio Network. Your address appears next to the button.

**Step 3 — Fund a Program as a sponsor.**
Go to **Fund Program**. Set scope URL and a one-line scope summary. Set pool (e.g. `2000000`), min bond (`25000`), and payouts HIGH `800000` / MEDIUM `300000` / LOW `50000`. Click **Escrow Pool & Create Program**. Wait ~30 seconds for finalization.

**Step 4 — Submit a Report.**
Go to **Submit Report**. Enter the program id from Step 3, bond ≥ program minimum, a one-line summary, and one or more evidence URLs (one per line). The seed script uses raw.githubusercontent.com URLs from this repo — any public URL works. Click **Stake Bond & Submit Report**.

**Step 5 — Convene the AI Verifier.**
Go to **Convene Verifier** (the Report ID is already prefilled). Click **Request AI Triage**. The nondet block fires: validators fetch every URL, run the triage prompt, and vote. Takes 1–3 minutes. When it finishes, the verdict is fetched and rendered below with the tier badge, payout, and plain-English reason.

**Expected end state:** a new Report appears in Recent Reports with status **REPORT_VERIFIED_HIGH / MEDIUM / LOW** or **REPORT_DEBUNKED**, a payout that matches the program schedule for that tier, and a rationale grounded in the evidence you submitted.

**If something goes wrong**
- "MetaMask required" — install MetaMask and reload.
- `insufficient funds` — your MetaMask address has no GEN on studionet. Fund from Studio Accounts (Step 2 prerequisites).
- Triage stuck > 3 minutes — refresh the page and use **Lookup a Report** to fetch the current state.

## Expected verification outcome (461 / 500)
Recent Reports shows three RESOLVED reports on Program 0 with distinct tiers: one HIGH_VERIFIED with payout 800000, one MEDIUM_VERIFIED with payout 300000, one DEBUNKED with bond forfeited to the pool. Each has a plain-English reason citing specific evidence sources - proof validators fetched the URLs and triaged them on-chain, not hardcoded. Explorer address page shows convene_verifier transactions with GENVM RESULT: SUCCESS and CONSENSUS RESULT: Accepted.

## Contract link
`https://explorer-studio.genlayer.com/address/<contract>`

- **Address:** `TO_BE_FILLED_AFTER_DEPLOY`
- **Network:** studionet (GenLayer Studio hosted)
- **Status:** **Preview** (studionet ≠ testnet)
- **Verify before submit:** open the Explorer link and confirm at least one `convene_verifier` transaction with `Result: SUCCESS` and `Consensus: Accepted`.

## Website
https://aegis-watch-app.vercel.app

## GitHub
https://github.com/phu1271997/AegisWatch

## Community links (optional)
Leave blank.

---

## FINAL CHECKLIST (tick before you hit Submit on Portal)

**Truthfulness**
- [ ] Every feature in the description works on the live app right now
- [ ] Status **Preview** matches studionet
- [ ] Each tag maps to a real function

**Deploy state**
- [ ] Local commits pushed to `main`
- [ ] Vercel finished the build (open live URL and hard-refresh)
- [ ] `gen_getContractSchema` returns all methods on the address in `frontend/src/config.js`
- [ ] Explorer address page opens in a browser and shows `convene_verifier` tx with SUCCESS / Accepted

**End-to-end (do it, don't imagine it)**
- [ ] Seeded: 1 HIGH_VERIFIED, 1 MEDIUM_VERIFIED, 1 DEBUNKED on Program 0 — visible in incognito without wallet
- [ ] Full path walked with a fresh MetaMask account: connect → fund → submit → convene → verdict shows

**Assets & limits**
- [ ] Logo: `frontend/public/logo.png` (PNG, 1024×1024, ~1.1 MB, verified at 128 px)
- [ ] One-liner: 137 chars (limit 180)
- [ ] Description: 984 chars (limit 1000)
- [ ] Expected verification outcome: 461 chars (limit 500)
- [ ] GitHub URL provided; Website URL also provided

**Consequences understood**
- [ ] Changes requested = one fix pass, 14 days
- [ ] Declined = no self-service resubmit
- [ ] 1 Projects contribution = 1 Explorer entry
