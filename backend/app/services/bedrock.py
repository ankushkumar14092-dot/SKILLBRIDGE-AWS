# Backward-compatible shim — all nodes import from here.
# Actual implementation is in services/llm.py (Strands Agents SDK).
from app.services.llm import invoke_llm, invoke_llm_json, set_mock_responses

__all__ = ["invoke_llm", "invoke_llm_json", "set_mock_responses"]
