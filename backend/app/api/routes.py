from datetime import datetime
from fastapi import APIRouter, WebSocket
from fastapi import BackgroundTasks
from fastapi.websockets import WebSocketState
from typing import Optional
from app.models import schema
from app.services.vibration import vibration
from app.log.logger import log

router = APIRouter(prefix="/api/v1", tags=["sensores"])


@router.get("/sensores", response_model=dict)
async def listar_sensores():
    # Lista todos sensores ativos
    return {
        "status": "ok",
        "count": len(vibration.get_all_sensors()),
        "data": vibration.get_all_sensors()
    }

@router.get("/sensores/{sensor_id}", response_model=schema.SensorResponse)
async def get_sensor(sensor_id: str):
    # Dados de sensor específico
    return vibration.get_sensor(sensor_id)

@router.get("/alertas", response_model=list[schema.VibrationAlert])
async def listar_alertas():
    # Alertas ativos
    return vibration.check_alerts()

@router.post("/simular/iniciar")
async def iniciar_simulacao():
    await vibration.enable_simulation()
    return {"status": "ok", "message": "Simulação iniciada", "started": True}

# WEBSOCKET REAL-TIME
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vibration.websocket_clients.append(websocket)
    
    try:
        while True:
            # Ping/pong keepalive
            await websocket.receive_text()
    except:
        pass
    finally:
        # Remove client morto
        if websocket.client_state == WebSocketState.DISCONNECTED:
            vibration.websocket_clients.remove(websocket)
            
@router.post("/receber")        
async def receber_dados(dados: dict):
    # Recebe dados do ESP32
    sensor_id = dados.get("id", "DESCONHECIDO")
    vib_rms = float(dados.get("vib", 0))
    temp = float(dados.get("temp", 0))
    
    # Atualiza service diretamente
    if sensor_id in vibration.sensores:
        vibration.sensores[sensor_id].vib_rms = vib_rms
        vibration.sensores[sensor_id].temp = temp
        vibration.sensores[sensor_id].timestamp = datetime.now()
    
    log.info(f"Recebido {sensor_id}: {vib_rms}g, {temp}°C")
    return {"status": "ok", "sensor": sensor_id}

@router.get("/dados/sqlite")
async def listar_registros_sqlite(limit: int = 100, sensor_id: Optional[str] = None):
    """Retorna registros de dados armazenados em SQLite."""
    registros = vibration.get_sqlite_records(limit=limit, sensor_id=sensor_id)
    return {
        "status": "ok",
        "count": len(registros),
        "data": registros
    }

@router.get("/anomalias/historico")
async def listar_historico_anomalias(limit: int = 20):
    """Retorna o histórico de anomalias detectadas pela IA."""
    from app.ia.ia import ia
    anomalias = ia.get_recent_anomalies(limit=limit)
    return {
        "status": "ok",
        "count": len(anomalias),
        "data": anomalias
    }

@router.post("/dados/gerar-csv")
async def gerar_novo_csv(background_tasks: BackgroundTasks):
    """Gera um novo arquivo CSV com dados frescos"""
    def regenerar():
        vibration.mpu_generator.generate_csv(force=True)
        vibration.simulation_enabled = False
        vibration.simulation_enabled = True
    
    background_tasks.add_task(regenerar)
    return {"message": "Geração de novo CSV iniciada em background"}
