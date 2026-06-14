"""NemotronInferenceAdapter — the REAL local-inference path on the GB10 box.

Talks to an OpenAI-compatible endpoint (vLLM / NIM / TGI) serving Nemotron. It sends the
transcript + clinic context and asks for the SAME partial-LeadAnalysis JSON the mock
returns, so nothing upstream changes. On any error it falls back to the mock adapter so
the demo can never hard-fail.

Enable with:  INFERENCE_BACKEND=nemotron  NEMOTRON_BASE_URL=http://<gb10-host>:8000/v1
"""
import json
from typing import Any, Dict, List

import httpx

from app import config
from app.adapters.base import InferenceAdapter
from app.adapters.mock import MockInferenceAdapter

SYSTEM_PROMPT = """You are the reasoning engine of an on-prem lead-qualification agent for \
BrightSmile Aesthetics, a cosmetic dental clinic. Given a call transcript and the clinic context, \
extract qualification slots, score the lead, and recommend the next best action. \
Return ONLY valid JSON, no prose, with exactly these keys: \
summary (string), extracted (object: service_interest[], timeline, deadline_weeks, urgency[low|medium|high], \
financing_interest, budget_signal, insurance_mentioned, decision_stage[researching|comparing|ready_to_book]), \
score (object: label[hot|warm|cold], value 0-100, confidence 0-1, reason_tags[], urgency_reasoning), \
estimated_deal_value (object: currency, low, high, basis), \
clinic_context_hits (array of {label, value, source, matched}), \
next_best_action (object: recommendation, draft_followup, channel[call|sms|email]). \
Apply the clinic's premium_lead_rules. Do not output chain-of-thought."""


class NemotronInferenceAdapter(InferenceAdapter):
    def __init__(self) -> None:
        self._fallback = MockInferenceAdapter()

    def analyze(self, transcript: List[Dict[str, Any]], clinic_context: Dict[str, Any]) -> Dict[str, Any]:
        user = json.dumps({"transcript": transcript, "clinic_context": clinic_context}, ensure_ascii=False)
        payload = {
            "model": config.NEMOTRON_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "max_tokens": 1200,
        }
        headers = {"Authorization": f"Bearer {config.NEMOTRON_API_KEY}"}
        try:
            resp = httpx.post(f"{config.NEMOTRON_BASE_URL}/chat/completions",
                              json=payload, headers=headers, timeout=45.0)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            # Reliability over purity: degrade to mock so the demo always renders.
            out = self._fallback.analyze(transcript, clinic_context)
            out.setdefault("_warnings", []).append(f"nemotron fallback: {e}")
            return out
