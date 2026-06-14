#!/usr/bin/env bash
# Generic entry point — delegates to start_nemotron.sh. Kept as the stable name the docs
# reference; swap the delegate if you serve a different model/engine.
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/start_nemotron.sh"
