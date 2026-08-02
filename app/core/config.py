from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Streaming Backend"
    VERSION: str = "1.0.0"
    
    LLM_API_BASE: str = ""
    LLM_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
# print(f"Loaded settings: {settings.dict()}")
