#!/bin/sh
set -e

# 1. apply DB migrations (idempotent)
alembic upgrade head

# 2. create LangGraph's own checkpoint tables (idempotent)
python -m worker.pipeline.setup_checkpointer

# 3. Arq worker in the background of the same container
#    (free tier has no separate worker; see Step 13 notes)
python -m worker.main &

# 4. API in the foreground; exec makes it PID 1 so it receives stop signals
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"