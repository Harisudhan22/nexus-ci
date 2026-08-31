"""
Tests: Phases 3-6 Production Abstractions
==========================================
Storage Backend, STT Provider, Language Detection, Hybrid RAG
"""
import os
import pytest
import tempfile
from app.services.evidence.storage_backend import LocalStorageBackend, get_storage_backend
from app.services.nlp.stt_provider import MockSTTProvider, get_stt_provider
from app.services.nlp.language_detector import HeuristicLanguageDetector, get_language_detector


class TestStorageBackend:
    def test_local_save_load_delete(self, tmp_path):
        """Save, load, verify, and delete a file via local storage backend."""
        backend = LocalStorageBackend(base_dir=str(tmp_path))
        
        data = b"FIR-101 evidence file content SHA-256 verified"
        key = "case-101/doc-fir-101.pdf"
        
        path = backend.save(key, data)
        assert backend.exists(key)
        
        loaded = backend.load(key)
        assert loaded == data
        
        deleted = backend.delete(key)
        assert deleted is True
        assert not backend.exists(key)
        
        print(f"\n{'='*60}")
        print(f"LOCAL STORAGE BACKEND:")
        print(f"  Save path: {path}")
        print(f"  Data match: True")
        print(f"  Delete confirmed: True")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")
    
    def test_directory_traversal_prevention(self, tmp_path):
        """Ensure '..' in keys is sanitized."""
        backend = LocalStorageBackend(base_dir=str(tmp_path))
        key = "../../../etc/passwd"
        path = backend.save(key, b"test")
        # Path should NOT escape base_dir
        assert str(tmp_path) in path
        
        print(f"\n{'='*60}")
        print(f"DIRECTORY TRAVERSAL PREVENTION:")
        print(f"  Malicious key: {key}")
        print(f"  Resolved path: {path}")
        print(f"  Stayed in base_dir: True")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_factory_returns_local_by_default(self):
        """Default factory should return local backend."""
        import app.services.evidence.storage_backend as sb_mod
        sb_mod._storage_instance = None
        backend = get_storage_backend()
        assert backend.backend_name == "local"
        sb_mod._storage_instance = None

        print(f"\n{'='*60}")
        print(f"STORAGE FACTORY:")
        print(f"  Backend: {backend.backend_name}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")


class TestSTTProvider:
    def test_mock_stt_transcription(self, tmp_path):
        """Mock STT returns deterministic transcript."""
        provider = MockSTTProvider()
        assert provider.is_available()
        
        # Create a dummy audio file
        audio_file = tmp_path / "suspect_call.wav"
        audio_file.write_bytes(b"fake audio data")
        
        result = provider.transcribe(str(audio_file))
        
        assert "suspect_call.wav" in result["text"]
        assert result["language"] == "en"
        assert result["duration_seconds"] > 0
        assert len(result["segments"]) >= 1
        
        print(f"\n{'='*60}")
        print(f"MOCK STT TRANSCRIPTION:")
        print(f"  Text: {result['text'][:80]}...")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"  Segments: {len(result['segments'])}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_stt_factory_returns_mock(self):
        """Factory returns mock when whisper is not installed."""
        provider = get_stt_provider("mock")
        assert provider.provider_name == "mock"
        
        print(f"\n{'='*60}")
        print(f"STT FACTORY:")
        print(f"  Provider: {provider.provider_name}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")


class TestLanguageDetector:
    def test_english_detection(self):
        """Detect English text."""
        detector = HeuristicLanguageDetector()
        result = detector.detect("The suspect was seen near the railway station at midnight.")
        
        assert result["language"] == "en"
        assert result["confidence"] > 0.8
        
        print(f"\n{'='*60}")
        print(f"LANGUAGE DETECTION - ENGLISH:")
        print(f"  Detected: {result['language']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_hindi_detection(self):
        """Detect Hindi (Devanagari) text."""
        detector = HeuristicLanguageDetector()
        result = detector.detect("संदिग्ध को रेलवे स्टेशन के पास देखा गया था")
        
        assert result["language"] == "hi"
        assert result["confidence"] > 0.5
        
        print(f"\n{'='*60}")
        print(f"LANGUAGE DETECTION - HINDI:")
        print(f"  Detected: {result['language']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_tamil_detection(self):
        """Detect Tamil text."""
        detector = HeuristicLanguageDetector()
        result = detector.detect("சந்தேகநபர் ரயில்வே நிலையம் அருகில் இரவில் காணப்பட்டார்")
        
        assert result["language"] == "ta"
        assert result["confidence"] > 0.5
        
        print(f"\n{'='*60}")
        print(f"LANGUAGE DETECTION - TAMIL:")
        print(f"  Detected: {result['language']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_empty_text_returns_undetermined(self):
        """Empty text returns 'und' language."""
        detector = HeuristicLanguageDetector()
        result = detector.detect("")
        assert result["language"] == "und"
        
        print(f"\n{'='*60}")
        print(f"LANGUAGE DETECTION - EMPTY:")
        print(f"  Detected: {result['language']}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_factory_returns_heuristic_by_default(self):
        """Factory returns heuristic detector when langdetect is not installed."""
        detector = get_language_detector()
        assert detector.provider_name == "heuristic"
        
        print(f"\n{'='*60}")
        print(f"LANGUAGE DETECTOR FACTORY:")
        print(f"  Provider: {detector.provider_name}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")
