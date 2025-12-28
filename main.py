from forge.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    from src.config import settings
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
