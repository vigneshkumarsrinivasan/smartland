#!/usr/bin/env bash
# Start the full test environment: FastAPI backend + Vite frontend dev server
# Usage: bash scripts/start-test-env.sh
# Stop with Ctrl+C — both processes are in the same process group

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[test-env] Seeding backend DB..."
(cd "$ROOT/backend" && python seed.py)

echo "[test-env] Starting FastAPI backend on :8000..."
(cd "$ROOT/backend" && python -m uvicorn main:app --port 8000 --reload) &
BACKEND_PID=$!

echo "[test-env] Starting Vite frontend on :5173..."
(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

echo "[test-env] Both servers started. Backend PID=$BACKEND_PID, Frontend PID=$FRONTEND_PID"
echo "[test-env] Run E2E tests: cd e2e && npx playwright test --reporter=list"
echo "[test-env] Stop with: kill $BACKEND_PID $FRONTEND_PID"

# Keep script alive
wait
