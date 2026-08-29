import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXUS-CI API"
    API_V1_STR: str = "/api"
    
    # Security
    JWT_SECRET: str = Field(default="dev-jwt-secret-key-for-nexus-ci-hackathon-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    
    # PostgreSQL
    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/nexus_ci")
    
    # Neo4j
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USERNAME: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="12345678")
    
    # Files
    UPLOAD_DIR: str = Field(default="./uploads")
    
    # LLM
    LLM_PROVIDER: str = Field(default="openai")  # "openai" or "groq"
    OPENAI_API_KEY: str = Field(default="")
    GROQ_API_KEY: str = Field(default="")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
