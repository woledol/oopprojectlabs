#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

mkdir -p .runtime

nohup python3 -m predictor_service.app > .runtime/predictor.log 2>&1 &
echo "$!" > .runtime/predictor.pid

nohup python3 -m user_service.app > .runtime/user.log 2>&1 &
echo "$!" > .runtime/user.pid

echo "Сервисы запущены:"
echo "- сайт: http://localhost:8000"
echo "- predictor_service: http://localhost:8001"
echo
echo "Логи:"
echo "- .runtime/user.log"
echo "- .runtime/predictor.log"
