#!/usr/bin/env bash
# Start Nemotron ASR Streaming NIM on the GB10.
set -euo pipefail

IMAGE="${ASR_IMAGE:-nvcr.io/nim/nvidia/nemotron-asr-streaming:latest}"
NAME="${ASR_CONTAINER_NAME:-lifeos-asr}"
HTTP_PORT="${ASR_HTTP_PORT:-8002}"
GRPC_PORT="${ASR_GRPC_PORT:-50053}"
NIM_CACHE="${NIM_CACHE:-/home/dell/.cache/nim}"

KEY="${NGC_API_KEY:-}"
if [ -z "$KEY" ]; then
  KEY="$(python3 - <<'PY'
from pathlib import Path
p=Path.home()/".hermes/.env"
vals={}
if p.exists():
    for raw in p.read_text(errors="replace").splitlines():
        if raw and not raw.lstrip().startswith("#") and "=" in raw:
            k,v=raw.split("=",1)
            vals[k]=v.strip().strip('"').strip("'")
print(vals.get("NGC_API_KEY") or vals.get("NVIDIA_API_KEY") or vals.get("NVIDIA_NGC_API_KEY") or "")
PY
)"
fi

if [ -z "$KEY" ]; then
  echo "Missing NGC_API_KEY/NVIDIA_API_KEY. Put it in ~/.hermes/.env or export NGC_API_KEY." >&2
  exit 2
fi

mkdir -p "$NIM_CACHE"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --restart unless-stopped --runtime=nvidia --gpus all \
  -e NGC_API_KEY="$KEY" \
  -v "$NIM_CACHE:/opt/nim/.cache" \
  -p "${HTTP_PORT}:9000" \
  -p "${GRPC_PORT}:50051" \
  "$IMAGE"

echo "$NAME starting: HTTP http://127.0.0.1:${HTTP_PORT}/v1, gRPC localhost:${GRPC_PORT}"
