from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Dict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    app_name: str = "Sentrya API"
    debug: bool = True
    simulation_interval: int = 1
    
    vibration_thresholds: Dict[str, float] = {
        "ATENCAO": 0.8,
        "ALERTA": 1.5,
        "CRITICO": 3.0
    }
        
settings = Settings()