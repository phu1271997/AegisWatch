#!/usr/bin/env bash
# Deploy AegisWatch to GenLayer.
#
# The primary target for this project is Studio (studionet) — deploy via the
# Studio UI at https://studio.genlayer.com/run-debug (see README section 5).
# This script exists for the localnet development loop only.
#
# Prerequisites:
#   1. npm install -g genlayer
#   2. genlayer keygen  (or import an existing key)
#
# Recommended order:
#   - Deploy sanity/storage_test.py first to confirm the environment.
#   - Then deploy contracts/aegis_watch.py.

set -euo pipefail

NETWORK="${1:-localnet}"

echo "==> Deploying sanity probe (sanity/storage_test.py)"
genlayer deploy --contract sanity/storage_test.py --network "$NETWORK"

echo ""
echo "==> Sanity OK. Deploying main contract (contracts/aegis_watch.py)"
genlayer deploy --contract contracts/aegis_watch.py --network "$NETWORK"

echo ""
echo "==> Done. Copy the contract address into frontend/src/config.js"
