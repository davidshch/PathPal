"""PathPal API - FastAPI application entry point."""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from .auth.handlers import router as auth_router
from .database.connection import init_db
from .features.alerts.handlers import router as alerts_router
from .features.trips.handlers import router as trips_router
from .features.websockets.handlers import router as websockets_router
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, read=30.0),  # 10s connect, 30s read
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    yield
    # Shutdown
    await app.state.http_client.aclose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Social Safety Navigation App",
    lifespan=lifespan,
)

# Include routers
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(trips_router)
app.include_router(websockets_router)


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "PathPal API is running", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.PROJECT_NAME, "version": settings.VERSION}
