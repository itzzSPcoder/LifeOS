# LifeOS - QUICK START GUIDE FOR JUDGES

## ⚡ 30-SECOND DEMO

```bash
# Open terminal in project folder
cd d:\Coding\Projects\LifeOS_VS

# Run the complete validation
python test_all_services.py
```

**Expected:** ✅ All 5 services working + all endpoints functional  
**Time:** ~20 seconds

---

## 🧪 RUN ALL TESTS (2 MINUTES)

```bash
# Run all 20 tests
python -m pytest lifeos/tests/ -v
```

**Expected:** 
```
✅ 20 passed in 2.35s
```

---

## 🔍 TEST INDIVIDUAL SERVICES (30 SECONDS EACH)

### 1. Echo Service
```bash
# Terminal 1: Start service
python -m uvicorn lifeos.env_services.echo_app:app --host 127.0.0.1 --port 8101

# Terminal 2: Test it
curl http://127.0.0.1:8101/health
```

### 2. Coding Service (Python Execution)
```bash
# Terminal 1
python -m uvicorn lifeos.env_services.coding_app:app --host 127.0.0.1 --port 8102

# Terminal 2: Execute Python code
curl -X POST http://127.0.0.1:8102/exec/python \
  -H "Content-Type: application/json" \
  -d '{"code":"print(2+3)","timeout_seconds":5}'

# Returns: {"ok":true,"stdout":"5\n",...}
```

### 3. Chess Service (Move Validation)
```bash
# Terminal 1
python -m uvicorn lifeos.env_services.chess_app:app --host 127.0.0.1 --port 8103

# Terminal 2: Validate move
curl -X POST http://127.0.0.1:8103/validate-move \
  -H "Content-Type: application/json" \
  -d '{"move":"e2e4","turn":"white"}'

# Returns: {"valid":true,...}
```

### 4. CARLA Service (Vehicle Simulation)
```bash
# Terminal 1
python -m uvicorn lifeos.env_services.carla_app:app --host 127.0.0.1 --port 8104

# Terminal 2: Simulate step
curl -X POST http://127.0.0.1:8104/step \
  -H "Content-Type: application/json" \
  -d '{"throttle":0.6,"steer":0.1,"brake":0.0}'

# Returns: {"state":{"speed_kmh":25.2,...}}
```

### 5. Julia Service (Julia Execution)
```bash
# Terminal 1
python -m uvicorn lifeos.env_services.julia_app:app --host 127.0.0.1 --port 8105

# Terminal 2: Execute Julia code (graceful if Julia not installed)
curl -X POST http://127.0.0.1:8105/exec/julia \
  -H "Content-Type: application/json" \
  -d '{"code":"println(2+3)","timeout_seconds":5}'
```

---

## 📊 WHAT YOU'LL SEE

### Test Results Screen
```
✅ COMPLETE TEST REPORT
═══════════════════════════════════════════
Total Tests: 20
All Passed: YES ✅
Time: 2.35 seconds

BREAKDOWN:
✅ API Tests (1/1)
✅ Environment Tests (2/2)
✅ Echo Service Tests (2/2)
✅ Coding Service Tests (4/4)
✅ Chess Service Tests (5/5)
✅ CARLA Service Tests (4/4)
✅ Julia Service Tests (2/2)
```

### Service Validation Screen
```
✓ echo_env        http://127.0.0.1:8101/health
✓ coding_env      http://127.0.0.1:8102/health
✓ chess_env       http://127.0.0.1:8103/health
✓ carla_env       http://127.0.0.1:8104/health
✓ julia_env       http://127.0.0.1:8105/health

Health checks: 5/5 services responding ✅

✓ Echo POST test
✓ Coding exec (output: 5)
✓ Chess validation (e2e4 = valid)
✓ CARLA step (speed=25.2 kmh)
⚠ Julia exec (Julia not in PATH - graceful handling)

RESULTS: 5/5 health OK | 5/5 endpoints OK ✅
```

---

## 🗂️ WHERE TO LOOK FOR CODE

| Component | File | What It Does |
|-----------|------|-------------|
| REST API | `lifeos/api/main.py` | FastAPI endpoints |
| Echo Service | `lifeos/env_services/echo_app.py` | Echo reflection |
| Coding Service | `lifeos/env_services/coding_app.py` | Python execution |
| Chess Service | `lifeos/env_services/chess_app.py` | Chess validation |
| CARLA Service | `lifeos/env_services/carla_app.py` | Vehicle simulation |
| Julia Service | `lifeos/env_services/julia_app.py` | Julia execution |
| Executor | `lifeos/runtime/hybrid_executor.py` | Subprocess safety + timeout |
| Tests | `lifeos/tests/` | 20 comprehensive tests |
| Environment | `lifeos/env/lifeos_env.py` | RL environment |
| Database | `lifeos/db/` | SQLAlchemy ORM |

---

## 📝 DOCUMENTATION FILES

| File | Purpose |
|------|---------|
| `README.md` | Setup + installation |
| `DEMO.md` | Full demonstration guide with examples |
| `FEATURES.md` | Complete feature list |
| `PROJECT_STATUS.md` | Final status report (this submission) |
| `QUICK_START.md` | This file - quick reference |

---

## ✅ VERIFICATION CHECKLIST

- [ ] Can run `python test_all_services.py` successfully
- [ ] All 5 services start without errors
- [ ] Health endpoints respond with status 200
- [ ] Functional endpoints return expected results
- [ ] Tests pass with `pytest`
- [ ] Can execute individual service via curl
- [ ] Coding service executes Python code
- [ ] Chess service validates moves
- [ ] CARLA service simulates vehicle
- [ ] Julia service handles gracefully (even without Julia)

---

## 🚀 DOCKER (Optional)

```bash
# If you have Docker installed
docker compose build
docker compose --profile envs up -d
docker compose ps

# Then test:
curl http://localhost:8102/exec/python -X POST \
  -d '{"code":"print(42)","timeout_seconds":5}' \
  -H "Content-Type: application/json"
```

---

## ❓ FAQ

### Q: What if Python/Julia is not installed?
**A:** Python is required. Julia is optional - service handles missing binary gracefully.

### Q: Do I need Docker?
**A:** No. Docker is optional. All services run locally.

### Q: Why are there 3 runtime modes?
**A:** Flexibility - choose Local (dev), Process (UV package manager), or Container (Docker).

### Q: How do I know all services are working?
**A:** Run `python test_all_services.py` - it starts all 5 and validates them.

### Q: Can I see the test results?
**A:** Yes - run `python -m pytest lifeos/tests/ -v` for detailed output.

### Q: What languages are supported?
**A:** Python (core) + Python execution service + Julia execution service + Chess validation + CARLA simulation.

---

## 🎯 JUDGES: RECOMMENDED ORDER

1. **Start here:** `python test_all_services.py` (20 seconds)
   - Validates all 5 services work
   
2. **Then:** `python -m pytest lifeos/tests/ -v` (3 seconds)
   - Shows all 20 tests pass
   
3. **Then:** Explore code
   - `lifeos/env_services/` - See 5 microservices
   - `lifeos/api/main.py` - See REST API
   - `lifeos/tests/test_microservices.py` - See test coverage
   
4. **Then:** Read documentation
   - `PROJECT_STATUS.md` - Overall summary
   - `FEATURES.md` - What was built
   - `DEMO.md` - Detailed examples

5. **Optional:** Manual curl tests
   - Use examples above to test individual services

---

## 📞 SUPPORT

For any questions, refer to:
- **"How do I run it?"** → `README.md`
- **"What exactly works?"** → `PROJECT_STATUS.md`
- **"Can you show me examples?"** → `DEMO.md`
- **"What features are there?"** → `FEATURES.md`
- **"Quick tests?"** → Commands above in this file

---

**Status:** ✅ Ready for Judges  
**Tested:** ✅ 20/20 tests passing  
**Documented:** ✅ Complete  
**Time to validate:** < 5 minutes  

**Good luck! 🍀**
