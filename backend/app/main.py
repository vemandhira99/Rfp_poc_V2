import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, health, private_chat, private_generation, rfp, uploads, usage
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(uploads.router)
app.include_router(rfp.router)
app.include_router(private_chat.router)
app.include_router(private_generation.router)
app.include_router(audit.router)
app.include_router(usage.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("%s backend started in %s mode. No external AI APIs are configured.", settings.APP_NAME, settings.AI_MODE)
