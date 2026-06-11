#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV="$BACKEND_DIR/.venv"

cleanup() {
  echo ""
  echo "Stopping all services..."
  kill $UVICORN_PID $VITE_PID $CELERY_WORKER_PID $CELERY_BEAT_PID 2>/dev/null
  wait
  echo "All services stopped."
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
source "$VENV/bin/activate"
export $(grep -v "^#" "$ROOT_DIR/.env" | xargs)

echo "Starting Redis..."
redis-server --daemonize no --bind 127.0.0.1 --port 6379 &
REDIS_PID=$!

echo "Starting uvicorn (hot-reload)..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

echo "Starting celery worker..."
celery -A app.core.celery_app.celery_app worker --loglevel=info &
CELERY_WORKER_PID=$!

echo "Starting celery beat..."
celery -A app.core.celery_app.celery_app beat --loglevel=info &
CELERY_BEAT_PID=$!

cd "$FRONTEND_DIR"
echo "Starting vite dev server..."
npm run dev &
VITE_PID=$!

echo ""
echo "All services started:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:8080"
echo "  API:      http://localhost:8000/api/v1/health"
echo ""
echo "Press Ctrl+C to stop all services."

wait
