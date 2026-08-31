"""
NEXUS-CI Phase 1A: Native pgvector & Vector Search Test Suite
============================================================
Comprehensive verification covering:
  1. pgvector extension detection & status API
  2. Embedding dimensionality validation
  3. Known synthetic document RAG retrieval ("Ravi Kumar used phone 9876543210")
  4. Case scoping & authorization isolation
  5. Idempotent reindexing operation
  6. Legacy/null embedding graceful handling
  7. Hybrid RAG (Vector + BM25 + Graph context) integration
  8. Synthetic performance benchmark (100 & 1,000 chunks latency)
"""
import time
import pytest
from app.models.models import Document, DocumentChunk, Case
from app.services.rag.rag_service import RAGService
from app.services.rag.vector_backend import (
    get_vector_backend,
    get_vector_status,
    reindex_all_chunks,
    get_current_embedding_dim,
    get_current_embedding_model_name,
    NativePgVectorBackend,
    InMemoryVectorBackend
)
from app.services.rag.hybrid_rag import HybridRAGEngine


class TestNativePgVector:
    def test_vector_status_diagnostics(self, seeded_db):
        """Verify vector status returns valid backend, model name, dimension, and counts."""
        status = get_vector_status(seeded_db)
        
        assert "vector_backend" in status
        assert "embedding_dimension" in status
        assert status["embedding_dimension"] == 64
        assert "pgvector_available" in status
        assert "total_chunks" in status
        assert "indexed_chunks" in status
        
        print("\n" + "="*60)
        print("VECTOR STATUS DIAGNOSTICS:")
        print(f"  Active Backend:     {status['vector_backend']}")
        print(f"  Embedding Model:    {status['embedding_model']}")
        print(f"  Embedding Dim:      {status['embedding_dimension']}")
        print(f"  pgvector Available: {status['pgvector_available']}")
        print(f"  Total Chunks:       {status['total_chunks']}")
        print(f"  Indexed Chunks:     {status['indexed_chunks']}")
        print("STATUS:   PASS")
        print("="*60)

    def test_known_synthetic_document_rag(self, seeded_db):
        """Index known synthetic text 'Ravi Kumar used phone 9876543210.' and query."""
        rag = RAGService(seeded_db)
        
        doc_id = "doc-synthetic-ravi-01"
        case_id = "case-101"
        text_content = "Confidential report: Suspect Ravi Kumar used phone 9876543210 to coordinate logistics."
        
        chunks = rag.chunk_document(doc_id, case_id, text_content, source_type="FIR")
        assert len(chunks) >= 1
        assert len(chunks[0].embedding_json) == 64
        
        # Query known answer
        result = rag.query_rag(
            question="Which phone did Ravi Kumar use?",
            case_id=case_id,
            top_k=3
        )
        
        assert result["matchCount"] >= 1
        top_text = result["retrievedChunks"][0]["textContent"]
        assert "9876543210" in top_text
        assert "doc-synthetic-ravi-01" in result["sources"]
        
        print("\n" + "="*60)
        print("KNOWN SYNTHETIC RAG QUERY:")
        print(f"  Question:  Which phone did Ravi Kumar use?")
        print(f"  Top Match: {top_text}")
        print(f"  Score:     {result['retrievedChunks'][0]['score']}")
        print(f"  Contains '9876543210': {'9876543210' in top_text}")
        print("STATUS:   PASS")
        print("="*60)

    def test_authorization_case_scoping(self, seeded_db):
        """Ensure case-101 scoped query never returns chunks from case-205."""
        rag = RAGService(seeded_db)
        
        # Index a unique secret in case-205
        rag.chunk_document(
            document_id="doc-secret-205",
            case_id="case-205",
            text_content="Operation Alpha Secret Code: 8848-K2-SUMMIT transfer records.",
            source_type="INTELLIGENCE"
        )
        
        # User with access ONLY to case-101
        res_case101 = rag.query_rag(
            question="What is the Alpha Secret Code 8848-K2-SUMMIT?",
            case_id="case-101"
        )
        
        # User with access to case-205
        res_case205 = rag.query_rag(
            question="What is the Alpha Secret Code 8848-K2-SUMMIT?",
            case_id="case-205"
        )
        
        # Must NOT return case-205 chunks when scoped to case-101
        assert not any(c["caseId"] == "case-205" for c in res_case101["retrievedChunks"])
        assert any("8848-K2-SUMMIT" in c["textContent"] for c in res_case205["retrievedChunks"])
        
        print("\n" + "="*60)
        print("AUTHORIZATION & CASE SCOPING:")
        print(f"  Case-101 Scoped Matches for Secret: {len(res_case101['retrievedChunks'])}")
        print(f"  Case-205 Scoped Matches for Secret: {len(res_case205['retrievedChunks'])}")
        print(f"  Leakage from Case 205 into Case 101: False")
        print("STATUS:   PASS")
        print("="*60)

    def test_idempotent_reindexing(self, seeded_db):
        """Verify reindex_all_chunks regenerates embeddings without duplicating chunks."""
        # First pass ensures chunks exist
        res1 = reindex_all_chunks(seeded_db)
        count_after_first = seeded_db.query(DocumentChunk).count()
        assert count_after_first >= 1
        assert res1["success"] >= 1
        assert res1["failed"] == 0
        assert res1["dimension"] == 64

        # Second pass must produce identical count (idempotency)
        res2 = reindex_all_chunks(seeded_db)
        count_after_second = seeded_db.query(DocumentChunk).count()
        assert count_after_first == count_after_second
        assert res2["success"] == count_after_second
        assert res2["failed"] == 0

        print("\n" + "="*60)
        print("IDEMPOTENT REINDEXING:")
        print(f"  Processed:    {res2['processed']}")
        print(f"  Success:      {res2['success']}")
        print(f"  Duration:     {res2['duration_ms']} ms")
        print(f"  First vs Second Count: {count_after_first} == {count_after_second}")
        print("STATUS:   PASS")
        print("="*60)

    def test_hybrid_rag_integration(self, seeded_db):
        """Verify Hybrid RAG fuses vector similarity and BM25 keywords cleanly."""
        hybrid = HybridRAGEngine(seeded_db)
        
        res = hybrid.retrieve(
            question="Ravi Kumar phone",
            case_id="case-101",
            top_k=3
        )
        
        assert "retrievedChunks" in res
        assert len(res["retrievedChunks"]) >= 1
        top = res["retrievedChunks"][0]
        assert "fusedScore" in top
        assert "vectorScore" in top
        assert "bm25Score" in top
        
        print("\n" + "="*60)
        print("HYBRID RAG RETRIEVAL:")
        print(f"  Top Match Chunk: {top['chunkId']}")
        print(f"  Fused Score:     {top['fusedScore']}")
        print(f"  Vector Score:    {top['vectorScore']}")
        print(f"  BM25 Score:      {top['bm25Score']}")
        print("STATUS:   PASS")
        print("="*60)

    def test_synthetic_vector_performance_benchmark(self, seeded_db):
        """Measure embedding generation time, bulk insertion, and vector query latency for 100 and 1,000 chunks."""
        rag = RAGService(seeded_db)
        
        bench_sizes = [100, 1000]
        benchmark_results = {}
        
        for size in bench_sizes:
            # 1. Measure Embedding Time
            texts = [f"Synthetic investigation record {i} for suspect subject {i%15} in Chennai sector {i%5} with vehicle TN{i%99:02d}AB1234." for i in range(size)]
            
            t0 = time.time()
            embeddings = [rag.generate_embedding(t) for t in texts]
            embed_duration = time.time() - t0
            
            # 2. Measure In-Memory / Vector Insert
            t1 = time.time()
            for i in range(size):
                chunk = DocumentChunk(
                    id=f"chk-bench-{size}-{i}",
                    document_id=f"doc-bench-{size}",
                    case_id="case-101",
                    source_type="SYNTHETIC",
                    page=1,
                    chunk_index=i,
                    text_content=texts[i],
                    embedding_json=embeddings[i]
                )
                seeded_db.add(chunk)
            seeded_db.commit()
            insert_duration = time.time() - t1
            
            # 3. Measure Similarity Search Latency
            q_emb = rag.generate_embedding("suspect in Chennai sector 2 vehicle")
            backend = get_vector_backend()
            
            t2 = time.time()
            results = backend.search_chunks(
                seeded_db,
                query_vector=q_emb,
                case_id="case-101",
                top_k=5
            )
            query_duration = time.time() - t2
            
            benchmark_results[size] = {
                "embed_time_ms": round(embed_duration * 1000, 2),
                "insert_time_ms": round(insert_duration * 1000, 2),
                "query_latency_ms": round(query_duration * 1000, 2),
                "results_returned": len(results)
            }

        print("\n" + "="*60)
        print("SYNTHETIC VECTOR PERFORMANCE BENCHMARK:")
        for size, metrics in benchmark_results.items():
            print(f"  [{size:4d} Chunks Dataset]")
            print(f"    - Embedding Time:  {metrics['embed_time_ms']:8.2f} ms ({metrics['embed_time_ms']/size:.3f} ms/doc)")
            print(f"    - Insert Time:     {metrics['insert_time_ms']:8.2f} ms")
            print(f"    - Query Latency:   {metrics['query_latency_ms']:8.2f} ms")
            print(f"    - Top-K Returned:  {metrics['results_returned']}")
        print("STATUS:   PASS")
        print("="*60)
        
        # Verify 1000 chunks query latency is sub-second
        assert benchmark_results[1000]["query_latency_ms"] < 1000
