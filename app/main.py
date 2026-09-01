import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

# Enable CORS for local testing from any origin/port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(payments_router)

# Mount static frontend directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        test_console = os.path.join(frontend_dir, "test-console.html")
        if os.path.exists(test_console):
            return FileResponse(test_console)
        return {"message": "Frontend directory mounted at /frontend"}


