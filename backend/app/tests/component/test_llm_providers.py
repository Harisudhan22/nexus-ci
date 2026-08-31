"""
COMPONENT TEST: Multi-Provider LLM & Factory Validation
=========================================================
Tests:
  TEST A: Gemini configuration detected
  TEST B: Groq configuration detected
  TEST C: Provider factory returns Gemini when LLM_PROVIDER=gemini
  TEST D: Provider factory returns Groq when LLM_PROVIDER=groq
  TEST E: Missing Gemini key produces configuration error
  TEST F: Missing Groq key produces configuration error
  TEST G: Local fallback is explicitly labeled LOCAL_FALLBACK
  TEST H: Real provider response is labeled REAL_LLM
  TEST I: API status diagnostic endpoint never exposes API keys
  TEST J: Seamless provider switching without code modifications
"""
import os
import pytest
from app.services.copilot.llm_provider import (
    get_llm_provider,
    get_provider_status,
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
    OllamaProvider,
    GroundedLocalProvider
)


class TestLLMProviders:
    """Step 17 & Step 24 — LLM Multi-Provider verification suite."""

    def test_a_gemini_configuration_detected(self, monkeypatch):
        """TEST A: Gemini configuration detected when keys are set."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-12345")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-pro")

        provider = get_llm_provider()

        print(f"\n{'='*60}")
        print(f"TEST A — GEMINI CONFIGURATION:")
        print(f"  Class:         {provider.__class__.__name__}")
        print(f"  Provider Name: {provider.provider_name}")
        print(f"  Model:         {provider.model}")
        print(f"  Provider Type: {provider.provider_type}")
        print(f"  Is Real LLM:   {provider.is_real_llm}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        assert isinstance(provider, GeminiProvider)
        assert provider.provider_name == "gemini"
        assert provider.model == "gemini-1.5-pro"
        assert provider.provider_type == "REAL_LLM"
        assert provider.is_real_llm is True

    def test_b_groq_configuration_detected(self, monkeypatch):
        """TEST B: Groq configuration detected when keys are set."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test_groq_key_999")
        monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        provider = get_llm_provider()

        print(f"\n{'='*60}")
        print(f"TEST B — GROQ CONFIGURATION:")
        print(f"  Class:         {provider.__class__.__name__}")
        print(f"  Provider Name: {provider.provider_name}")
        print(f"  Model:         {provider.model}")
        print(f"  Provider Type: {provider.provider_type}")
        print(f"  Is Real LLM:   {provider.is_real_llm}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        assert isinstance(provider, GroqProvider)
        assert provider.provider_name == "groq"
        assert provider.model == "llama-3.3-70b-versatile"
        assert provider.provider_type == "REAL_LLM"
        assert provider.is_real_llm is True

    def test_c_factory_returns_gemini(self, monkeypatch):
        """TEST C: Provider factory returns Gemini when LLM_PROVIDER=gemini."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

        provider = get_llm_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.provider_type == "REAL_LLM"

    def test_d_factory_returns_groq(self, monkeypatch):
        """TEST D: Provider factory returns Groq when LLM_PROVIDER=groq."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        provider = get_llm_provider()
        assert isinstance(provider, GroqProvider)
        assert provider.provider_type == "REAL_LLM"

    def test_e_missing_gemini_key_raises_error(self, monkeypatch):
        """TEST E: Missing Gemini key produces clear configuration error."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        print(f"\n{'='*60}")
        print(f"TEST E — MISSING GEMINI KEY:")
        with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable is required"):
            get_llm_provider()
        print(f"  Expected ValueError was raised successfully.")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_f_missing_groq_key_raises_error(self, monkeypatch):
        """TEST F: Missing Groq key produces clear configuration error."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        print(f"\n{'='*60}")
        print(f"TEST F — MISSING GROQ KEY:")
        with pytest.raises(ValueError, match="GROQ_API_KEY environment variable is required"):
            get_llm_provider()
        print(f"  Expected ValueError was raised successfully.")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

    def test_g_local_fallback_label(self, monkeypatch):
        """TEST G: Local fallback is explicitly labeled LOCAL_FALLBACK."""
        monkeypatch.setenv("LLM_PROVIDER", "local")

        provider = get_llm_provider()
        res = provider.generate_answer("Who is Ravi?", {"chunks": [], "matchedEntities": []})

        print(f"\n{'='*60}")
        print(f"TEST G — LOCAL FALLBACK LABEL:")
        print(f"  Provider Type: {res['providerType']}")
        print(f"  Is Real LLM:   {res['is_real_llm']}")
        print(f"  Summary:       {res['summary']}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        assert res["providerType"] == "LOCAL_FALLBACK"
        assert res["is_real_llm"] is False

    def test_h_real_provider_metadata(self):
        """TEST H: Real provider classes expose REAL_LLM and is_real_llm=True."""
        gemini = GeminiProvider(api_key="mock", model="gemini-1.5-flash")
        groq = GroqProvider(api_key="mock", model="llama-3.3-70b-versatile")
        openai = OpenAIProvider(api_key="mock", model="gpt-4o-mini")
        ollama = OllamaProvider(host="http://localhost:11434", model="llama3")

        for p in [gemini, groq, openai, ollama]:
            assert p.provider_type == "REAL_LLM"
            assert p.is_real_llm is True

    def test_i_provider_status_safe_endpoint(self, monkeypatch):
        """TEST I: get_provider_status endpoint returns metadata without exposing secrets."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "super_secret_gemini_key_never_leak")

        status = get_provider_status()

        print(f"\n{'='*60}")
        print(f"TEST I — PROVIDER STATUS ENDPOINT PAYLOAD:")
        for k, v in status.items():
            print(f"  {k:20s}: {v}")
        print(f"STATUS:   PASS")
        print(f"{'='*60}")

        assert "super_secret_gemini_key_never_leak" not in str(status)
        assert status["provider_name"] == "gemini"
        assert status["provider_type"] == "REAL_LLM"
        assert status["configured"] is True

    def test_j_provider_switching(self, monkeypatch):
        """TEST J: Provider switching without code changes."""
        # 1. Switch to Groq
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        p_groq = get_llm_provider()
        assert p_groq.provider_name == "groq"

        # 2. Switch to Gemini
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "gem_test")
        p_gemini = get_llm_provider()
        assert p_gemini.provider_name == "gemini"

        # 3. Switch to OpenAI
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        p_openai = get_llm_provider()
        assert p_openai.provider_name == "openai"

        # 4. Switch to Local
        monkeypatch.setenv("LLM_PROVIDER", "local")
        p_local = get_llm_provider()
        assert p_local.provider_name == "grounded_local"
