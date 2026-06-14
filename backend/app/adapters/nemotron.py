"""NemotronInferenceAdapter — the REAL local-inference path on the GB10 box.

Talks to an OpenAI-compatible endpoint (vLLM / NIM / TGI / Ollama) serving a Nemotron-family
model. Strategy chosen for hackathon reliability:

  1. Run the mock heuristic FIRST to get a COMPLETE LeadAnalysis skeleton.
  2. Ask the model for the same JSON; robustly parse it (handles <think> reasoning tags,
     ```json fences, and leading/trailing prose).
  3. OVERLAY the model's non-empty fields onto the skeleton — so even if the model omits
     estimated_deal_value or context hits, the dashboard still gets a full object.
  4. On ANY error, return the mock skeleton. The demo can never hard-fail.

Enable with:  INFERENCE_BACKEND=nemotron  NEMOTRON_BASE_URL=http://127.0.0.1:11434/v1
              NEMOTRON_MODEL=lifeos-nemotron-120b:latest   (Ollama on the GB10, no API key)
Nemotron reasoning toggle: we prepend "detailed thinking off" so output is clean JSON. Even if
the model still emits <think> blocks, _extract_json strips them — so this is robust either way.
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

SYSTEM_PROMPT = """detailed thinking off
You are the reasoning engine of an on-prem lead-qualification agent for BrightSmile Aesthetics, \
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


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    """Pull a JSON object out of messy model output (reasoning tags, fences, prose)."""
    if not raw:
        return None
    # strip <think>...</think> reasoning blocks (Nemotron reasoning models)
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


class NemotronInferenceAdapter(InferenceAdapter):
    def __init__(self) -> None:
        self._fallback = MockInferenceAdapter()

    def _call_model(self, transcript, clinic_context) -> Optional[Dict[str, Any]]:
        user = json.dumps({"transcript": transcript, "clinic_context": clinic_context}, ensure_ascii=False)
        base_payload = {
            "model": config.NEMOTRON_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 1400,
        }
        headers = {"Authorization": f"Bearer {config.NEMOTRON_API_KEY}"}
        url = f"{config.NEMOTRON_BASE_URL}/chat/completions"

        # Fail fast if the host is unreachable (5s connect), but allow a slow model to think
        # (NEMOTRON_TIMEOUT_READ, default 90s — the 120B can be slow on a cold first token).
        # Without the short connect timeout a bad URL stalls the whole demo. PRE-WARM the model.
        timeout = httpx.Timeout(connect=5.0, read=config.NEMOTRON_TIMEOUT_READ, write=10.0, pool=5.0)

        # Try with JSON mode first; some servers 400 on response_format -> retry without it.
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
        result["_source"] = "nemotron"
        return result
