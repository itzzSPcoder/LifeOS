from fastapi import FastAPI

app = FastAPI(title="Echo Environment")

@app.get("/health")
def health():
    return {"status": "ok", "env": "echo_env"}

@app.post("/echo")
def echo(payload: dict):
    return {"received": payload, "env": "echo_env"}
