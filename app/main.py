from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.payments import router as payments_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app import models  # noqa: F401 -- registers SQLAlchemy models


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Good for this starter. Replace with Alembic migrations before production.
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="KHQR payment microservice for the Hotel Booking System",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(payments_router)

