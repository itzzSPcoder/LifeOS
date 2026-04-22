from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import sys

app = FastAPI(title="Coding Environment")

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
    return {"status": "ok", "env": "coding_env"}

@app.post("/exec/python")
def exec_python(req: ExecRequest):
    try:
        result = subprocess.run(
            [sys.executable, "-c", req.code],
            capture_output=True,
            timeout=req.timeout_seconds,
            text=True
        )
        return ExecutionResult(
            ok=result.returncode == 0,
            language="python",
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=f"python -c {req.code[:30]}..."
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            ok=False,
            language="python",
            exit_code=-1,
            stdout="",
            stderr=f"Timeout after {req.timeout_seconds}s",
            command=req.code[:50]
        )
    except Exception as e:
        return ExecutionResult(
            ok=False,
            language="python",
            exit_code=-1,
            stdout="",
            stderr=str(e),
            command=req.code[:50]
        )
