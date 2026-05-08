import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, Optional

import numpy as np
import pandas as pd

from app.db.sqlite import sqlite_storage
from app.log.logger import log
from app.services.mpu_csv_service import MPU6050CSVService


class MPU6050DataGenerator:
    """Gera dados simulados de MPU6050 e os emite em tempo real"""

    def __init__(self, fs: int = 0.5, duration: int = 60):  # 1 dado a cada 2 segundos
        self.fs = fs  # Frequência de amostragem (Hz)
        self.duration = duration  # Duração total da simulação (segundos)
        self.current_index = 0
        self.simulation_enabled = False
        self.csv_service = MPU6050CSVService(fs=self.fs, duration=self.duration)
        self.dataframe = None
        # Múltiplos sensores simulando máquinas diferentes
        self.machine_sensors = [
            "MOTOR_PRINCIPAL",
            "BOMBA_HIDRAULICA", 
            "VENTILADOR_REFRIGERACAO",
            "COMPRESSOR_AR",
            "TRANSMISSAO_CORREIA"
        ]
        self.current_sensor_index = 0

    def _insert_sensor_record(self, record: Dict[str, object]):
        sqlite_storage.insert_sensor_record(record)

    def generate_csv(self, force: bool = False) -> pd.DataFrame:
        """Gera o CSV com dados simulados"""
        self.dataframe = self.csv_service.generate_csv(force=force)
        return self.dataframe

    def load_csv(self, csv_path: Optional[str] = None) -> pd.DataFrame:
        """Carrega CSV existente"""
        self.dataframe = self.csv_service.load_csv(csv_path)
        return self.dataframe

    async def stream_data(self) -> AsyncGenerator[Dict, None]:
        """Streaming de dados em tempo real"""
        if self.dataframe is None:
            self.load_csv()

        self.simulation_enabled = True
        self.current_index = 0

        while self.simulation_enabled:
            if self.current_index >= len(self.dataframe):
                # Reinicia o ciclo
                self.current_index = 0
                log.info("Ciclo de dados reiniciado")

            row = self.dataframe.iloc[self.current_index]

            # Alterna entre diferentes sensores (máquinas)
            sensor_id = self.machine_sensors[self.current_sensor_index % len(self.machine_sensors)]
            self.current_sensor_index += 1

            vibration_rms = float(row["vibration_rms"])
            energia = float(row.get("energia", vibration_rms ** 2))

            # IA determina anomalia em tempo real (não usa label do CSV)
            from app.ia.ia import ia
            sensor_dict = {
                "vib_rms": vibration_rms,
                "temp": 42.0 + np.random.normal(0, 2)
            }
            ai_prediction = ia.predict_fault(sensor_dict)
            
            sensor_data = {
                "sensor_id": sensor_id,
                "vibracao": round(vibration_rms * 50, 2),
                "temperatura": sensor_dict["temp"],
                "energia": round(energia, 4),
                "status": self._get_status(vibration_rms),
                "risk_pct": int(min(100, ai_prediction["anomaly_score"] * 100)),
                "label": ai_prediction["fault_type"],
                "is_anomaly": ai_prediction["fault_type"] == "anomalia",
                "anomaly_score": ai_prediction["anomaly_score"],
                "timestamp": str(row["timestamp"]),
                "accelerometer": {
                    "x": float(row["acc_x"]),
                    "y": float(row["acc_y"]),
                    "z": float(row["acc_z"])
                },
                "gyroscope": {
                    "x": float(row["gyro_x"]),
                    "y": float(row["gyro_y"]),
                    "z": float(row["gyro_z"])
                }
            }

            self._insert_sensor_record({
                "sensor_id": sensor_data["sensor_id"],
                "timestamp": sensor_data["timestamp"],
                "acc_x": sensor_data["accelerometer"]["x"],
                "acc_y": sensor_data["accelerometer"]["y"],
                "acc_z": sensor_data["accelerometer"]["z"],
                "gyro_x": sensor_data["gyroscope"]["x"],
                "gyro_y": sensor_data["gyroscope"]["y"],
                "gyro_z": sensor_data["gyroscope"]["z"],
                "vibration_rms": float(row["vibration_rms"]),
                "energia": sensor_data["energia"],
                "temp": sensor_data["temperatura"],
                "status": sensor_data["status"],
                "is_anomaly": sensor_data["is_anomaly"],
                "anomaly_score": sensor_data["anomaly_score"],
            })

            yield sensor_data

            self.current_index += 1
            await asyncio.sleep(1.0 / self.fs)

    def _get_status(self, vibration_rms: float) -> str:
        """Determina o status baseado na vibração"""
        if vibration_rms > 2.0:
            return "CRITICO"
        elif vibration_rms > 1.2:
            return "ALERTA"
        elif vibration_rms > 0.8:
            return "ATENCAO"
        else:
            return "OK"

    def stop(self):
        """Para o streaming"""
        self.simulation_enabled = False
        log.info("Streaming de dados parado")