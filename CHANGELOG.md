# Changelog

Follows [Semantic Versioning](https://semver.org/).

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
