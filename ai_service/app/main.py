import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import config
from app.services.storage import StorageService
from app.services.vector_store import VectorStoreService
from app.services.llm_client import LLMClient
from app.services.parser import ParserService
from app.services.memory_lock import MemoryLockManager
from app.skills.memory_generator import MemoryGenerator


_services: dict = {}


def get_services() -> dict:
    """Get initialized service instances."""
    return _services


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and clean up services."""
    logger.info("Starting AI Service...")

    log_cfg = config.log
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_cfg.get("level", "DEBUG"),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.add(
        "logs/ai_service_{time:YYYY-MM-DD}.log",
        level=log_cfg.get("level", "DEBUG"),
        rotation=log_cfg.get("rotation", "10MB"),
        retention=log_cfg.get("retention", "7 days"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
    )

    llm_client = LLMClient()
    _services["storage"] = StorageService()
    _services["vector_store"] = VectorStoreService()
    _services["llm_client"] = llm_client
    _services["parser"] = ParserService(llm_client=llm_client)
    _services["memory_generator"] = MemoryGenerator(llm_client=llm_client)
    _services["lock_manager"] = MemoryLockManager()

    logger.info("All services initialized")
    yield

    logger.info("Shutting down AI Service...")


app = FastAPI(
    title="AI Service",
    description="AI Memory Service for parsing, storing, and searching memories",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.memory import router as memory_router
from app.api.chat import router as chat_router
app.include_router(memory_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {"service": "AI Service", "version": "1.0.0"}