import asyncio
import json
from datetime import datetime
from typing import Dict, Optional
from collections import deque
from app.db.sqlite import sqlite_storage
from app.enum.enums import StatusSensor
from app.core.config import settings
from app.log.logger import log
from app.services.mpu_data_generator import MPU6050DataGenerator


class VibrationService:
    def __init__(self):
        # NOVO: Usa o gerador MPU6050
        self.mpu_generator = MPU6050DataGenerator(duration=60)  # usa o valor padrão do gerador        
        # Inicializa múltiplos sensores simulando máquinas diferentes
        machine_sensors = [
            "MOTOR_PRINCIPAL",
            "BOMBA_HIDRAULICA", 
            "VENTILADOR_REFRIGERACAO",
            "COMPRESSOR_AR",
            "TRANSMISSAO_CORREIA"
        ]
        
        self.sensores = {}
        for sensor_id in machine_sensors:
            self.sensores[sensor_id] = {
                "sensor_id": sensor_id,
                "vib_rms": 0.5,
                "temp": 42.0,
                "status": StatusSensor.OK,
                "timestamp": datetime.now(),
                "history": deque(maxlen=30),
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "label": "normal",
            }

        self.websocket_clients = []
        self.simulation_enabled = False
        self.stream_task = None

    async def simular_dados(self):
        """Simula dados usando o gerador MPU6050"""
        
        # Gera/ Carrega o CSV
        self.mpu_generator.generate_csv()
        
        #Streaming de dados
        async for sensor_data in self.mpu_generator.stream_data():
            if not self.simulation_enabled:
                await asyncio.sleep(0.5)
                continue
            
            # Atualiza o sensor com os dados reais
            sensor_id = sensor_data["sensor_id"]
            
            if sensor_id not in self.sensores:
                # Cria dinamicamente se não existir
                self.sensores[sensor_id] = {
                    "sensor_id": sensor_id,
                    "vib_rms": sensor_data["vibracao"] / 100,  # Converte de mm/s para g
                    "temp": sensor_data["temperatura"],
                    "energia": sensor_data.get("energia", 0.0),
                    "status": StatusSensor[sensor_data["status"]] if sensor_data["status"] in StatusSensor.__members__ else StatusSensor.OK,
                    "timestamp": datetime.fromisoformat(sensor_data["timestamp"]) if isinstance(sensor_data["timestamp"], str) else sensor_data["timestamp"],
                    "history": deque(maxlen=30),
                    "is_anomaly": sensor_data["is_anomaly"],
                    "anomaly_score": sensor_data["anomaly_score"],
                    "label": sensor_data["label"],
                }
            else:
                # Atualiza sensor existente
                self.sensores[sensor_id]["vib_rms"] = sensor_data["vibracao"] / 100
                self.sensores[sensor_id]["temp"] = sensor_data["temperatura"]
                self.sensores[sensor_id]["energia"] = sensor_data.get("energia", self.sensores[sensor_id].get("energia", 0.0))
                self.sensores[sensor_id]["status"] = StatusSensor[sensor_data["status"]] if sensor_data["status"] in StatusSensor.__members__ else StatusSensor.OK
                self.sensores[sensor_id]["timestamp"] = datetime.fromisoformat(sensor_data["timestamp"]) if isinstance(sensor_data["timestamp"], str) else sensor_data["timestamp"]
                self.sensores[sensor_id]["is_anomaly"] = sensor_data["is_anomaly"]
                self.sensores[sensor_id]["anomaly_score"] = sensor_data["anomaly_score"]
                self.sensores[sensor_id]["label"] = sensor_data["label"]
            
            # Adiciona ao histórico
            self.sensores[sensor_id]["history"].append([
                self.sensores[sensor_id]["vib_rms"],
                self.sensores[sensor_id]["temp"]
            ])
            
            log.info(f'Dados MPU6050: {sensor_id} - Vibração: {sensor_data["vibracao"]:.2f} mm/s, '
                    f'Temperatura: {sensor_data["temperatura"]:.1f}°C, Status: {sensor_data["status"]}')
            
            # Notifica clientes WebSocket
            await self.notify_clients()
    
    async def notify_clients(self):
        """Notifica clientes WebSocket com dados formatados"""
        sensores_list = self.get_all_sensors()
        
        if sensores_list:
            sensor_principal = sensores_list[0]
            sensor_obj = self.sensores[sensor_principal["sensor_id"]]
            
            dados_frontend = {
                "vibracao": round(sensor_principal["vib_rms"] * 100, 2),
                "temperatura": sensor_principal["temp"],
                "energia": sensor_obj.get("energia", 0.0),
                "sensor_id": sensor_principal["sensor_id"],
                "status": sensor_principal["status"],
                "label": sensor_obj.get("label", "normal"),
                "fault_type": sensor_obj.get("label", "normal"),
                "risk_pct": int(sensor_obj.get("anomaly_score", 0) * 100),
                "is_anomaly": sensor_obj.get("is_anomaly", False),
                "anomaly_score": sensor_obj.get("anomaly_score", 0),
                "timestamp": sensor_principal["timestamp"],
                "events": [
                    {
                        "id": f"evt_{sensor_principal['sensor_id']}",
                        "level": "danger" if sensor_principal["status"] == "CRITICO" else "warn",
                        "title": f"{sensor_principal['status']}",
                        "desc": f"Vibração: {round(sensor_principal['vib_rms'] * 100, 2)} mm/s",
                        "timestamp": sensor_principal["timestamp"]
                    }
                ] if sensor_principal["status"] in ["ALERTA", "CRITICO"] else []
            }
            
            for client in list(self.websocket_clients):
                try:
                    await client.send_text(json.dumps(dados_frontend, default=str))
                except:
                    if client in self.websocket_clients:
                        self.websocket_clients.remove(client)
    
    async def enable_simulation(self):
        """Habilita a simulação"""
        self.simulation_enabled = True
        log.info("Simulação MPU6050 habilitada")
        await self.notify_clients()
    
    def get_sensor(self, sensor_id: str):
        """Retorna dados de um sensor específico"""
        if sensor_id not in self.sensores:
            raise ValueError(f"Sensor {sensor_id} não encontrado")
        
        sensor = self.sensores[sensor_id]
        
        return {
            "sensor_id": sensor["sensor_id"],
            "vib_rms": sensor["vib_rms"],
            "temp": sensor["temp"],
            "status": sensor["status"].value if hasattr(sensor["status"], 'value') else sensor["status"],
            "timestamp": sensor["timestamp"].isoformat(),
            "alert_level": list(StatusSensor).index(sensor["status"]) if hasattr(sensor["status"], 'value') else 0
        }
    
    def get_all_sensors(self):
        """Retorna todos os sensores"""
        return [self.get_sensor(sensor_id) for sensor_id in self.sensores.keys()]
    
    def check_alerts(self):
        """Verifica alertas ativos"""
        alerts = []
        
        for sensor_id, sensor in self.sensores.items():
            status_value = sensor["status"].value if hasattr(sensor["status"], 'value') else sensor["status"]
            if status_value in ["ALERTA", "CRITICO"]:
                alerts.append({
                    "sensor_id": sensor_id,
                    "message": f"{status_value}: Vib={sensor['vib_rms']:.2f}g",
                    "severity": 3 if status_value == "CRITICO" else 2,
                    "timestamp": sensor["timestamp"]
                })
        
        return alerts

    def get_sqlite_records(self, limit: int = 100, sensor_id: Optional[str] = None):
        """Retorna registros do banco SQLite gerado pelo MPD generator"""
        return sqlite_storage.query_sensor_records(limit=limit, sensor_id=sensor_id)


# Instância global
vibration = VibrationService()