"""
LLM service — Strands Agents SDK (BUILD IT track).

Strands Agents SDK is the official AWS open-source agent framework.
https://github.com/strands-agents/sdk-python

Model providers (configure via env):
  STRANDS_PROVIDER=ollama   → fully local, no API key (ollama pull llama3.2)
  STRANDS_PROVIDER=bedrock  → AWS Bedrock (needs credentials)
  STRANDS_PROVIDER=mock     → deterministic mock (zero setup, for CI/testing)
"""
import os
import json
from typing import List, Dict, Any

STRANDS_PROVIDER = os.getenv("STRANDS_PROVIDER", "mock").lower()
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3.2")
FIREWORKS_API_KEY= os.getenv("FIREWORKS_API_KEY", "")
FIREWORKS_MODEL  = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/deepseek-v4-flash-0731")
AWS_REGION       = os.getenv("AWS_REGION", "us-east-1")


# ── Fireworks AI provider ──────────────────────────────────────────────────────

def _invoke_fireworks(messages: List[Dict[str, Any]], system: str = "") -> str:
    import requests
    api_key = os.getenv("FIREWORKS_API_KEY", "").strip()
    model_name = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/deepseek-v4-flash-0731").strip()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    formatted_messages = []
    if system:
        formatted_messages.append({"role": "system", "content": system})
    formatted_messages.extend(messages)

    payload = {
        "model": model_name,
        "messages": formatted_messages,
        "temperature": 0.2,
    }
    print(f"   🤖 [fireworks-llm] calling model: {model_name}")
    r = requests.post("https://api.fireworks.ai/inference/v1/chat/completions", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


# ── Mock provider (zero setup) ─────────────────────────────────────────────────

_MOCK_RESPONSES: Dict[str, Any] = {}  # injected by local_runner.py
_mock_call_idx = {"n": 0}


def _invoke_mock(messages: List[Dict[str, Any]], system: str = "") -> str:
    keys = list(_MOCK_RESPONSES.keys())
    if not keys:
        return json.dumps({"error": "no mock responses configured"})
    idx = _mock_call_idx["n"] % len(keys)
    _mock_call_idx["n"] += 1
    key = keys[idx]
    print(f"   🤖 [mock-llm] call #{_mock_call_idx['n']} → {key}")
    return json.dumps(_MOCK_RESPONSES[key])


def set_mock_responses(responses: Dict[str, Any]) -> None:
    """Called by local_runner to inject deterministic responses."""
    _MOCK_RESPONSES.clear()
    _MOCK_RESPONSES.update(responses)
    _mock_call_idx["n"] = 0


# ── Ollama provider (fully local, no API key) ──────────────────────────────────

def _invoke_ollama(messages: List[Dict[str, Any]], system: str = "") -> str:
    try:
        from strands import Agent
        from strands.models.ollama import OllamaModel

        model = OllamaModel(model_id=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
        prompt = _build_prompt(messages, system)
        agent = Agent(model=model)
        return str(agent(prompt))
    except ImportError:
        # Fallback: direct Ollama HTTP API
        import requests
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": _build_prompt(messages, system),
            "stream": False,
        }
        r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["response"]


# ── Bedrock provider via Strands SDK ──────────────────────────────────────────

def _invoke_strands_bedrock(messages: List[Dict[str, Any]], system: str = "") -> str:
    from strands import Agent
    from strands.models import BedrockModel

    model = BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION)
    prompt = _build_prompt(messages, system)
    agent = Agent(model=model, system_prompt=system or None)
    return str(agent(prompt))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_prompt(messages: List[Dict[str, Any]], system: str = "") -> str:
    parts = []
    if system:
        parts.append(f"System instructions: {system}")
    for m in messages:
        parts.append(f"{m.get('role','user').capitalize()}: {m.get('content','')}")
    return "\n\n".join(parts)


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    # Strip markdown fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    return json.loads(text)


# ── Public interface ───────────────────────────────────────────────────────────

def invoke_llm(messages: List[Dict[str, Any]], system: str = "") -> str:
    if STRANDS_PROVIDER == "mock":
        return _invoke_mock(messages, system)
    elif STRANDS_PROVIDER == "ollama":
        return _invoke_ollama(messages, system)
    elif STRANDS_PROVIDER == "fireworks":
        return _invoke_fireworks(messages, system)
    else:
        return _invoke_strands_bedrock(messages, system)


def invoke_llm_json(messages: List[Dict[str, Any]], system: str = "") -> Dict[str, Any]:
    text = invoke_llm(messages, system)
    return _extract_json(text)
