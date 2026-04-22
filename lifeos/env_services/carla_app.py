from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="CARLA Environment")

class CarlaStepRequest(BaseModel):
    throttle: float = 0.0  # 0 to 1
    steer: float = 0.0     # -1 to 1
    brake: float = 0.0     # 0 to 1

class VehicleState(BaseModel):
    speed_kmh: float
    lane_offset: float
    heading: float

@app.get("/health")
def health():
    return {"status": "ok", "env": "carla_env"}

@app.post("/step")
def step(req: CarlaStepRequest):
    # Simple mock vehicle dynamics
    speed_kmh = max(0, (req.throttle - req.brake) * 42.0)
    lane_offset = req.steer * 0.35
    heading = 0.0
    
    return {
        "state": VehicleState(
            speed_kmh=speed_kmh,
            lane_offset=lane_offset,
            heading=heading
        ),
        "env": "carla_env"
    }
