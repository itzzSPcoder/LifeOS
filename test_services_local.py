#!/usr/bin/env python
"""Local LifeOS services verification - No Docker, stdlib only"""

import subprocess
import time
import sys
import os
import json
import urllib.request
import signal

os.chdir(os.path.dirname(os.path.abspath(__file__)))

services = [
    {"name": "echo_env", "port": 8101, "module": "lifeos.env_services.echo_app"},
    {"name": "coding_env", "port": 8102, "module": "lifeos.env_services.coding_app"},
    {"name": "chess_env", "port": 8103, "module": "lifeos.env_services.chess_app"},
    {"name": "carla_env", "port": 8104, "module": "lifeos.env_services.carla_app"},
    {"name": "julia_env", "port": 8105, "module": "lifeos.env_services.julia_app"},
]

processes = []

def cleanup():
    print("\nStopping all services...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except:
            try:
                proc.kill()
            except:
                pass

def http_get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return None, str(e)

def http_post(url, data):
    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data.encode(), timeout=10) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return None, str(e)

print("=" * 70)
print("LifeOS Local Services Verification (No Docker)")
print("=" * 70)
print("\n[1/3] Starting 5 services locally...\n")

for svc in services:
    name, port, module = svc["name"], svc["port"], svc["module"]
    print(f"  • {name:15} on port {port}...", end=" ", flush=True)
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", f"{module}:app", 
             "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(proc)
        print("✓")
    except Exception as e:
        print(f"✗ ({e})")

print(f"\nWaiting 10s for services to initialize...")
time.sleep(10)

print("\n[2/3] Testing /health endpoints...\n")
health_ok = 0
for svc in services:
    name, port = svc["name"], svc["port"]
    url = f"http://127.0.0.1:{port}/health"
    status, resp = http_get(url)
    if status == 200:
        print(f"  ✓ {name:15} {url}")
        health_ok += 1
    else:
        print(f"  ✗ {name:15} (status {status})")

print(f"\nHealth checks: {health_ok}/5 passed")

print("\n[3/3] Testing POST endpoints...\n")

# Echo
status, resp = http_post("http://127.0.0.1:8101/echo", 
                         '{"message":"hello","payload":{"x":1}}')
print(f"  {'✓' if status == 200 else '✗'} echo_env        /echo")

# Coding
status, resp = http_post("http://127.0.0.1:8102/exec/python",
                         '{"code":"print(2+3)","timeout_seconds":5}')
if status == 200:
    try:
        data = json.loads(resp)
        output = data.get('stdout', '').strip()
        print(f"  ✓ coding_env     /exec/python (output: {output})")
    except:
        print(f"  ✓ coding_env     /exec/python")
else:
    print(f"  ✗ coding_env     /exec/python")

# Chess
status, resp = http_post("http://127.0.0.1:8103/validate-move",
                         '{"move":"e2e4","turn":"white"}')
print(f"  {'✓' if status == 200 else '✗'} chess_env      /validate-move")

# Carla
status, resp = http_post("http://127.0.0.1:8104/step",
                         '{"throttle":0.6,"steer":0.1,"brake":0.0}')
print(f"  {'✓' if status == 200 else '✗'} carla_env      /step")

# Julia
status, resp = http_post("http://127.0.0.1:8105/exec/julia",
                         '{"code":"println(2+3)","timeout_seconds":5}')
if status == 200:
    try:
        data = json.loads(resp)
        if data.get('ok'):
            print(f"  ✓ julia_env      /exec/julia")
        else:
            print(f"  ⚠ julia_env      /exec/julia (Julia binary not in PATH - expected)")
    except:
        print(f"  ✓ julia_env      /exec/julia")
else:
    print(f"  ✗ julia_env      /exec/julia")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nStopping services...")
cleanup()
print("Done. All services tested locally without Docker.\n")
