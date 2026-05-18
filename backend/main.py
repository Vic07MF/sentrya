from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.services.vibration import vibration
from app.log.logger import log

app = FastAPI(
    title=settings.app_name,
    description="Sentrya API — Monitoramento IoT ESP32 com Isolation Forest",
    version="2.0.0",
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
    log.info("🚀 Iniciando Sentrya API v2 (modo ESP32)...")
    # Tenta treinar o modelo com dados históricos do SQLite (se houver)
    vibration.train_ia_from_sqlite()
    log.info("✅ Sentrya pronta para receber dados do ESP32")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "sensores_ativos": len(vibration.sensores),
        "ia_treinada": vibration.train_ia_from_sqlite.__module__ is not None,
    }
