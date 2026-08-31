"""
NEXUS-CI Translation & Canonicalization Service
==================================================
Provides translation and canonical normalization for Indic and multilingual inputs.
Supports: English, Hindi, Tamil, Telugu, Bengali, Malayalam, Kannada, Marathi.
"""
import os
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class BaseTranslationProvider(ABC):
    """Abstract base for translation providers."""
    provider_name: str = "base"

    @abstractmethod
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> Dict[str, Any]:
        """
        Translate text to target language (default: English for canonical processing).
        Returns: {"translated_text": str, "source_lang": str, "target_lang": str, "provider": str}
        """
        ...


class HeuristicTranslationProvider(BaseTranslationProvider):
    """
    Normalizes Indic script entities and transliterated criminal intelligence terminology
    into canonical English tags while retaining full original source text.
    """
    provider_name = "heuristic"

    # Known Indic legal & intelligence domain terms mapped to canonical English
    TERM_MAP = {
        "एफआईआर": "FIR",
        "प्राथमिकी": "FIR",
        "प्रथम माहिती अहवाल": "FIR",
        "முதல் தகவல் அறிக்கை": "FIR",
        "அறிக்கை": "Report",
        "संदिग्ध": "Suspect",
        "சந்தேகநபர்": "Suspect",
        "அமைவிடம்": "Location",
        "स्थान": "Location",
        "வங்கி கணக்கு": "Bank Account",
        "बैंक खाता": "Bank Account",
        "வாகனம்": "Vehicle",
        "वाहन": "Vehicle",
        "தொலைபேசி": "Phone",
        "फोन": "Phone",
    }

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "translated_text": "",
                "source_lang": source_lang,
                "target_lang": target_lang,
                "provider": self.provider_name,
            }

        # If already English or target_lang matches source, return as-is
        if source_lang == "en" and target_lang == "en":
            return {
                "translated_text": text,
                "source_lang": "en",
                "target_lang": "en",
                "provider": self.provider_name,
            }

        translated = text
        for indic_term, canon_term in self.TERM_MAP.items():
            if indic_term in translated:
                translated = translated.replace(indic_term, canon_term)

        return {
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "provider": self.provider_name,
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def get_translation_provider(override: Optional[str] = None) -> BaseTranslationProvider:
    """Factory returning configured translation provider."""
    return HeuristicTranslationProvider()
