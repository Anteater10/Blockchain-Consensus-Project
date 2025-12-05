#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/data"

echo "[CLEANUP] Resetting blockchain.json and balances.json for all nodes..."
echo "Root directory: $ROOT_DIR"
echo

for i in 1 2 3 4 5; do
    NODE_DIR="$DATA_DIR/P$i"
    BC_FILE="$NODE_DIR/blockchain.json"
    BAL_FILE="$NODE_DIR/balances.json"

    if [[ -d "$NODE_DIR" ]]; then
        echo "[CLEANUP] Processing $NODE_DIR"

        # Remove files if they exist
        rm -f "$BC_FILE" "$BAL_FILE"

        # Optionally recreate minimal empty files
        echo "[]" > "$BC_FILE"
        echo '{"P1":100,"P2":100,"P3":100,"P4":100,"P5":100}' > "$BAL_FILE"

        echo "  - blockchain.json reset"
        echo "  - balances.json reset to default balances"
        echo
    else
        echo "[CLEANUP] Skipping $NODE_DIR (does not exist)"
    fi
done

echo "[CLEANUP] Done!"
