from datetime import datetime
from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketState
from typing import Optional
from app.models import schema
from app.services.vibration import vibration
from app.ia.ia import ia
from app.log.logger import log

router = APIRouter(prefix="", tags=["sensores"])


# ------------------------------------------------------------------
# Recebimento de dados do ESP32
# ------------------------------------------------------------------

@router.post("/receber")
async def receber_dados(dados: dict):
    """
    Endpoint principal — recebe POST do ESP32.
    Formato esperado:
      { "id": "ESP32_01", "vib": 0.12, "temp": 42.5,
        "acc_x": 0.01, "acc_y": 0.02, "acc_z": 1.00,
        "gyro_x": 0.1, "gyro_y": 0.2, "gyro_z": 0.0 }
    """
    result = await vibration.process_reading(dados)
    return {"status": "ok", "classification": result["label"], "sensor_id": result["sensor_id"]}


# ------------------------------------------------------------------
# Consultas
# ------------------------------------------------------------------

@router.get("/sensores")
async def listar_sensores():
    return {
        "status": "ok",
        "count": len(vibration.get_all_sensors()),
        "data": vibration.get_all_sensors(),
    }


@router.get("/sensores/{sensor_id}", response_model=schema.SensorResponse)
async def get_sensor(sensor_id: str):
    return vibration.get_sensor(sensor_id)


@router.get("/alertas", response_model=list[schema.VibrationAlert])
async def listar_alertas():
    return vibration.check_alerts()


@router.get("/dados/sqlite")
async def listar_registros_sqlite(limit: int = 100, sensor_id: Optional[str] = None):
    registros = vibration.get_sqlite_records(limit=limit, sensor_id=sensor_id)
    return {"status": "ok", "count": len(registros), "data": registros}


@router.get("/eventos")
async def listar_eventos(limit: int = 100):
    """
    Histórico persistente de eventos Alerta/Crítico.
    Não some ao reconectar — fica em memória durante a sessão do servidor.
    """
    eventos = vibration.get_event_log(limit=limit)
    return {"status": "ok", "count": len(eventos), "data": eventos}


@router.get("/anomalias/historico")
async def listar_historico_anomalias(limit: int = 20):
    """Histórico de anomalias detectadas pelo Isolation Forest."""
    anomalias = ia.get_recent_anomalies(limit=limit)
    return {"status": "ok", "count": len(anomalias), "data": anomalias}


@router.post("/ia/treinar")
async def treinar_ia(limit: int = 500):
    """Re-treina o Isolation Forest com os dados do SQLite."""
    vibration.train_ia_from_sqlite(limit=limit)
    return {"status": "ok", "ia_treinada": ia.is_trained}


# ------------------------------------------------------------------
# WebSocket — dados em tempo real
# ------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vibration.websocket_clients.append(websocket)
    log.info(f"WebSocket conectado: {websocket.client}")
    try:
        while True:
            await websocket.receive_text()   # keepalive ping
    except Exception:
        pass
    finally:
        if websocket in vibration.websocket_clients:
            vibration.websocket_clients.remove(websocket)
        log.info(f"WebSocket desconectado: {websocket.client}")
