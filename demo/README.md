# Demo

A review app that runs on a laptop:
- **Review queue:** suggestions with confidence badges and safe-to-approve flags; approve one, approve all safe ones, or pick another account.
- **Why each suggestion:** the past transactions the model read, with a trace of model version and latency.
- **Rules and chart of accounts:** add and delete them, and see suggestions update.
- **Monitoring:** suggestion accuracy, top-5 rate, calibration by confidence band, latency.

The model runs separately behind `demo/inference_server.py` on a GPU.

```bash
uv run --no-project python demo/build_db.py                       # demo database from two development organizations
MODEL_URL=http://<gpu-host>:<port> demo/run.sh                    # app at http://localhost:8000
MOCK=1 uv run --no-project --with fastapi --with uvicorn --with httpx python demo/app.py   # without a GPU, for the interface only
```

