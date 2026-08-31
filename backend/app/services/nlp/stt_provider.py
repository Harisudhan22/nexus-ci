"""
NEXUS-CI Speech-to-Text Provider Abstraction
==============================================
Provides Whisper-based audio transcription with mock fallback
for testing and environments without GPU/audio libraries.
"""
import os
from typing import Optional
from abc import ABC, abstractmethod


class BaseSTTProvider(ABC):
    """Abstract base for speech-to-text providers."""
    provider_name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "en") -> dict:
        """
        Transcribe an audio file.
        Returns: {"text": str, "language": str, "duration_seconds": float, "segments": list}
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is ready to use."""
        ...


class WhisperSTTProvider(BaseSTTProvider):
    """
    OpenAI Whisper speech-to-text provider.
    Uses the whisper Python library for local inference.
    """
    provider_name = "whisper"

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_size)
        return self._model

    def transcribe(self, audio_path: str, language: str = "en") -> dict:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()
        result = model.transcribe(audio_path, language=language)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip()
            })

        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language", language),
            "duration_seconds": segments[-1]["end"] if segments else 0.0,
            "segments": segments
        }

    def is_available(self) -> bool:
        try:
            import whisper
            return True
        except ImportError:
            return False


class MockSTTProvider(BaseSTTProvider):
    """
    Mock speech-to-text provider for testing.
    Returns a deterministic transcript from the filename.
    """
    provider_name = "mock"

    def transcribe(self, audio_path: str, language: str = "en") -> dict:
        basename = os.path.basename(audio_path)
        mock_text = f"[Mock Transcript] Audio file '{basename}' processed. Suspect discussed meeting at the warehouse on Friday at 8 PM."
        return {
            "text": mock_text,
            "language": language,
            "duration_seconds": 120.0,
            "segments": [
                {"start": 0.0, "end": 5.0, "text": f"[Mock Transcript] Audio file '{basename}' processed."},
                {"start": 5.0, "end": 12.0, "text": "Suspect discussed meeting at the warehouse on Friday at 8 PM."}
            ]
        }

    def is_available(self) -> bool:
        return True


# ── Factory ──────────────────────────────────────────────────────

def get_stt_provider(override: Optional[str] = None) -> BaseSTTProvider:
    """Factory returning configured STT provider."""
    target = (override or os.getenv("STT_PROVIDER", "mock")).strip().lower()
    strict = os.getenv("STT_STRICT", "false").strip().lower() == "true"

    if target == "whisper":
        provider = WhisperSTTProvider()
        if provider.is_available():
            return provider
        if strict:
            raise RuntimeError("STT_PROVIDER=whisper requested in strict mode, but whisper library is not installed.")
        print("[STT] Whisper library unavailable, using MockSTTProvider")

    return MockSTTProvider()
