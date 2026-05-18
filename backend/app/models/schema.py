from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.enum.enums import StatusSensor


class SensorData(BaseModel):
    sensor_id: str
    vib_rms: float
    temp: float
    rpm: Optional[float] = None
    status: StatusSensor
    timestamp: datetime

class SensorResponse(BaseModel):
    sensor_id: str
    vib_rms: float
    temp: float
    status: StatusSensor
    timestamp: str
    alert_level: int  # 0=OK, 3=CRITICO

class VibrationAlert(BaseModel):
    sensor_id: str
    message: str
    severity: int
    timestamp: datetime