from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import sys

app = FastAPI(title="Julia Environment")

class ExecRequest(BaseModel):
    code: str
    timeout_seconds: int = 5

class ExecutionResult(BaseModel):
    ok: bool
    language: str
    exit_code: int
    stdout: str
    stderr: str
    command: str

@app.get("/health")
def health():
    return {"status": "ok", "env": "julia_env"}

@app.post("/exec/julia")
def exec_julia(req: ExecRequest):
    try:
        result = subprocess.run(
            ["julia", "-e", req.code],
            capture_output=True,
            timeout=req.timeout_seconds,
            text=True
        )
        return ExecutionResult(
            ok=result.returncode == 0,
            language="julia",
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=f"julia -e {req.code[:30]}..."
        )
    except FileNotFoundError:
        return ExecutionResult(
            ok=False,
            language="julia",
            exit_code=-1,
            stdout="",
            stderr="julia binary not found in PATH",
            command=req.code[:50]
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            ok=False,
            language="julia",
            exit_code=-1,
            stdout="",
            stderr=f"Timeout after {req.timeout_seconds}s",
            command=req.code[:50]
        )
    except Exception as e:
        return ExecutionResult(
            ok=False,
            language="julia",
            exit_code=-1,
            stdout="",
            stderr=str(e),
            command=req.code[:50]
        )
