#!/usr/bin/env bash
# Convenience: pull latest on the remote box so shared/ context stays in sync across machines.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"
git pull --rebase --autostash
echo "Synced. shared/ is the cross-machine source of truth."
