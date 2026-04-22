from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI(title="Chess Environment")

class ChessMove(BaseModel):
    move: str  # UCI format: e2e4, d7d8q, etc.
    turn: str = "white"

@app.get("/health")
def health():
    return {"status": "ok", "env": "chess_env"}

@app.post("/validate-move")
def validate_move(move_req: ChessMove):
    # UCI move format: source_file + source_rank + dest_file + dest_rank + promotion
    pattern = r"^[a-h][1-8][a-h][1-8][qrbn]?$"
    is_valid = bool(re.match(pattern, move_req.move))
    return {
        "move": move_req.move,
        "valid": is_valid,
        "turn": move_req.turn,
        "env": "chess_env"
    }
