import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any
from app.models.schema import SensorData

class VibrationAI:
    def __init__(self):
        # Modelo Isolation Forest (anomalias)
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.is_trained = False
    
    def extract_features(self, sensor: SensorData) -> np.ndarray:
       # Extrai features para IA 
        return np.array([
            sensor.vib_rms,
            sensor.temp,
            sensor.vib_rms ** 2,  # Energia
            abs(sensor.vib_rms - 1.0)  # Desvio normal
        ])
    
    def predict_fault(self, sensor: SensorData) -> Dict[str, Any]:
        # Prediz tipo de falha
        
        features = self.extract_features(sensor)
        
        if not self.is_trained:
            return {"fault_type": "NORMAL", "confidence": 0.95}
        
        prediction = self.model.predict(features.reshape(1, -1))[0]
        return {
            "fault_type": "ANOMALIA" if prediction == -1 else "NORMAL",
            "confidence": 0.92
        }
ia = VibrationAI()