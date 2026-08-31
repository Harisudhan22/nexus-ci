"""Add pgvector extension and vector column to document_chunks

Revision ID: 001_add_vector_column
Revises: 
Create Date: 2026-08-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '001_add_vector_column'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # 1. Enable pgvector extension safely if supported by PostgreSQL engine
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        print(f"[MIGRATION NOTICE] Native pgvector extension not available: {e}")

    # 2. Add native vector column to document_chunks safely
    try:
        conn.execute(text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(64);"))
    except Exception as e:
        print(f"[MIGRATION NOTICE] Could not add vector(64) column (pgvector not installed): {e}")

    # 3. Add vector cosine index if pgvector is enabled
    try:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);"))
    except Exception as e:
        print(f"[MIGRATION NOTICE] Vector index could not be created: {e}")


def downgrade() -> None:
    conn = op.get_bind()
    try:
        conn.execute(text("DROP INDEX IF EXISTS idx_document_chunks_embedding;"))
        conn.execute(text("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;"))
    except Exception as e:
        print(f"[MIGRATION NOTICE] Downgrade notice: {e}")
