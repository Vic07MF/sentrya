from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import Dict, Any
from app.models.schema import SensorData

class VibrationAI:
    def __init__(self):
        # Ajusta contamination para ser mais sensível a anomalias
        self.model = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
        self.is_trained = False
        self.anomaly_history = []  # Mantém histórico de anomalias detectadas

    def extract_features(self, sensor_data: Dict) -> np.ndarray:
        """
        Extrai features para IA - 7 features compatíveis com o modelo
        """
        vibracao = sensor_data.get("vibracao", 0)
        temperatura = sensor_data.get("temperatura", 25)
        acc_x = sensor_data.get("acc_x", 0)
        acc_y = sensor_data.get("acc_y", 0)
        acc_z = sensor_data.get("acc_z", 0)
        gyro_x = sensor_data.get("gyro_x", 0)
        gyro_y = sensor_data.get("gyro_y", 0)

        # Retorna 7 features (ORDEM IMPORTANTE - deve ser a mesma do treinamento)
        return np.array([
            vibracao / 100,           # Vibração normalizada
            temperatura,               # Temperatura
            acc_x,                     # Aceleração X
            acc_y,                     # Aceleração Y
            acc_z,                     # Aceleração Z
            gyro_x,                    # Giroscópio X
            gyro_y,                     # Giroscópio Y
            
        ])
    def build_feature_matrix(self, df: pd.DataFrame) -> np.ndarray:
        features = []
        for _, row in df.iterrows():
            features.append([
                float(row.get("vibration_rms", 0.0)),
                float(row.get("temp", row.get("temperatura", 0.0))),
                float(row.get("vibration_rms", 0.0)) ** 2,
                abs(float(row.get("vibration_rms", 0.0)) - 1.0)
            ])
        return np.asarray(features)

    def train(self, X: np.ndarray):
        if len(X) == 0:
            return
        self.model.fit(X)
        self.is_trained = True

    def label_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if "label" in df.columns and "anomaly_score" in df.columns:
            return df

        features = self.build_feature_matrix(df)
        self.train(features)

        predictions = self.model.predict(features)
        scores = self.model.decision_function(features)
        if len(scores) > 0:
            normalized = 1.0 - ((scores - scores.min()) / (scores.max() - scores.min() + 1e-9))
            anomaly_scores = np.clip(normalized, 0.0, 1.0)
        else:
            anomaly_scores = np.zeros(len(predictions))

        df = df.copy()
        df["anomaly_score"] = anomaly_scores
        df["label"] = np.where(predictions == -1, "anomalia", "normal")
        return df

    def predict_fault(self, sensor: SensorData | dict) -> Dict[str, Any]:
        features = self.extract_features(sensor)

        if not self.is_trained:
            return {"fault_type": "normal", "confidence": 0.95, "anomaly_score": 0.0}

        prediction = self.model.predict(features.reshape(1, -1))[0]
        score = self.model.decision_function(features.reshape(1, -1))[0]
        
        # Normaliza o score para [0, 1] onde 1 é mais anômalo
        anomaly_score = float(np.clip(1.0 - ((score - (-0.5)) / (0.5 - (-0.5))), 0.0, 1.0))
        
        fault_type = "anomalia" if prediction == -1 else "normal"
        confidence = 0.95 if fault_type == "normal" else min(0.99, 0.80 + anomaly_score * 0.15)
        
        # Registra anomalia detectada
        if fault_type == "anomalia":
            anomaly_record = {
                "timestamp": datetime.now().isoformat(),
                "sensor_data": {
                    "vib_rms": float(sensor.vib_rms if hasattr(sensor, "vib_rms") else sensor.get("vib_rms", 0.0)),
                    "temp": float(sensor.temp if hasattr(sensor, "temp") else sensor.get("temp", 0.0))
                },
                "anomaly_score": anomaly_score,
                "confidence": confidence,
                "level": "CRÍTICO" if anomaly_score > 0.8 else "ALTO" if anomaly_score > 0.6 else "MÉDIO"
            }
            self.anomaly_history.append(anomaly_record)
            # Mantém apenas as últimas 50 anomalias
            if len(self.anomaly_history) > 50:
                self.anomaly_history = self.anomaly_history[-50:]

        return {
            "fault_type": fault_type,
            "confidence": confidence,
            "anomaly_score": anomaly_score
        }

    def get_anomaly_history(self) -> list:
        """Retorna o histórico de anomalias detectadas"""
        return self.anomaly_history.copy()

    def get_recent_anomalies(self, limit: int = 10) -> list:
        """Retorna as anomalias mais recentes"""
        return self.anomaly_history[-limit:] if self.anomaly_history else []

ia = VibrationAI()