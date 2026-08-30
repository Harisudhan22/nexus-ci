import os
import json
import urllib.request
from typing import Dict, Any, List, Optional

class BaseLLMProvider:
    provider_type: str = "LOCAL_FALLBACK"

    def generate_answer(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class OpenAIProvider(BaseLLMProvider):
    provider_type: str = "REAL_LLM"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def generate_answer(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""You are an Evidence-Grounded Criminal Intelligence Copilot.
Answer the question strictly based on the provided evidence context. Do not invent details.

<evidence_data_context>
{json.dumps(context)}
</evidence_data_context>

Question: {question}
"""
        req_data = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"]
                return {
                    "summary": text,
                    "providerType": self.provider_type,
                    "model": self.model
                }
        except Exception as e:
            return GroundedLocalProvider().generate_answer(question, context)

class OllamaProvider(BaseLLMProvider):
    provider_type: str = "REAL_LLM"

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3"):
        self.host = host
        self.model = model

    def generate_answer(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Strictly answer based on context:\nContext: {json.dumps(context)}\nQuestion: {question}"""
        req_data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return {
                    "summary": result.get("response", ""),
                    "providerType": self.provider_type,
                    "model": self.model
                }
        except Exception:
            return GroundedLocalProvider().generate_answer(question, context)

class GroundedLocalProvider(BaseLLMProvider):
    provider_type: str = "LOCAL_FALLBACK"

    def generate_answer(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        chunks = context.get("chunks", [])
        matched = context.get("matchedEntities", [])
        
        if chunks:
            top_text = chunks[0].get("textContent", "")
            return {
                "summary": f"Based on evidence chunk ({chunks[0].get('documentId', '')}): \"{top_text[:300]}...\"",
                "providerType": self.provider_type,
                "model": "GroundedLocalSolver"
            }
        elif matched:
            target = matched[0]
            label = target.get("label") if isinstance(target, dict) else target.label
            attributes = target.get("attributes") if isinstance(target, dict) else target.attributes
            return {
                "summary": f"Entity '{label}' is registered in target operation. Attributes: {json.dumps(attributes)}.",
                "providerType": self.provider_type,
                "model": "GroundedLocalSolver"
            }
        
        return {
            "summary": "Insufficient evidence in the current dataset.",
            "providerType": self.provider_type,
            "model": "GroundedLocalSolver"
        }

def get_llm_provider() -> BaseLLMProvider:
    """Factory returning configured LLM provider based on environment variables."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return OpenAIProvider(api_key=openai_key)

    ollama_host = os.getenv("OLLAMA_HOST")
    if ollama_host:
        return OllamaProvider(host=ollama_host)

    return GroundedLocalProvider()
