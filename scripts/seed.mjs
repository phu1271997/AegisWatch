// Seed three demo reports on studionet so the Explorer catalog has visible
// on-chain state from the moment the AegisWatch listing goes live.
//
// One HIGH_VERIFIED (advisory + disclosed PR)
// One MEDIUM_VERIFIED (forum thread confirmed by maintainer)
// One DEBUNKED (single screenshot already publicly rebutted)
//
// Usage (from frontend/ so genlayer-js resolves through its own node_modules):
//   cd frontend
//   npm install
//   cp ../scripts/seed.mjs ./seed-run.mjs
//   export AEGIS_PRIVATE_KEY=0x<a funded studionet key>
//   export VITE_CONTRACT_ADDRESS=0x<deployed aegis_watch contract>
//   node seed-run.mjs
//   rm seed-run.mjs
//
// The script is idempotent: reports already in a terminal state are skipped.
// It paces itself at 10s poll intervals to stay under the studionet public RPC
// cap (30 requests/minute per IP) and backs off on -32029 rate-limit errors.
//
// Requires roughly 5-10 GEN in the funder wallet on studionet.

import { createClient, createAccount } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const CONTRACT = process.env.VITE_CONTRACT_ADDRESS;
const PK = process.env.AEGIS_PRIVATE_KEY;
if (!CONTRACT || !PK) {
  console.error("Set VITE_CONTRACT_ADDRESS and AEGIS_PRIVATE_KEY first.");
  process.exit(1);
}

const REPO_RAW = "https://raw.githubusercontent.com/phu1271997/AegisWatch/main/docs/samples/evidence";
const SCOPE_URL = "https://raw.githubusercontent.com/phu1271997/AegisWatch/main/docs/samples/evidence/report_high_advisory.txt";

// One shared Program: pool = 2_000_000, HIGH=800k, MEDIUM=300k, LOW=50k,
// min_bond=25k. Numbers are in wei-scale but small enough that the whole demo
// stays under ~4 GEN of the funder wallet.
const PROGRAM = {
  pool: 2_000_000n,
  high_payout: 800_000,
  medium_payout: 300_000,
  low_payout: 50_000,
  min_bond: 25_000,
  scope_url: SCOPE_URL,
  scope_summary: "AcmeSwap / NimbusVoting reference scope for AegisWatch demo (mock projects).",
};

const REPORTS = [
  {
    name: "HIGH — signature-replay in AcmeSwap /api/withdraw",
    bond: 25_000n,
    summary:
      "Signature-replay in AcmeSwap /api/withdraw allows the same signed message to drain a fresh vault. Confirmed by two independent researchers and closed in disclosed PR #1834.",
    evidence: [
      { url: `${REPO_RAW}/report_high_advisory.txt`, note: "GHSA advisory" },
      { url: `${REPO_RAW}/report_high_pr.txt`, note: "Disclosed fix PR notes" },
    ],
  },
  {
    name: "MEDIUM — unbounded loop in NimbusVoting.tallyBallots",
    bond: 25_000n,
    summary:
      "NimbusVoting.tallyBallots iterates every ballot unbounded; a 61k-voter proposal exceeds block gas and freezes execution. Confirmed by a Nimbus maintainer in a public forum thread.",
    evidence: [
      { url: `${REPO_RAW}/report_medium_blog.txt`, note: "Researcher writeup + maintainer confirmation" },
    ],
  },
  {
    name: "DEBUNKED — 'AcmeSwap oracle manipulation' with only a self-screenshot",
    bond: 25_000n,
    summary:
      "Claim that the AcmeSwap oracle is being manipulated during reorgs. Only evidence is a cropped self-screenshot already publicly rebutted with reproducible data.",
    evidence: [
      { url: `${REPO_RAW}/report_debunked_screenshot.txt`, note: "Only evidence supplied" },
    ],
  },
];

const funder = createAccount(PK);
const client = createClient({ chain: studionet, account: funder });
console.log("Funder / sponsor:", funder.address);
console.log("Contract:        ", CONTRACT);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function rpc(label, fn, maxRetries = 30) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (e) {
      const msg = String(e?.details || e?.cause?.message || e?.message || e);
      const retryAfter = e?.cause?.data?.retry_after_seconds;
      if (/rate limit/i.test(msg)) {
        const wait = ((retryAfter ?? 5) + 3) * 1000;
        console.log(`     ${label} rate-limited, waiting ${wait / 1000}s (retry ${attempt + 1}/${maxRetries})…`);
        await sleep(wait);
        continue;
      }
      throw e;
    }
  }
  throw new Error(`Gave up on ${label} after rate-limit retries`);
}

async function readTotals() {
  const raw = await rpc("get_totals", () =>
    client.readContract({ address: CONTRACT, functionName: "get_totals", args: [] })
  );
  return typeof raw === "string" ? JSON.parse(raw) : raw;
}

async function readReport(id) {
  try {
    const raw = await rpc(`get_report(${id})`, () =>
      client.readContract({ address: CONTRACT, functionName: "get_report", args: [id] })
    );
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch (e) {
    const msg = (e?.message || "") + " " + JSON.stringify(e?.cause?.data?.receipt?.genvm_result || {});
    if (/not found|does not exist/i.test(msg)) return null;
    throw e;
  }
}

async function writeAndWait(label, fn, args, value = 0n) {
  console.log(`     tx ${label}…`);
  const hash = await rpc(`write ${label}`, () =>
    client.writeContract({ address: CONTRACT, functionName: fn, args, value })
  );
  console.log(`     hash: ${hash}`);
  await rpc(`wait ${label}`, () =>
    client.waitForTransactionReceipt({
      hash, status: "FINALIZED", retries: 60, interval: 10000,
    })
  );
  await sleep(4000);
  return hash;
}

// 1. Ensure at least one Program exists.
let totals = await readTotals();
console.log("Initial totals:", totals);

let programId;
if (totals.programs === 0) {
  console.log("\n── Creating Program 0");
  await writeAndWait("create_program", "create_program", [
    PROGRAM.scope_url,
    PROGRAM.scope_summary,
    PROGRAM.high_payout,
    PROGRAM.medium_payout,
    PROGRAM.low_payout,
    PROGRAM.min_bond,
  ], PROGRAM.pool);
  totals = await readTotals();
  programId = totals.programs - 1;
} else {
  programId = 0;
  console.log(`Reusing existing Program #${programId}`);
}

// 2. Submit + convene each report if missing.
const startReports = totals.reports;
for (let i = 0; i < REPORTS.length; i++) {
  const R = REPORTS[i];
  const rid = startReports + i;
  console.log(`\n── Report ${rid} — ${R.name}`);

  let existing = await readReport(rid);
  if (existing && existing.status !== "REPORT_PENDING") {
    if (["REPORT_VERIFIED_HIGH", "REPORT_VERIFIED_MEDIUM", "REPORT_VERIFIED_LOW",
         "REPORT_DEBUNKED", "REPORT_INSUFFICIENT_PROOF", "REPORT_WITHDRAWN"].includes(existing.status)) {
      console.log(`   already ${existing.status} — skipping.`);
      continue;
    }
  }

  if (!existing) {
    const evidenceJson = JSON.stringify(R.evidence);
    await writeAndWait("submit_report", "submit_report",
      [programId, R.summary, evidenceJson], R.bond);
    existing = await readReport(rid);
    if (!existing) {
      await sleep(10000);
      existing = await readReport(rid);
    }
    if (!existing) throw new Error(`Report ${rid} never appeared on chain`);
  }

  if (existing.status === "REPORT_PENDING") {
    console.log("   Convene AI Verifier — 1 to 3 minutes…");
    await writeAndWait("convene_verifier", "convene_verifier", [rid]);
    existing = await readReport(rid);
  }

  console.log(`   status: ${existing.status}`);
  console.log(`   severity: ${existing.severity}  payout: ${existing.payout_amount}  withdrawable: ${existing.withdrawable}`);
  console.log(`   reason:  ${(existing.reason || "").slice(0, 240)}`);
}

console.log(`\nDone. Explorer: https://explorer-studio.genlayer.com/address/${CONTRACT}`);
