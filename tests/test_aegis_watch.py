"""
gltest suite for AegisWatch.

Run:  gltest tests/test_aegis_watch.py

Covers the deterministic surface: state machine, permissions, arithmetic
invariants, and refusal of impossible inputs. The convene_verifier() path
depends on live LLM inference and web fetching; the integration test at the
bottom installs mocks (llm_mocks + web_mocks) via sim_installMocks so it can
run offline against localnet.
"""

import json
import pytest
from gltest import get_contract_factory, create_account
from gltest.assertions import tx_execution_succeeded, tx_execution_failed


HIGH = 800_000
MED = 300_000
LOW = 50_000
BOND = 25_000
POOL = 2_000_000


def _deploy(sponsor):
    return get_contract_factory("Contract").deploy(args=[], account=sponsor)


def _transact(contract, method, args=None, value=0, account=None, transaction_context=None):
    if account is not None:
        contract.account = account
    return getattr(contract, method)(args=args).transact(value=value, transaction_context=transaction_context)


def _create_program(contract, sponsor, pool=POOL, high=HIGH, med=MED, low=LOW, bond=BOND,
                    scope_url="https://example.org/scope", scope_summary="Test scope"):
    return _transact(
        contract,
        "create_program",
        args=[scope_url, scope_summary, high, med, low, bond],
        value=pool,
        account=sponsor,
    )


def _submit_report(contract, reporter, program_id, urls, bond=BOND, summary="Suspicious behaviour observed."):
    evidence = json.dumps([{"url": u, "note": ""} for u in urls])
    return _transact(
        contract,
        "submit_report",
        args=[program_id, summary, evidence],
        value=bond,
        account=reporter,
    )


# ---------------------------------------------------------------------------
# Program lifecycle
# ---------------------------------------------------------------------------

def test_create_program_happy_path():
    sponsor = create_account()
    contract = _deploy(sponsor)
    receipt = _create_program(contract, sponsor)
    assert tx_execution_succeeded(receipt)

    totals = json.loads(contract.get_totals(args=[]).call())
    assert totals["programs"] == 1

    prog = json.loads(contract.get_program(args=[0]).call())
    assert prog["status"] == "PROGRAM_OPEN"
    assert prog["pool_balance"] == POOL
    assert prog["high_payout"] == HIGH


def test_create_program_rejects_non_monotonic_schedule():
    sponsor = create_account()
    contract = _deploy(sponsor)
    receipt = _transact(
        contract, "create_program",
        args=["https://example.org/scope", "s", LOW, MED, HIGH, BOND],  # ascending is wrong
        value=POOL, account=sponsor,
    )
    assert tx_execution_failed(receipt)


def test_create_program_rejects_high_payout_larger_than_pool():
    sponsor = create_account()
    contract = _deploy(sponsor)
    receipt = _transact(
        contract, "create_program",
        args=["https://example.org/scope", "s", POOL + 1, MED, LOW, BOND],
        value=POOL, account=sponsor,
    )
    assert tx_execution_failed(receipt)


def test_create_program_rejects_zero_pool():
    sponsor = create_account()
    contract = _deploy(sponsor)
    receipt = _transact(
        contract, "create_program",
        args=["https://example.org/scope", "s", HIGH, MED, LOW, BOND],
        value=0, account=sponsor,
    )
    assert tx_execution_failed(receipt)


# ---------------------------------------------------------------------------
# Report submission
# ---------------------------------------------------------------------------

def test_submit_report_rejects_bond_below_minimum():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    receipt = _submit_report(contract, reporter, 0, ["https://example.org/a"], bond=BOND - 1)
    assert tx_execution_failed(receipt)


def test_submit_report_rejects_bad_json():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    receipt = _transact(
        contract, "submit_report",
        args=[0, "bad", "not-json"],
        value=BOND, account=reporter,
    )
    assert tx_execution_failed(receipt)


def test_submit_report_rejects_empty_evidence():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    receipt = _transact(
        contract, "submit_report",
        args=[0, "summary", "[]"],
        value=BOND, account=reporter,
    )
    assert tx_execution_failed(receipt)


def test_submit_report_happy_path_marks_pending():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    receipt = _submit_report(contract, reporter, 0, ["https://example.org/a", "https://example.org/b"])
    assert tx_execution_succeeded(receipt)

    r = json.loads(contract.get_report(args=[0]).call())
    assert r["status"] == "REPORT_PENDING"
    assert r["bond"] == BOND
    assert len(r["evidence"]) == 2

    prog = json.loads(contract.get_program(args=[0]).call())
    assert prog["open_reports"] == 1


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

def test_only_reporter_can_withdraw():
    sponsor = create_account()
    reporter = create_account()
    stranger = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    _submit_report(contract, reporter, 0, ["https://example.org/a"])
    # Report is still pending, so withdraw should fail for both reasons
    # (state and permission). Stranger is refused first on permission.
    receipt = _transact(contract, "withdraw_report", args=[0], account=stranger)
    assert tx_execution_failed(receipt)


def test_only_sponsor_can_close_program():
    sponsor = create_account()
    stranger = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    receipt = _transact(contract, "close_program", args=[0], account=stranger)
    assert tx_execution_failed(receipt)


def test_cannot_close_program_with_open_reports():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    _submit_report(contract, reporter, 0, ["https://example.org/a"])
    receipt = _transact(contract, "close_program", args=[0], account=sponsor)
    assert tx_execution_failed(receipt)


# ---------------------------------------------------------------------------
# Integration - convene the AI Verifier with mocks
# ---------------------------------------------------------------------------

def _make_context(severity: str, payout: int, reason: str = "Test-mocked verdict.", injection: bool = False):
    verdict = json.dumps({
        "severity": severity,
        "payout_amount": payout,
        "reason": reason,
        "injection_flag": injection,
    })
    validator_view = json.dumps({"severity": severity, "injection_flag": injection})
    return {
        "validators": [
            {
                "plugin_config": {
                    "mock_web_response": {
                        "nondet_web_request": {
                            ".*": "Mock evidence content: independent advisory published; PoC in attached PR.",
                        }
                    },
                    "mock_response": {
                        "response": {
                            ".*triager.*": verdict,
                            ".*re-triage.*": validator_view,
                        }
                    }
                }
            }
        ]
    }


def test_verified_medium_pays_out_and_updates_pool():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    _submit_report(contract, reporter, 0, ["https://example.org/advisory"])

    ctx = _make_context("MEDIUM", MED, reason="Independent advisory published.")
    receipt = _transact(contract, "convene_verifier", args=[0], account=sponsor, transaction_context=ctx)
    assert tx_execution_succeeded(receipt)

    r = json.loads(contract.get_report(args=[0]).call())
    assert r["status"] == "REPORT_VERIFIED_MEDIUM"
    assert r["severity"] == "MEDIUM"
    assert r["payout_amount"] == MED
    # Pull-payment: reporter's withdrawable is payout + returned bond.
    assert r["withdrawable"] == MED + BOND

    prog = json.loads(contract.get_program(args=[0]).call())
    assert prog["pool_balance"] == POOL - MED
    assert prog["open_reports"] == 0


def test_debunked_forfeits_bond_to_pool():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    _submit_report(contract, reporter, 0, ["https://example.org/nothing"])

    ctx = _make_context("DEBUNKED", 0, reason="Evidence disproves the claim.")
    receipt = _transact(contract, "convene_verifier", args=[0], account=sponsor, transaction_context=ctx)
    assert tx_execution_succeeded(receipt)

    r = json.loads(contract.get_report(args=[0]).call())
    assert r["status"] == "REPORT_DEBUNKED"
    assert r["withdrawable"] == 0

    prog = json.loads(contract.get_program(args=[0]).call())
    # Bond moved into the pool.
    assert prog["pool_balance"] == POOL + BOND


def test_sponsor_reclaims_residual_after_close():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    _submit_report(contract, reporter, 0, ["https://example.org/low"])

    ctx = _make_context("LOW", LOW, reason="Cosmetic bug confirmed.")
    _transact(contract, "convene_verifier", args=[0], account=sponsor, transaction_context=ctx)

    # Reporter withdraws payout + bond first.
    _transact(contract, "withdraw_report", args=[0], account=reporter)

    receipt = _transact(contract, "close_program", args=[0], account=sponsor)
    assert tx_execution_succeeded(receipt)
    prog = json.loads(contract.get_program(args=[0]).call())
    assert prog["status"] == "PROGRAM_CLOSED"
    assert prog["pool_balance"] == 0


def test_cannot_convene_twice():
    sponsor = create_account()
    reporter = create_account()
    contract = _deploy(sponsor)
    _create_program(contract, sponsor)
    _submit_report(contract, reporter, 0, ["https://example.org/a"])

    ctx = _make_context("LOW", LOW)
    assert tx_execution_succeeded(_transact(contract, "convene_verifier", args=[0], account=sponsor, transaction_context=ctx))
    # Second convene: report is no longer pending.
    receipt = _transact(contract, "convene_verifier", args=[0], account=sponsor, transaction_context=ctx)
    assert tx_execution_failed(receipt)
