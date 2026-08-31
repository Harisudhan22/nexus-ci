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
    NEO4J_PASSWORD: str = Field(default="password")
    
    # Files
    UPLOAD_DIR: str = Field(default="./uploads")
    
    # Infrastructure Configurations
    VECTOR_BACKEND: str = Field(default="pgvector")  # "pgvector" or "in_memory"
    VECTOR_FALLBACK_ENABLED: bool = Field(default=False)  # Explicit production control: False = Fail closed if pgvector unavailable
    EMBEDDING_PROVIDER: str = Field(default="deterministic")  # "deterministic" or "transformer"
    EMBEDDING_DIMENSION: int = Field(default=64)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    STORAGE_BACKEND: str = Field(default="local")  # "local" or "s3"
    S3_ENDPOINT: str = Field(default="")
    S3_BUCKET: str = Field(default="nexus-ci-evidence")
    S3_ACCESS_KEY: str = Field(default="")
    S3_SECRET_KEY: str = Field(default="")
    S3_REGION: str = Field(default="ap-south-1")
    STT_PROVIDER: str = Field(default="whisper")  # "whisper" or "mock"
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # LLM Multi-Provider Configurations
    LLM_PROVIDER: str = Field(default="gemini")
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.6-flash")
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OLLAMA_HOST: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
