from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    api_prefix: str = "/api"
    backend_mode: str = "file"  # file | sandbox | prod
    data_dir: str = "data"
    cors_origins: List[str] = ["http://localhost:3000"]
    environment: str = "local"  # local | dev | prod

    class Config:
        env_prefix = "FORGE_"
        env_file = ".env"

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


settings = Settings()
