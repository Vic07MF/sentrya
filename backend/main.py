from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.api.routes import router
from app.core.config import settings
from app.services.vibration import vibration
from datetime import datetime
from app.log.logger import log

app = FastAPI(
    title=settings.app_name,
    description="Sentrya API - Monitoramento Simulado",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # Inicia a tarefa de simulação, aguardando comando do frontend para começar
    
    log.info("🚀 Iniciando Sentrya API...")
    asyncio.create_task(vibration.simular_dados())
    log.info("✅ Simulação de dados pronta para iniciar via endpoint")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "sensores_ativos": len(vibration.sensores)}


@app.post("/receber") 
async def receber_dados_raw(dados: dict):
    
    # Recebe dados brutos do ESP32
    sensor_id = dados.get("id", "DESCONHECIDO")
    vib_rms = float(dados.get("vib", 0))
    temp = float(dados.get("temp", 0))
    
    # Atualiza service
    if sensor_id in vibration.sensores:
        vibration.sensores[sensor_id].vib_rms = vib_rms
        vibration.sensores[sensor_id].temp = temp
        vibration.sensores[sensor_id].timestamp = datetime.now()
    
    print(f"ESP32: {sensor_id} = {vib_rms}g, {temp}°C")
    return {"status": "ok"}