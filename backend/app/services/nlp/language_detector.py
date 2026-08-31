"""
NEXUS-CI Language Detection Provider
======================================
Detects the language of input text for multilingual NLP pipeline routing.
Uses langdetect when available, falls back to a simple heuristic.
"""
import os
from typing import Optional
from abc import ABC, abstractmethod


class BaseLanguageDetector(ABC):
    """Abstract base for language detection."""
    provider_name: str = "base"

    @abstractmethod
    def detect(self, text: str) -> dict:
        """
        Detect language of text.
        Returns: {"language": str (ISO 639-1), "confidence": float, "provider": str}
        """
        ...


class LangDetectProvider(BaseLanguageDetector):
    """Language detection using the langdetect library (Google's language-detection port)."""
    provider_name = "langdetect"

    def detect(self, text: str) -> dict:
        if not text or not text.strip():
            return {"language": "und", "confidence": 0.0, "provider": self.provider_name}

        from langdetect import detect_langs

        results = detect_langs(text)
        if results:
            top = results[0]
            return {
                "language": str(top.lang),
                "confidence": round(float(top.prob), 4),
                "provider": self.provider_name
            }
        return {"language": "und", "confidence": 0.0, "provider": self.provider_name}


class HeuristicLanguageDetector(BaseLanguageDetector):
    """
    Simple character-set heuristic language detector.
    Detects Hindi (Devanagari), Tamil, Telugu, Bengali, Arabic, Chinese, English.
    """
    provider_name = "heuristic"

    # Unicode block ranges for major Indian and international scripts
    SCRIPT_RANGES = {
        "hi": (0x0900, 0x097F),   # Devanagari (Hindi, Marathi, Sanskrit)
        "ta": (0x0B80, 0x0BFF),   # Tamil
        "te": (0x0C00, 0x0C7F),   # Telugu
        "bn": (0x0980, 0x09FF),   # Bengali
        "gu": (0x0A80, 0x0AFF),   # Gujarati
        "kn": (0x0C80, 0x0CFF),   # Kannada
        "ml": (0x0D00, 0x0D7F),   # Malayalam
        "pa": (0x0A00, 0x0A7F),   # Gurmukhi (Punjabi)
        "or": (0x0B00, 0x0B7F),   # Odia
        "ar": (0x0600, 0x06FF),   # Arabic
        "zh": (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    }

    def detect(self, text: str) -> dict:
        if not text or not text.strip():
            return {"language": "und", "confidence": 0.0, "provider": self.provider_name}

        scores: dict = {}
        total_chars = 0

        for ch in text:
            cp = ord(ch)
            if ch.isspace() or ch in ".,;:!?-()[]{}\"'":
                continue
            total_chars += 1
            for lang, (lo, hi) in self.SCRIPT_RANGES.items():
                if lo <= cp <= hi:
                    scores[lang] = scores.get(lang, 0) + 1
                    break
            else:
                if ch.isascii() and ch.isalpha():
                    scores["en"] = scores.get("en", 0) + 1

        if not total_chars:
            return {"language": "und", "confidence": 0.0, "provider": self.provider_name}

        best_lang = max(scores, key=scores.get, default="und")
        confidence = round(scores.get(best_lang, 0) / total_chars, 4) if total_chars else 0.0

        return {
            "language": best_lang,
            "confidence": confidence,
            "provider": self.provider_name
        }


# ── Factory ──────────────────────────────────────────────────────

def get_language_detector(override: Optional[str] = None) -> BaseLanguageDetector:
    """Factory returning configured language detector."""
    target = (override or os.getenv("LANGUAGE_DETECTOR", "heuristic")).strip().lower()

    if target == "langdetect":
        try:
            from langdetect import detect_langs
            return LangDetectProvider()
        except ImportError:
            print("[LANG] langdetect not available, falling back to heuristic")

    return HeuristicLanguageDetector()
