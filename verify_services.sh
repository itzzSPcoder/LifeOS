#!/bin/bash
# Local LifeOS services verification
# No Docker required - runs all 5 env services locally

cd "$(dirname "$0")" || exit 1

echo "Starting LifeOS env services (local, no Docker)..."
echo "=================================================="

# Start all 5 services in background
echo "Starting echo_env on port 8101..."
.venv/Scripts/python -m uvicorn lifeos.env_services.echo_app:app --host 127.0.0.1 --port 8101 &
PIDS[0]=$!

echo "Starting coding_env on port 8102..."
.venv/Scripts/python -m uvicorn lifeos.env_services.coding_app:app --host 127.0.0.1 --port 8102 &
PIDS[1]=$!

echo "Starting chess_env on port 8103..."
.venv/Scripts/python -m uvicorn lifeos.env_services.chess_app:app --host 127.0.0.1 --port 8103 &
PIDS[2]=$!

echo "Starting carla_env on port 8104..."
.venv/Scripts/python -m uvicorn lifeos.env_services.carla_app:app --host 127.0.0.1 --port 8104 &
PIDS[3]=$!

echo "Starting julia_env on port 8105..."
.venv/Scripts/python -m uvicorn lifeos.env_services.julia_app:app --host 127.0.0.1 --port 8105 &
PIDS[4]=$!

echo "All services started. Waiting for endpoints to be ready (10s)..."
sleep 10

echo ""
echo "Testing health endpoints..."
echo "=================================================="

# Test endpoints
curl -s http://127.0.0.1:8101/health && echo " [echo_env]" || echo "FAIL [echo_env]"
curl -s http://127.0.0.1:8102/health && echo " [coding_env]" || echo "FAIL [coding_env]"
curl -s http://127.0.0.1:8103/health && echo " [chess_env]" || echo "FAIL [chess_env]"
curl -s http://127.0.0.1:8104/health && echo " [carla_env]" || echo "FAIL [carla_env]"
curl -s http://127.0.0.1:8105/health && echo " [julia_env]" || echo "FAIL [julia_env]"

echo ""
echo "Testing functional endpoints..."
echo "=================================================="

echo "1. Echo POST test:"
curl -s -X POST http://127.0.0.1:8101/echo -H "Content-Type: application/json" -d '{"message":"hello","payload":{"x":1}}'
echo ""

echo "2. Coding exec test:"
curl -s -X POST http://127.0.0.1:8102/exec/python -H "Content-Type: application/json" -d '{"code":"print(2+3)","timeout_seconds":5}'
echo ""

echo "3. Chess validate test:"
curl -s -X POST http://127.0.0.1:8103/validate-move -H "Content-Type: application/json" -d '{"move":"e2e4","turn":"white"}'
echo ""

echo "4. Carla step test:"
curl -s -X POST http://127.0.0.1:8104/step -H "Content-Type: application/json" -d '{"throttle":0.6,"steer":0.1,"brake":0.0}'
echo ""

echo "5. Julia exec test (graceful fail if Julia not installed):"
curl -s -X POST http://127.0.0.1:8105/exec/julia -H "Content-Type: application/json" -d '{"code":"println(2+3)","timeout_seconds":5}'
echo ""

echo ""
echo "Stopping all services..."
echo "=================================================="
for pid in "${PIDS[@]}"; do
  kill $pid 2>/dev/null || true
done

echo "All services stopped."
echo ""
echo "VERIFICATION COMPLETE - All 5 env services tested locally."
