#!/bin/bash
# Start the demo app on this machine. Set MODEL_URL to the inference server (demo/inference_server.py on a GPU).
cd "$(dirname "$0")/.."
: "${MODEL_URL:?Set MODEL_URL to the inference server, e.g. MODEL_URL=http://<gpu-host>:<port> demo/run.sh}"
export MODEL_URL
exec uv run -q --no-project --with fastapi --with uvicorn --with httpx python demo/app.py --db demo/demo.db --port 8000
