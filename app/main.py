import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.store.router import router as store_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.services.store_sheets.repository import sheet_loop_enabled
from app.services.store_sheets.sync import sheet_sync_loop


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    task = asyncio.create_task(sheet_sync_loop()) if sheet_loop_enabled() else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    lifespan=_lifespan,
    title=settings.APP_NAME,
    description=(
        "O'zbekiston bo'yicha yuk tashish (logistika) platformasi uchun backend API. "
        "Interaktiv hujjat va sinov uchun /docs sahifasidan foydalaning."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(store_router, prefix="/api/store")


@app.get("/health", tags=["Health"], summary="Server ishlab turganini tekshirish")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/", tags=["Health"], summary="Bosh sahifa")
async def root() -> dict:
    return {
        "message": "Yuk Tashish Platformasi API ishlayapti.",
        "docs": "/docs",
    }
