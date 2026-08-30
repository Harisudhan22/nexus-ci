from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    # For SQLite, connect_args={"check_same_thread": False} is needed, but we use Postgres
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
from sqlalchemy import text

def init_db():
    Base.metadata.create_all(bind=engine)
    # Safe non-destructive column additions for existing PostgreSQL tables
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE cases ADD COLUMN IF NOT EXISTS police_station VARCHAR;"))
            conn.execute(text("ALTER TABLE cases ADD COLUMN IF NOT EXISTS district VARCHAR;"))
            conn.execute(text("ALTER TABLE cases ADD COLUMN IF NOT EXISTS state VARCHAR;"))
            conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS rows_data JSON;"))
            conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS extracted_text TEXT;"))
            conn.execute(text("ALTER TABLE entity_merge_decisions ADD COLUMN IF NOT EXISTS rollback_state JSON;"))
            conn.execute(text("ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_document_id_fkey;"))
            conn.commit()
        except Exception as e:
            print(f"Schema migration notice: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
