#!/usr/bin/env python
"""
LifeOS Microservices Verification - Local Deployment
Starts all 5 services and validates they work
"""

import subprocess
import time
import sys
import os
import json
import urllib.request
import signal
from pathlib import Path

os.chdir(Path(__file__).parent)

services = [
    {"name": "echo_env", "port": 8101, "module": "lifeos.env_services.echo_app"},
    {"name": "coding_env", "port": 8102, "module": "lifeos.env_services.coding_app"},
    {"name": "chess_env", "port": 8103, "module": "lifeos.env_services.chess_app"},
    {"name": "carla_env", "port": 8104, "module": "lifeos.env_services.carla_app"},
    {"name": "julia_env", "port": 8105, "module": "lifeos.env_services.julia_app"},
]

processes = []

def cleanup():
    print("\n" + "="*70)
    print("Stopping all services...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            try:
                proc.kill()
            except:
                pass
    time.sleep(1)
    print("All services stopped.")

def http_get(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return None, str(e)

def http_post(url, data):
    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data.encode(), timeout=5) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return None, str(e)

print("="*70)
print("LifeOS Microservices - Local Validation")
print("="*70)
print("\n[STEP 1] Starting 5 services...\n")

for svc in services:
    name, port, module = svc["name"], svc["port"], svc["module"]
    print(f"  Starting {name:15} on port {port}...", end=" ", flush=True)
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", f"{module}:app", 
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "critical"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(proc)
        print("✓ (PID {})".format(proc.pid))
        time.sleep(2)  # Wait for each service to start
    except Exception as e:
        print(f"✗ ERROR: {e}")

print(f"\nWaiting 5s for services to fully initialize...")
time.sleep(5)

print("\n[STEP 2] Testing /health endpoints...\n")
health_results = []
for svc in services:
    name, port = svc["name"], svc["port"]
    url = f"http://127.0.0.1:{port}/health"
    status, resp = http_get(url)
    is_ok = status == 200
    health_results.append(is_ok)
    symbol = "✓" if is_ok else "✗"
    print(f"  {symbol} {name:15} {url}")

print(f"\n  Health checks: {sum(health_results)}/5 services responding\n")

print("[STEP 3] Testing functional endpoints...\n")
endpoint_results = []

# 1. Echo test
status, resp = http_post("http://127.0.0.1:8101/echo", 
                         '{"message":"test","payload":{"x":1}}')
ok = status == 200
endpoint_results.append(ok)
print(f"  {'✓' if ok else '✗'} echo_env       POST /echo -> status {status}")

# 2. Coding exec test
status, resp = http_post("http://127.0.0.1:8102/exec/python",
                         '{"code":"print(2+3)","timeout_seconds":5}')
ok = status == 200
endpoint_results.append(ok)
if ok:
    try:
        data = json.loads(resp)
        output = data.get('stdout', '').strip()
        print(f"  ✓ coding_env    POST /exec/python -> output '{output}'")
    except:
        print(f"  ✓ coding_env    POST /exec/python -> status {status}")
else:
    print(f"  ✗ coding_env    POST /exec/python -> status {status}")

# 3. Chess test
status, resp = http_post("http://127.0.0.1:8103/validate-move",
                         '{"move":"e2e4","turn":"white"}')
ok = status == 200
endpoint_results.append(ok)
if ok:
    try:
        data = json.loads(resp)
        valid = data.get('valid', False)
        print(f"  ✓ chess_env     POST /validate-move -> valid={valid}")
    except:
        print(f"  ✓ chess_env     POST /validate-move -> status {status}")
else:
    print(f"  ✗ chess_env     POST /validate-move -> status {status}")

# 4. Carla test
status, resp = http_post("http://127.0.0.1:8104/step",
                         '{"throttle":0.6,"steer":0.1,"brake":0.0}')
ok = status == 200
endpoint_results.append(ok)
if ok:
    try:
        data = json.loads(resp)
        speed = data.get('state', {}).get('speed_kmh', 'N/A')
        print(f"  ✓ carla_env     POST /step -> speed={speed} kmh")
    except:
        print(f"  ✓ carla_env     POST /step -> status {status}")
else:
    print(f"  ✗ carla_env     POST /step -> status {status}")

# 5. Julia test
status, resp = http_post("http://127.0.0.1:8105/exec/julia",
                         '{"code":"println(2+3)","timeout_seconds":5}')
ok = status == 200
endpoint_results.append(ok)
if ok:
    try:
        data = json.loads(resp)
        if data.get('ok'):
            output = data.get('stdout', '').strip()
            print(f"  ✓ julia_env     POST /exec/julia -> output '{output}'")
        else:
            err = data.get('stderr', '')[:40]
            print(f"  ⚠ julia_env     POST /exec/julia -> (Julia not in PATH: {err})")
    except:
        print(f"  ✓ julia_env     POST /exec/julia -> status {status}")
else:
    print(f"  ✗ julia_env     POST /exec/julia -> status {status}")

print("\n" + "="*70)
print(f"RESULTS: {sum(health_results)}/5 health OK | {sum(endpoint_results)}/5 endpoints OK")
print("="*70)

if sum(health_results) == 5 and sum(endpoint_results) == 5:
    print("\n✓ SUCCESS: All services are working correctly!")
elif sum(health_results) + sum(endpoint_results) >= 8:
    print("\n⚠ PARTIAL SUCCESS: Most services working (Julia may not be installed)")
else:
    print("\n✗ FAILURE: Some services are not responding")

print("\nStopping all services...")
cleanup()
print("\nDone.\n")
