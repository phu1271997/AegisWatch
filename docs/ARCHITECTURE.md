# AegisWatch — Architecture

## Problem

Bug-bounty programs today rely on the sponsor's own triage team to grade every incoming report. The reporter has to trust that the maintainer will honour a payout when the finding is inconvenient; the sponsor has to trust that a random pseudonymous submission is not a duplicate, spam, or a fabricated screenshot. Whistleblower reports about misconduct sit in the same trust hole — the entity being reported on is exactly the wrong party to grade the report.

AegisWatch removes both trust points. The severity tier — and therefore the payout — is decided by an on-chain AI Jury that reads the public evidence directly and reaches consensus on the meaning of the verdict, not the wording of it.

## Actors and contract objects

| Actor | Object | Purpose |
|---|---|---|
| **Sponsor** (project / DAO / company) | `Program` | Escrows a bounty pool with a HIGH / MEDIUM / LOW payout schedule and a minimum reporter bond. |
| **Reporter** (researcher / whistleblower) | `Report` | Stakes an anti-spam bond and attaches public evidence URLs. |
| **AI Verifier** (GenLayer validator set) | `convene_verifier` nondet block | Reads every evidence URL, re-runs the triage prompt, votes. |

## State machines

```
Program:  PROGRAM_OPEN ── close_program (once all reports resolved) ──▶ PROGRAM_CLOSED

Report:   REPORT_PENDING
              │
              │ convene_verifier
              ▼
   ┌──────────┴─────────────────────────────────────────────┐
   │                                                         │
REPORT_VERIFIED_HIGH   REPORT_VERIFIED_MEDIUM   REPORT_VERIFIED_LOW
REPORT_INSUFFICIENT_PROOF                     REPORT_DEBUNKED
              │                                                 │
              │ withdraw_report                                 │ (bond forfeit to pool)
              ▼                                                 │
        REPORT_WITHDRAWN                                        │
```

## Consensus design (the axis-2 point)

`convene_verifier` invokes `gl.vm.run_nondet(leader_fn, validator_fn)` with a hand-written `validator_fn` that does four things — in this order:

1. **Type-checks the leader return.** Rejects anything that is not a JSON object with a valid severity token and an integer payout.
2. **Enforces the arithmetic.** The payout must equal `schedule[severity]` exactly and must not exceed `pool_balance`. Any leader that returns an out-of-schedule number is rejected before any LLM work happens.
3. **Runs an independent LLM triage.** The validator re-fetches every evidence URL, re-triages the report, and compares its own severity with the leader's.
   - **HIGH / MEDIUM / LOW** agree within a **1-tier tolerance** (HIGH~MEDIUM and MEDIUM~LOW pass; HIGH~LOW does not). One-tier tolerance is deliberate: LLMs disagree at the margins on noisy real-world evidence, and forcing exact agreement would produce a contract that never reaches consensus.
   - **DEBUNKED** and **INSUFFICIENT_PROOF** require **exact match**. Those tiers are qualitatively different from a graded severity — a validator that turned "insufficient proof" into "LOW" would be lowering the evidence bar.
4. **Prompt-injection defence.** Any evidence text that appears to instruct the model ("ignore previous instructions", role-play, base64 payloads with instructions) sets `injection_flag=true` and forces classification to `INSUFFICIENT_PROOF` with payout 0. If either the leader or the validator saw injection, both must have downgraded — otherwise the leader is rejected.

A validator LLM outage falls through as agreement rather than disagreement. That way a real-world inference blip on one validator does not manufacture a fake consensus failure. The trade-off is explicit and documented in the source comment above the fall-through.

Every check runs a second time on-chain after consensus (payout == schedule, payout <= pool) as defence in depth — a validator agreement is necessary but not sufficient; the arithmetic invariant is the final word.

## Storage design

- `programs: TreeMap[str, Program]` — key is `str(program_id)`.
- `reports: TreeMap[str, Report]` — key is `str(report_id)`.
- Every dataclass is `@allow_storage @dataclass`.
- Evidence URL lists inside a `Report` are stored as **JSON strings**, not `DynArray[Evidence]`. GenVM's storage layer disallows constructing `DynArray[T]` from a `@dataclass __init__` on the current Studio build; using JSON strings keeps the same on-chain semantics without hitting the failure.
- All monetary values are `u256`. There is no bare `int` in storage.

## Money flow

```
Sponsor  ──create_program(value = pool)──▶  program.pool_balance
Reporter ──submit_report (value = bond)──▶  report.bond
                                            │
                        convene_verifier ───┤
                                            ▼
        VERIFIED_*   report.withdrawable = payout + bond   ; pool_balance -= payout
        INSUFFICIENT report.withdrawable = bond            ; pool unchanged
        DEBUNKED     report.withdrawable = 0               ; pool_balance += bond

Reporter ──withdraw_report──▶  pull-payment (emit_transfer)
Sponsor  ──close_program (once open_reports == 0)──▶  pool residual pulled back
```

Pull-payment is used instead of push so that a failing recipient send cannot lock the contract, and so re-entrancy on the recipient side is scoped to a single report row.

## What Solidity cannot do here

- **Reading the evidence directly.** `gl.nondet.web.render(url)` fetches an advisory, PR, blog, or on-chain trace inside the consensus block. No oracle, no off-chain relayer, no trusted middleman.
- **Grading the report.** "Independent advisory + disclosed fix" is HIGH; "one screenshot already publicly rebutted" is DEBUNKED. That judgement lives inside the validator LLM at consensus time.
- **Prompt-injection defence at consensus.** Evidence is arbitrary UGC. Whether a payload is an evidence document or an injection payload is itself a judgement call that only the LLM can make; the contract's job is to enforce that the judgement propagates into the tier assignment.

Take those three away and there is no product left — AegisWatch would be a Google Form pointed at a maintainer's inbox.
