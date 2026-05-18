import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

from app.db.sqlite import sqlite_storage
from app.enum.enums import StatusSensor
from app.core.config import settings
from app.log.logger import log
from app.ia.ia import ia


class VibrationService:
    """
    Serviço de recebimento de dados reais do ESP32.
    Não há simulação — os dados chegam via POST /receber ou WebSocket.
    O Isolation Forest classifica cada leitura em: Normal | Alerta | Crítico.
    """

    def __init__(self):
        self.sensores: Dict[str, Dict] = {}
        self.websocket_clients: List = []
        # Histórico persistente de eventos Alerta/Crítico (não some ao reconectar)
        self.event_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Recebimento de dados do ESP32
    # ------------------------------------------------------------------

    async def process_reading(self, dados: Dict) -> Dict:
        """
        Processa uma leitura vinda do ESP32.
        Retorna o dict formatado que foi enviado aos clientes WS.
        """
        sensor_id  = str(dados.get("id",   dados.get("sensor_id", "ESP32")))
        vib_rms    = float(dados.get("vib", dados.get("vib_rms",    0)) or 0)
        temp       = float(dados.get("temp", dados.get("temperatura", 25)) or 25)
        acc_x      = float(dados.get("acc_x",  0) or 0)
        acc_y      = float(dados.get("acc_y",  0) or 0)
        acc_z      = float(dados.get("acc_z",  1) or 1)
        gyro_x     = float(dados.get("gyro_x", 0) or 0)
        gyro_y     = float(dados.get("gyro_y", 0) or 0)
        gyro_z     = float(dados.get("gyro_z", 0) or 0)
        now        = datetime.now()

        # --- Classifica com Isolation Forest ---
        ai_result = ia.predict({
            "sensor_id": sensor_id,
            "vib_rms": vib_rms,
            "temp": temp,
            "acc_x": acc_x,
            "acc_y": acc_y,
            "acc_z": acc_z,
            "gyro_x": gyro_x,
            "gyro_y": gyro_y,
        })

        label         = ai_result["label"]          # "Normal" | "Alerta" | "Crítico"
        anomaly_score = ai_result["anomaly_score"]
        is_anomaly    = ai_result["is_anomaly"]

        # --- Determina StatusSensor compatível com enum ---
        status = self._label_to_status(label)

        # --- Atualiza / cria entrada do sensor ---
        if sensor_id not in self.sensores:
            self.sensores[sensor_id] = {
                "sensor_id": sensor_id,
                "history": deque(maxlen=60),
            }

        sensor = self.sensores[sensor_id]
        sensor.update({
            "vib_rms":      vib_rms,
            "temp":         temp,
            "acc_x":        acc_x,
            "acc_y":        acc_y,
            "acc_z":        acc_z,
            "gyro_x":       gyro_x,
            "gyro_y":       gyro_y,
            "gyro_z":       gyro_z,
            "status":       status,
            "label":        label,
            "anomaly_score": anomaly_score,
            "is_anomaly":   is_anomaly,
            "timestamp":    now,
        })
        sensor["history"].append([vib_rms, temp])

        # --- Persiste no SQLite ---
        sqlite_storage.insert_sensor_record({
            "sensor_id":     sensor_id,
            "timestamp":     now.isoformat(),
            "acc_x":         acc_x,
            "acc_y":         acc_y,
            "acc_z":         acc_z,
            "gyro_x":        gyro_x,
            "gyro_y":        gyro_y,
            "gyro_z":        gyro_z,
            "vibration_rms": vib_rms,
            "energia":       round(vib_rms ** 2, 4),
            "temp":          temp,
            "status":        status.value,
            "is_anomaly":    int(is_anomaly),
            "anomaly_score": anomaly_score,
            "label":         label,
        })

        # --- Registra evento persistente se for Alerta ou Crítico ---
        if is_anomaly:
            event = {
                "id":        f"evt_{sensor_id}_{int(now.timestamp())}",
                "sensor_id": sensor_id,
                "level":     "danger" if label == "Crítico" else "warn",
                "label":     label,
                "title":     f"{label} — {sensor_id}",
                "desc":      f"Vibração: {vib_rms:.3f} g | Temp: {temp:.1f}°C | Score: {anomaly_score*100:.1f}%",
                "timestamp": now.isoformat(),
            }
            self.event_log.append(event)
            if len(self.event_log) > 500:
                self.event_log = self.event_log[-500:]

        log.info(f"[{sensor_id}] vib={vib_rms:.3f}g temp={temp:.1f}°C → {label} (score={anomaly_score:.3f})")

        # --- Monta payload para WebSocket ---
        ws_payload = {
            "sensor_id":    sensor_id,
            "vibracao":     round(vib_rms, 4),
            "temperatura":  round(temp, 2),
            "energia":      round(vib_rms ** 2, 4),
            "status":       status.value,
            "label":        label,
            "fault_type":   label,
            "risk_pct":     int(anomaly_score * 100),
            "is_anomaly":   is_anomaly,
            "anomaly_score": anomaly_score,
            "timestamp":    now.isoformat(),
            # Apenas o evento mais recente — frontend acumula o histórico
            "events": [event] if is_anomaly else [],
        }

        await self.notify_clients(ws_payload)
        return ws_payload

    # ------------------------------------------------------------------
    # Treinamento online do modelo IA
    # ------------------------------------------------------------------

    def train_ia_from_sqlite(self, limit: int = 500):
        """Treina o Isolation Forest com os dados já salvos no SQLite."""
        import pandas as pd
        records = sqlite_storage.query_sensor_records(limit=limit)
        if not records:
            log.warning("Sem registros no SQLite para treinar o modelo IA.")
            return
        df = pd.DataFrame(records)
        ia.train_from_df(df)

    # ------------------------------------------------------------------
    # Notificação WebSocket
    # ------------------------------------------------------------------

    async def notify_clients(self, payload: Dict):
        dead = []
        for client in list(self.websocket_clients):
            try:
                await client.send_text(json.dumps(payload, default=str))
            except Exception:
                dead.append(client)
        for c in dead:
            if c in self.websocket_clients:
                self.websocket_clients.remove(c)

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    def _label_to_status(self, label: str) -> StatusSensor:
        mapping = {
            "Normal":   StatusSensor.OK,
            "Alerta":   StatusSensor.ALERTA,
            "Crítico":  StatusSensor.CRITICO,
        }
        return mapping.get(label, StatusSensor.OK)

    def get_sensor(self, sensor_id: str) -> Dict:
        if sensor_id not in self.sensores:
            raise ValueError(f"Sensor {sensor_id} não encontrado")
        s = self.sensores[sensor_id]
        return {
            "sensor_id":    s["sensor_id"],
            "vib_rms":      s.get("vib_rms", 0.0),
            "temp":         s.get("temp", 0.0),
            "status":       s["status"].value if hasattr(s.get("status"), "value") else "OK",
            "label":        s.get("label", "Normal"),
            "anomaly_score": s.get("anomaly_score", 0.0),
            "is_anomaly":   s.get("is_anomaly", False),
            "timestamp":    s["timestamp"].isoformat() if isinstance(s.get("timestamp"), datetime) else str(s.get("timestamp", "")),
            "alert_level":  list(StatusSensor).index(s["status"]) if hasattr(s.get("status"), "value") else 0,
        }

    def get_all_sensors(self) -> List[Dict]:
        return [self.get_sensor(sid) for sid in self.sensores]

    def check_alerts(self) -> List[Dict]:
        alerts = []
        for sensor_id, s in self.sensores.items():
            label = s.get("label", "Normal")
            if label in ("Alerta", "Crítico"):
                alerts.append({
                    "sensor_id":    sensor_id,
                    "message":      f"{label}: Vib={s.get('vib_rms', 0):.3f}g",
                    "severity":     3 if label == "Crítico" else 2,
                    "timestamp":    s.get("timestamp", datetime.now()),
                })
        return alerts

    def get_sqlite_records(self, limit: int = 100, sensor_id: Optional[str] = None) -> List[Dict]:
        return sqlite_storage.query_sensor_records(limit=limit, sensor_id=sensor_id)

    def get_event_log(self, limit: int = 100) -> List[Dict]:
        """Retorna histórico persistente de eventos Alerta/Crítico (mais recente primeiro)."""
        return list(reversed(self.event_log[-limit:]))


vibration = VibrationService()
