from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Echo Environment")

class EchoRequest(BaseModel):
    message: str
    payload: dict = {}

@app.get("/health")
def health():
    return {"status": "ok", "env": "echo_env"}

@app.post("/echo")
def echo(req: EchoRequest):
    return {"message": req.message, "payload": req.payload, "env": "echo_env"}
