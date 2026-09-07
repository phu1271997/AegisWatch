# AegisWatch — Decentralized Bug-Bounty & Whistleblower Report Verifier

> An **Intelligent Contract** on GenLayer that turns every bounty report into an on-chain AI Verifier verdict. Sponsors fund a bounty pool with a HIGH / MEDIUM / LOW payout schedule; reporters attach public evidence URLs and stake an anti-spam bond; validators fetch the evidence directly on-chain, run a security-triage prompt, and settle the payout.

- **Live app:** https://aegis-watch-app.vercel.app
- **Network:** **GenLayer Studio Network (studionet)**
- **Explorer:** https://explorer-studio.genlayer.com

---

## 1. Problem

Two trust holes in the bug-bounty workflow today:

1. **Grader-is-the-target.** The maintainer decides the payout for a report against their own product. Reporters have no forum when the finding is inconvenient.
2. **Spam is free.** Any pseudonymous submitter can flood the queue with regurgitated CVEs or hallucinated screenshots.

AegisWatch closes both. Grading moves to an on-chain AI Jury that reads the evidence directly and votes on the severity tier. A reporter bond makes fabricated reports economically punished — the bond is forfeited to the pool on `DEBUNKED`.

## 2. Why the project would DIE without GenLayer

The verdict requires two capabilities Solidity cannot provide:

1. **Reading unstructured evidence on the web on-chain.** `gl.nondet.web.render` fetches an advisory, a disclosed PR, a mirrored news post, or a blog into the consensus block — no oracle, no off-chain relay.
2. **Subjective severity triage.** "Independent advisory + disclosed fix + on-chain trace" is HIGH; "one cropped self-screenshot already publicly rebutted" is DEBUNKED. That judgement lives inside the validator LLM.

Strip out AI and the web reads and there is no product. AegisWatch is not blockchain plus AI; it is a machine that only works because AI runs at the consensus layer.

## 3. Consensus quality — the axis-2 story

`convene_verifier` uses `gl.vm.run_nondet(leader_fn, validator_fn)` with a hand-written validator that:

- **Enforces math before LLM.** Rejects any leader whose `payout_amount` differs from `schedule[severity]` or exceeds `pool_balance`. Two lines of Python, saves an inference call, closes a whole class of attacks.
- **Re-runs its own triage.** The validator re-fetches every evidence URL and runs an independent LLM assessment. Agrees only when severity matches within a 1-tier tolerance (HIGH~MEDIUM, MEDIUM~LOW — never HIGH~LOW). DEBUNKED and INSUFFICIENT_PROOF require exact match.
- **Defends against prompt injection.** Any instructions embedded inside evidence text are data, not commands. If the leader flagged injection, the validator only agrees with a downgrade to INSUFFICIENT_PROOF.
- **Falls through on validator LLM outage.** A validator inference blip should not manufacture a false disagreement.

Two validators that write the `reason` differently but land on the same tier consensus. Two validators that produce a matching schema but split HIGH vs LOW do not. That is the axis-2 line.

## 4. Repository layout

```
AegisWatch/
├── contracts/aegis_watch.py     # Main Intelligent Contract (~400 lines)
├── sanity/storage_test.py       # Deploy first as an environment probe
├── frontend/
│   ├── index.html               # Single-page dApp, calls the contract via genlayer-js
│   ├── src/config.js            # CONTRACT_ADDRESS + CHAIN
│   └── public/logo.*            # 1024/512/128 PNG + SVG source
├── tests/test_aegis_watch.py    # gltest: state machine, permissions, invariants, mocked adjudication
├── scripts/
│   ├── deploy.sh                # localnet convenience script (Studio UI is primary)
│   └── seed.mjs                 # 3 demo reports: HIGH, MEDIUM, DEBUNKED
├── docs/
│   ├── ARCHITECTURE.md
│   └── samples/evidence/*.txt   # 4 evidence sources hosted from GitHub raw
├── EXPLORER_SUBMISSION.md       # Portal form draft with verified character counts
├── CHANGELOG.md
└── README.md
```

## 5. Deploying the contract to studionet

Studio UI is the primary deploy path (matches the live app):

1. Open https://studio.genlayer.com/run-debug
2. **Settings → Reset Storage → Confirm → hard refresh** (Cmd/Ctrl+Shift+R).
3. Deploy `sanity/storage_test.py` first. Open the transaction and confirm **Result: SUCCESS**. If that fails, the environment is at fault — do not proceed.
4. Deploy `contracts/aegis_watch.py`. Same check: open the deploy tx, confirm `Result: SUCCESS`.
5. Copy the contract address into `frontend/src/config.js` (`CONTRACT_ADDRESS`) or set `VITE_CONTRACT_ADDRESS` in the Vercel build environment.

**Funding your MetaMask address on studionet:** Studio → **Accounts** panel → transfer GEN from a pre-funded Studio account to the address you use with MetaMask. There is **no public faucet** for studionet; the testnet faucet at `testnet-faucet.genlayer.foundation` funds testnet only.

If `gh` CLI is authed (`gh auth status`) and you want a fresh remote:

```bash
gh repo create phu1271997/AegisWatch --public --source=. --push
```

## 6. Running the frontend

```bash
cd frontend
npm install
VITE_CONTRACT_ADDRESS=0x<your contract> npm run dev
```

Open the app in a browser with MetaMask installed. **Connect Wallet** — the app runs `wallet_switchEthereumChain` (falls back to `wallet_addEthereumChain`) so MetaMask lands on studionet before any signed tx. Walk the four tabs: Fund Program → Submit Report → Convene Verifier → Recent Reports.

Recent Reports uses a **wallet-less read client** — visitors browse existing verdicts without connecting.

**Deploying live** (Vercel): point the project at the `frontend/` directory, set `VITE_CONTRACT_ADDRESS` and `VITE_CHAIN=studio` as environment variables, and build.

## 7. End-to-end demo flow

1. **Sponsor** creates a Program: pool 2_000_000, HIGH 800_000, MEDIUM 300_000, LOW 50_000, min_bond 25_000.
2. **Reporter** submits a Report against Program 0: staked bond 25_000, summary "signature-replay in AcmeSwap /api/withdraw", evidence URLs = advisory + disclosed PR.
3. Anyone calls **Convene Verifier** → nondet block fetches every URL, runs the triage prompt, validators consensus.
4. Verdict written on-chain: severity HIGH, payout 800_000, reason quoting which evidence source drove the tier.
5. Reporter calls **withdraw_report** → pull-payment for `payout + bond`.
6. Once every report on a Program is terminal, **sponsor** calls **close_program** → residual pool returned.

## 8. Seeding demo data

Peter runs this once with his funded key (see funder note at bottom):

```bash
cd frontend
npm install
cp ../scripts/seed.mjs ./seed-run.mjs
export AEGIS_PRIVATE_KEY=0x<a funded studionet key>
export VITE_CONTRACT_ADDRESS=0x<contract>
node seed-run.mjs
rm seed-run.mjs
```

Creates one Program and three Reports: one HIGH_VERIFIED, one MEDIUM_VERIFIED, one DEBUNKED. Roughly 5–10 GEN needed in the funder wallet (pool + bonds + gas).

The script paces itself at 10-second poll intervals to stay under the studionet public RPC cap of 30 requests per minute per IP and backs off on `-32029` rate-limit errors.

## 9. Tests

```bash
gltest tests/test_aegis_watch.py
```

Covers: state machine, permission checks (only reporter withdraws, only sponsor closes), refusal of impossible inputs (non-monotonic schedule, HIGH payout larger than pool, empty evidence, bond below minimum, close-with-open-reports), and the deposit-conservation invariant. The `test_verified_medium_pays_out_and_updates_pool`, `test_debunked_forfeits_bond_to_pool`, and `test_sponsor_reclaims_residual_after_close` tests install `sim_installMocks` (llm_mocks + web_mocks) so they run offline against localnet.

## 10. Further reading

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — data model, consensus design, money flow, "what Solidity cannot do".
- [`EXPLORER_SUBMISSION.md`](EXPLORER_SUBMISSION.md) — Portal Explorer submission draft with character counts already verified against the form caps.

---

*AegisWatch is deployed on **GenLayer Studio Network (studionet)**. Explorer listing status will be **Preview** — studionet is not testnet.*
