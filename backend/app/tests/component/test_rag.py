"""
COMPONENT TEST: RAG Retrieval & Permission Scoping
===================================================
Tests RAG vector indexing, chunk similarity retrieval, known question verification ("Which phone did Ravi Kumar use?"),
and case-level permission boundaries.
"""
import pytest
from app.services.rag.rag_service import RAGService
from app.models.models import DocumentChunk


class TestRAG:
    """Phase 17 & Phase 18 — RAG vector retrieval & permission scoping."""

    def test_rag_chunking_and_retrieval(self, seeded_db, rag_chunks):
        res = rag_chunks.query_rag(question="Which phone is associated with Ravi Kumar?", case_id="case-101")

        chunks = res.get("retrievedChunks", [])
        sources = res.get("sources", [])

        print(f"\n{'='*60}")
        print(f"RAG RETRIEVAL (case-101):")
        print(f"  Question: Which phone is associated with Ravi Kumar?")
        print(f"  Chunks Found: {len(chunks)}")
        print(f"  Sources: {sources}")
        for c in chunks:
            print(f"    - [{c['score']:.4f}] Doc: {c['documentId']}, Text: \"{c['textContent'][:100]}...\"")
        print(f"STATUS:   {'PASS' if len(chunks) >= 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(chunks) >= 1
        assert "doc-fir-101" in sources

    def test_known_answer_retrieval(self, seeded_db, rag_chunks):
        res = rag_chunks.query_rag(question="Which phone did Ravi Kumar use?", case_id="case-101")
        top_chunk = res["retrievedChunks"][0]["textContent"]

        print(f"\n{'='*60}")
        print(f"KNOWN ANSWER VERIFICATION:")
        print(f"  Top Text: {top_chunk}")
        print(f"  Phone-101 / 9876543210 present: {'9876543210' in top_chunk}")
        print(f"STATUS:   {'PASS' if '9876543210' in top_chunk else 'FAIL'}")
        print(f"{'='*60}")

        assert "9876543210" in top_chunk

    def test_rag_permission_scoping(self, seeded_db):
        """User asking for case-205 evidence when scoping to case-101 should return NO case-205 chunks."""
        rag = RAGService(seeded_db)
        
        # Index document for case-205 with unique content
        rag.chunk_document("doc-tx-205", "case-205", "Operation Silverline confidential ledger item X99", source_type="TRANSACTIONS")
        
        # Query scoped strictly to case-101
        res_case101 = rag.query_rag(question="Silverline confidential ledger item X99", case_id="case-101")
        
        # Query scoped to case-205
        res_case205 = rag.query_rag(question="Silverline confidential ledger item X99", case_id="case-205")

        print(f"\n{'='*60}")
        print(f"RAG PERMISSION SCOPING TEST:")
        print(f"  Case-101 Scoped Match Count: {len(res_case101['retrievedChunks'])}")
        print(f"  Case-205 Scoped Match Count: {len(res_case205['retrievedChunks'])}")
        print(f"STATUS:   {'PASS' if len(res_case101['retrievedChunks']) == 0 and len(res_case205['retrievedChunks']) >= 1 else 'FAIL'}")
        print(f"{'='*60}")

        assert len(res_case101["retrievedChunks"]) == 0
        assert len(res_case205["retrievedChunks"]) >= 1
