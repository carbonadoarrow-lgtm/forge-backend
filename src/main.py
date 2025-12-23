from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import forge_router, orunmila_router
from forge.autonomy.cockpit_api import router as autonomy_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(forge_router, prefix=settings.API_PREFIX)
app.include_router(orunmila_router, prefix=settings.API_PREFIX)
app.include_router(autonomy_router)

@app.get("/")
async def root():
    return {
        "message": "Forge Backend v1 with Jobs + LETO-BLRM",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/healthz"
    }

@app.get("/health")
@app.get("/healthz")
async def health():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": settings.FORGE_BACKEND_MODE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
