import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.ia.ia import ia
from app.log.logger import log


class MPU6050CSVService:
    def __init__(self, fs: float = 0.5, duration: int = 60, data_path: str | Path = "app/data/mpu_data.csv"):
        self.fs = fs
        self.duration = duration
        self.dataframe: Optional[pd.DataFrame] = None
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        
    def build_feature_matrix(self, df):
            """
            Constrói matriz de features para o modelo de IA
            """
            import numpy as np

            # Seleciona as colunas numéricas para features
            feature_columns = ['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z', 'vibration_rms']

            # Verifica quais colunas existem no dataframe
            available_cols = [col for col in feature_columns if col in df.columns]

            if not available_cols:
                # Se não encontrar as colunas específicas, usa todas as colunas numéricas
                available_cols = df.select_dtypes(include=[np.number]).columns.tolist()

            # Retorna a matriz de features
            return df[available_cols].values

    def _build_dataframe(self) -> pd.DataFrame:
        n_samples = int(self.fs * self.duration)
        start_time = datetime.now()

        timestamps = [
            start_time + timedelta(seconds=i / self.fs)
            for i in range(n_samples)
        ]

        t = np.linspace(0, self.duration, n_samples)

        acc_x = 0.02 * np.sin(2 * np.pi * 5 * t) + np.random.normal(0, 0.01, n_samples)
        acc_y = 0.02 * np.sin(2 * np.pi * 7 * t) + np.random.normal(0, 0.01, n_samples)
        acc_z = 1.0 + 0.02 * np.sin(2 * np.pi * 3 * t) + np.random.normal(0, 0.01, n_samples)

        gyro_x = np.random.normal(0, 0.5, n_samples)
        gyro_y = np.random.normal(0, 0.5, n_samples)
        gyro_z = np.random.normal(0, 0.5, n_samples)

        for _ in range(20):
            idx = np.random.randint(0, n_samples)
            acc_x[idx] += np.random.uniform(1, 3)
            acc_y[idx] += np.random.uniform(1, 3)
            acc_z[idx] += np.random.uniform(1, 3)
            gyro_x[idx] += np.random.uniform(50, 150)
            gyro_y[idx] += np.random.uniform(50, 150)
            gyro_z[idx] += np.random.uniform(50, 150)

        if n_samples > 300:
            fault_start = np.random.randint(0, n_samples - 300)
            fault_end = fault_start + 300
            for i in range(fault_start, fault_end):
                acc_x[i] += np.sin(2 * np.pi * 20 * t[i]) * 0.5
                acc_y[i] += np.sin(2 * np.pi * 20 * t[i]) * 0.5
                acc_z[i] += np.sin(2 * np.pi * 20 * t[i]) * 0.5
                gyro_x[i] += np.sin(2 * np.pi * 20 * t[i]) * 20
                gyro_y[i] += np.sin(2 * np.pi * 20 * t[i]) * 20
                gyro_z[i] += np.sin(2 * np.pi * 20 * t[i]) * 20

        vibration_rms = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2)

        return pd.DataFrame({
            "timestamp": timestamps,
            "acc_x": acc_x,
            "acc_y": acc_y,
            "acc_z": acc_z,
            "gyro_x": gyro_x,
            "gyro_y": gyro_y,
            "gyro_z": gyro_z,
            "vibration_rms": vibration_rms,
            
        })

    def _label_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        # Remove qualquer label existente e treina o modelo IA sem adicionar labels ao CSV
        if "label" in df.columns:
            df = df.drop(columns=["label"])
        if "anomaly_score" in df.columns:
            df = df.drop(columns=["anomaly_score"])
            
        # Treina o modelo IA com os dados (mas não adiciona labels ao CSV)
        features = self.build_feature_matrix(df)
        ia.train(features)
        log.info(f"Modelo IA treinado com dados do CSV: {self.data_path}")
        return df

    def _save_dataframe(self, df: pd.DataFrame) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.data_path, index=False)

    def generate_csv(self, force: bool = False) -> pd.DataFrame:
        if self.dataframe is not None and not force:
            return self.dataframe

        self.dataframe = self._build_dataframe()
        self.dataframe = self._label_dataframe(self.dataframe)
        self._save_dataframe(self.dataframe)
        log.info(f"CSV gerado: {self.data_path}")
        return self.dataframe

    def load_csv(self, csv_path: Optional[str] = None) -> pd.DataFrame:
        path = Path(csv_path) if csv_path else self.data_path

        if not path.exists():
            log.warning(f"CSV não encontrado: {path}. Gerando novo...")
            return self.generate_csv()

        df = pd.read_csv(path)
        self.dataframe = self._label_dataframe(df)
        self.data_path = path
        log.info(f"CSV carregado: {path} com {len(self.dataframe)} amostras")
        return self.dataframe
