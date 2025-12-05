#!/usr/bin/env bash
set -e

# Navigate to project root (script → parent → root)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[RUN] Starting node 5"
python3 -m src.node --id 5
