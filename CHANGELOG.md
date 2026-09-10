# Changelog

Follows [Semantic Versioning](https://semver.org/).

## [1.2.0] — 2026-09-10

### Added — client-side routing (Explorer review feedback)
- **Hash router.** Each view is now its own address: `#/explorer` (catalog of programs + resolved cases), `#/create`, `#/submit` / `#/submit/:programId` (pre-targeted), and `#/report/:id` (permalink to a single resolved case). Unknown routes fall back to `#/explorer`; the browser back/forward buttons work.
- **Dedicated Explorer route** for resolved cases — surfaces every verdict (severity, payout, AI rationale, consensus) at a stable URL, wallet-less, as the judge requested.
- **Resolved-case permalinks:** convening, withdrawing, and filing a report all land on `#/report/:id`, so a verdict is a shareable link.

### Changed
- Program share links now use `#/submit/:id`; legacy `?program=` / `?report=` query links are auto-migrated to the equivalent hash route on load.
- Report/program card actions and internal navigation go through the router (single source of truth for the active view).

## [1.1.0] — 2026-09-10

### Changed — usability overhaul (judge feedback)
- **Program Explorer** replaces the old tab layout. New landing tab **Explore** shows a live card catalog of every bounty Program (scope, pool, payout schedule, report count) alongside the Reports list. A reporter picks a program and clicks **Submit a report** — the Program ID and minimum bond pre-fill automatically. No more copying a raw ID by hand.
- **Persistent share panel** after `create_program`: the new **Program ID** is shown large and copyable with a one-click **shareable link** (`?program=<id>`), so a sponsor can hand it to researchers immediately (previous build only flashed the ID in a transient toast).
- **Report ID abstracted away.** Each report card carries inline **View verdict** and, when pending, **Convene AI Verifier** actions; the full verdict opens in a detail modal. The dedicated "Convene Verifier" and "Lookup by Report ID" tabs are gone.
- **Shareable deep links**: `?program=<id>` opens the Submit flow for that program; `?report=<id>` opens that report's verdict — friendlier for non-crypto ("zk") users arriving from a link.
- Reports list gains a **program filter**; program cards link straight to their own reports.

## [1.0.0] — 2026-09-07

### Added
- Intelligent Contract `contracts/aegis_watch.py`: full bounty-report lifecycle. Program (funded pool + HIGH/MEDIUM/LOW schedule + min bond) → Report (evidence URLs + staked bond) → `convene_verifier` (AI Jury) → withdraw / close.
- AI Verifier via `gl.vm.run_nondet` with a hand-written `validator_fn` that: type-checks the leader return, enforces `payout == schedule[severity]` and `payout <= pool_balance`, re-fetches evidence and re-runs an independent LLM triage, agrees within a 1-tier tolerance for HIGH/MEDIUM/LOW, requires exact match for DEBUNKED/INSUFFICIENT_PROOF, and defends against evidence-embedded prompt injection.
- Pull-payment `withdraw_report` for reporters; `close_program` returns the residual pool to the sponsor once all reports are terminal.
- `sanity/storage_test.py` — trivial contract to deploy first as an environment probe.
- `tests/test_aegis_watch.py` — gltest suite covering the deterministic surface plus three mocked integration paths (VERIFIED_MEDIUM, DEBUNKED, LOW → close_program).
- Single-file dApp `frontend/index.html`: cyber-forensic dark theme with tier-coded severity chips, four tabs (Fund Program / Submit Report / Convene Verifier / Recent Reports), wallet-less Recent Reports read via a public read-only client, MetaMask auto chain-switch.
- Logo `frontend/public/logo.svg` + rendered PNGs at 1024/512/128 — shield frame around a forensic magnifier with a red alert chevron on the anomaly.
- `scripts/seed.mjs` — Node script seeding 3 demo reports (HIGH, MEDIUM, DEBUNKED); paces at 10 s intervals and backs off on studionet RPC rate limits.
- Evidence samples under `docs/samples/evidence/` referenced by the seed script and reachable via `raw.githubusercontent.com`.
- `docs/ARCHITECTURE.md`, `EXPLORER_SUBMISSION.md` (with verified character counts), and README.

### Security
- `landlord`/`sponsor`/`reporter` permission checks on every write.
- Post-consensus arithmetic verification (`payout == schedule` and `payout <= pool_balance`) reasserted on-chain as defence in depth.
- `str`-keyed TreeMaps everywhere; `str(int(id))` conversion at every calldata boundary.
- No `DynArray[T]()` inside `@dataclass __init__` — evidence arrays live as JSON strings inside `Report` (SDK explicitly disallows the alternative on the current Studio build).
