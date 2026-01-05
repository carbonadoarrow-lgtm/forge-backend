from .config import settings
from forge.app import create_app

# Use forge/app.py's create_app() which initializes all V2 state objects
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
