#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo ""
echo " ========================================"
echo "  JobMind Match — Premium Job Console"
echo " ========================================"
echo ""

if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 not found. Install Python 3.11+ first."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
fi

echo "[2/4] Activating environment..."
source .venv/bin/activate

echo "[3/4] Installing dependencies..."
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
  echo "[INFO] Creating .env from template..."
  cp .env.example .env
fi

echo "[4/4] Starting JobMind Match..."
echo ""
echo " Dashboard: http://127.0.0.1:8000/dashboard"
echo " Press Ctrl+C to stop the server."
echo ""

if command -v xdg-open &>/dev/null; then
  (sleep 2 && xdg-open "http://127.0.0.1:8000/dashboard") &
elif command -v open &>/dev/null; then
  (sleep 2 && open "http://127.0.0.1:8000/dashboard") &
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000
