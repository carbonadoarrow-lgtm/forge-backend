from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import forge, orunmila, chat, console, console_chat, orunmila_events, autobuilder, coding_lane, cockpit, leto_authority

app = FastAPI(
    title="Forge Console API",
    description="Backend API for Forge Console - Infrastructure and runtime management",
    version="1.0.0",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(forge.router, prefix=settings.api_prefix)
app.include_router(orunmila.router, prefix=settings.api_prefix)
app.include_router(orunmila_events.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(console.router, prefix=settings.api_prefix)
app.include_router(console_chat.router, prefix=settings.api_prefix)
app.include_router(autobuilder.router, prefix=settings.api_prefix)
app.include_router(coding_lane.router, prefix=settings.api_prefix)
app.include_router(cockpit.router, prefix=settings.api_prefix)
app.include_router(leto_authority.router, prefix=settings.api_prefix)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "Forge Console API",
        "version": "1.0.0",
        "status": "operational",
        "mode": settings.backend_mode,
    }


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    """Readiness check endpoint."""
    # In production, check connectivity to backends here
    return {
        "status": "ready",
        "backend_mode": settings.backend_mode,
    }
