import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import asyncio
from typing import AsyncGenerator, Dict, Optional
from pathlib import Path
import json
from app.log.logger import log


class MPU6050DataGenerator:
    """Gera dados simulados de MPU6050 e os emite em tempo real"""
    
    def __init__(self, fs: int = 100, duration: int = 60):
        self.fs = fs  # Frequência de amostragem (Hz)
        self.duration = duration  # Duração total da simulação (segundos)
        self.current_index = 0
        self.dataframe = None
        self.simulation_enabled = False
        self.data_path = Path("app/data/mpu_data.csv")
        
    def generate_csv(self, force: bool = False) -> pd.DataFrame:
        """Gera o CSV com dados simulados"""
        if self.dataframe is not None and not force:
            return self.dataframe
            
        n_samples = self.fs * self.duration
        start_time = datetime.now()
        
        timestamps = [
            start_time + timedelta(seconds=i / self.fs)
            for i in range(n_samples)
        ]
        
        t = np.linspace(0, self.duration, n_samples)
        
        # Acelerômetro (g)
        acc_x = 0.02 * np.sin(2 * np.pi * 5 * t) + np.random.normal(0, 0.01, n_samples)
        acc_y = 0.02 * np.sin(2 * np.pi * 7 * t) + np.random.normal(0, 0.01, n_samples)
        acc_z = 1.0 + 0.02 * np.sin(2 * np.pi * 3 * t) + np.random.normal(0, 0.01, n_samples)
        
        # Giroscópio (°/s)
        gyro_x = np.random.normal(0, 0.5, n_samples)
        gyro_y = np.random.normal(0, 0.5, n_samples)
        gyro_z = np.random.normal(0, 0.5, n_samples)
        
        # Falhas: picos aleatórios
        for _ in range(20):
            idx = np.random.randint(0, n_samples)
            acc_x[idx] += np.random.uniform(1, 3)
            acc_y[idx] += np.random.uniform(1, 3)
            acc_z[idx] += np.random.uniform(1, 3)
            gyro_x[idx] += np.random.uniform(50, 150)
            gyro_y[idx] += np.random.uniform(50, 150)
            gyro_z[idx] += np.random.uniform(50, 150)
        
        # Falha contínua
        fault_start = np.random.randint(0, n_samples - 300)
        fault_end = fault_start + 300
        for i in range(fault_start, fault_end):
            acc_x[i] += np.sin(2 * np.pi * 20 * t[i]) * 0.5
            acc_y[i] += np.sin(2 * np.pi * 20 * t[i]) * 0.5
            acc_z[i] += np.sin(2 * np.pi * 20 * t[i]) * 0.5
            gyro_x[i] += np.sin(2 * np.pi * 20 * t[i]) * 20
            gyro_y[i] += np.sin(2 * np.pi * 20 * t[i]) * 20
            gyro_z[i] += np.sin(2 * np.pi * 20 * t[i]) * 20
        
        # RMS da vibração
        vibration_rms = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
        
        df = pd.DataFrame({
            "timestamp": timestamps,
            "acc_x": acc_x,
            "acc_y": acc_y,
            "acc_z": acc_z,
            "gyro_x": gyro_x,
            "gyro_y": gyro_y,
            "gyro_z": gyro_z,
            "vibration_rms": vibration_rms,
        })
        
        # Salvar CSV
        self.data_path.parent.mkdir(exist_ok=True)
        df.to_csv(self.data_path, index=False)
        log.info(f"CSV gerado: {self.data_path}")
        
        self.dataframe = df
        return df
    
    def load_csv(self, csv_path: Optional[str] = None) -> pd.DataFrame:
        """Carrega CSV existente"""
        path = Path(csv_path) if csv_path else self.data_path
        
        if not path.exists():
            log.warning(f"CSV não encontrado: {path}. Gerando novo...")
            return self.generate_csv()
        
        self.dataframe = pd.read_csv(path)
        self.data_path = path
        log.info(f"CSV carregado: {path} com {len(self.dataframe)} amostras")
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
            
            # Formato compatível com o frontend
            sensor_data = {
                "sensor_id": "MPU6050_01",
                "vibracao": round(float(row["vibration_rms"]) * 100, 2),  # Converte para mm/s
                "temperatura": 42.0 + np.random.normal(0, 2),  # Temperatura simulada
                "status": self._get_status(float(row["vibration_rms"])),
                "risk_pct": int(min(100, float(row["vibration_rms"]) * 30)),
                "is_anomaly": float(row["vibration_rms"]) > 1.5,
                "anomaly_score": min(1.0, float(row["vibration_rms"]) / 3.0),
                "timestamp": row["timestamp"],
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
            
            yield sensor_data
            
            self.current_index += 1
            
            # Aguarda o intervalo baseado na frequência de amostragem
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