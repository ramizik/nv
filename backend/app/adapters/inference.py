"""Real inference adapters — turn a transcript into a LeadAnalysis.

The DEMO/REAL path is `HermesInferenceAdapter`: we POST the transcript to Hermes
(the teammate's OpenAI-compatible gateway on the GB10) and Hermes delegates the
reasoning to its local default model — **Qwen3-30B served via Ollama on the box**.
So inference stays on-prem (patient conversations never leave the building) AND we
never run our own model server. `QwenInferenceAdapter` is a DIRECT-to-Ollama fallback
for when Hermes is unavailable.

Both share one reliability strategy (so the demo can never hard-fail):
  1. Run the mock heuristic FIRST to get a COMPLETE LeadAnalysis skeleton.
  2. Ask the model for the same JSON; robustly parse it (handles <think> reasoning
     tags, ```json fences, and leading/trailing prose).
  3. OVERLAY the model's non-empty fields onto the skeleton — so even if the model
     omits a field, the dashboard still gets a full object.
  4. On ANY error, return the mock skeleton tagged `_source = mock_fallback`.

Enable the real path with:
  INFERENCE_BACKEND=hermes
  HERMES_BASE_URL=http://127.0.0.1:8642
  HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>   (the gateway bearer; the model is keyless)
Or the direct fallback with:
  INFERENCE_BACKEND=qwen   QWEN_BASE_URL=http://127.0.0.1:11434/v1   QWEN_MODEL=Qwen3-30B:latest
"""
import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app import config
from app.adapters.base import InferenceAdapter
from app.adapters.mock import MockInferenceAdapter

# Keys we accept from the model and overlay onto the mock skeleton.
_OVERLAY_KEYS = ("summary", "extracted", "score", "estimated_deal_value",
                 "clinic_context_hits", "next_best_action")

# The reasoning instruction. The first line is a per-model "thinking off" directive
# (Qwen3: "/no_think"); leftover <think> blocks are stripped by _extract_json regardless.
_PROMPT_BODY = """You are the reasoning engine of an on-prem lead-qualification agent for BrightSmile Aesthetics, \
a cosmetic dental clinic. Given a call transcript and the clinic context, extract qualification \
slots, score the lead, and recommend the next best action. Apply the clinic's premium_lead_rules. \
Return ONLY a single valid JSON object, no prose, no markdown fences, with exactly these keys: \
summary (string), extracted (object: service_interest[], timeline, deadline_weeks, urgency[low|medium|high], \
financing_interest(bool), budget_signal, insurance_mentioned(bool), decision_stage[researching|comparing|ready_to_book]), \
score (object: label[hot|warm|cold], value(0-100), confidence(0-1), reason_tags[], urgency_reasoning), \
estimated_deal_value (object: currency, low, high, basis), \
clinic_context_hits (array of {label, value, source, matched}), \
next_best_action (object: recommendation, draft_followup, channel[call|sms|email]). \
Do not output chain-of-thought."""


def _build_system_prompt(thinking_directive: str) -> str:
    directive = (thinking_directive or "").strip()
    return f"{directive}\n{_PROMPT_BODY}" if directive else _PROMPT_BODY


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    """Pull a JSON object out of messy model output (reasoning tags, fences, prose)."""
    if not raw:
        return None
    # strip <think>...</think> reasoning blocks (Qwen3 / reasoning models)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    # strip ```json ... ``` fences
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        # else take the outermost { ... }
        start, end = raw.find("{"), raw.rfind("}")
        candidate = raw[start:end + 1] if (start != -1 and end > start) else raw
    try:
        return json.loads(candidate)
    except Exception:
        return None


class _OpenAICompatInferenceAdapter(InferenceAdapter):
    """Shared logic for any OpenAI-compatible chat endpoint (Hermes or direct Ollama)."""

    #: subclasses set these
    source_label: str = "remote"

    def __init__(self) -> None:
        self._fallback = MockInferenceAdapter()

    # --- subclass hooks -------------------------------------------------
    def _base_url(self) -> str: raise NotImplementedError
    def _api_key(self) -> str: raise NotImplementedError
    def _model(self) -> str: raise NotImplementedError          # "" => let the server pick its default
    def _read_timeout(self) -> float: raise NotImplementedError
    def _thinking_directive(self) -> str: return config.QWEN_THINKING_DIRECTIVE

    def _call_model(self, transcript, clinic_context) -> Optional[Dict[str, Any]]:
        user = json.dumps({"transcript": transcript, "clinic_context": clinic_context}, ensure_ascii=False)
        base_payload: Dict[str, Any] = {
            "messages": [
                {"role": "system", "content": _build_system_prompt(self._thinking_directive())},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 1400,
        }
        model = self._model()
        if model:  # omit when blank so the server uses its configured default (Qwen3-30B)
            base_payload["model"] = model

        headers = {"Content-Type": "application/json"}
        key = self._api_key()
        if key and key != "not-needed":
            headers["Authorization"] = f"Bearer {key}"
        url = f"{self._base_url()}/chat/completions"

        # Fail fast if the host is unreachable (5s connect), but allow a slow model to think.
        timeout = httpx.Timeout(connect=5.0, read=self._read_timeout(), write=10.0, pool=5.0)

        # Try JSON mode first; some servers 400 on response_format -> retry without it.
        for payload in ({**base_payload, "response_format": {"type": "json_object"}}, base_payload):
            try:
                resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                parsed = _extract_json(content)
                if parsed:
                    return parsed
            except httpx.HTTPStatusError:
                continue  # try the no-response_format variant
            except Exception:
                return None
        return None

    def analyze(self, transcript: List[Dict[str, Any]], clinic_context: Dict[str, Any]) -> Dict[str, Any]:
        # 1) complete skeleton from the heuristic so nothing downstream is ever missing
        result = self._fallback.analyze(transcript, clinic_context)
        # 2) real model
        parsed = self._call_model(transcript, clinic_context)
        if not parsed:
            result["_source"] = "mock_fallback"
            return result
        # 3) overlay non-empty model fields
        for k in _OVERLAY_KEYS:
            v = parsed.get(k)
            if v not in (None, "", [], {}):
                result[k] = v
        result["_source"] = self.source_label
        return result


class HermesInferenceAdapter(_OpenAICompatInferenceAdapter):
    """REAL path: reason via Hermes, which delegates to its local default model (Qwen3-30B)."""
    source_label = "hermes"

    def _base_url(self) -> str: return f"{config.HERMES_BASE_URL}/v1"
    def _api_key(self) -> str: return config.HERMES_API_KEY
    def _model(self) -> str: return config.HERMES_INFERENCE_MODEL
    def _read_timeout(self) -> float: return config.HERMES_TIMEOUT_READ


class QwenInferenceAdapter(_OpenAICompatInferenceAdapter):
    """FALLBACK path: call the local Ollama OpenAI endpoint directly (Hermes bypassed)."""
    source_label = "qwen"

    def _base_url(self) -> str: return config.QWEN_BASE_URL
    def _api_key(self) -> str: return config.QWEN_API_KEY
    def _model(self) -> str: return config.QWEN_MODEL
    def _read_timeout(self) -> float: return config.QWEN_TIMEOUT_READ
