"""Adapter interfaces — the two swap-points of the system.

InferenceAdapter: transcript + clinic_context -> analysis fields (extract/score/etc).
ChatAdapter: an analysis -> a posted staff alert.

Keep these stable. Mock and real implementations must honor the same contract so we
can flip INFERENCE_BACKEND / CHAT_BACKEND with zero changes upstream.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class InferenceAdapter(ABC):
    @abstractmethod
    def analyze(self, transcript: List[Dict[str, Any]], clinic_context: Dict[str, Any]) -> Dict[str, Any]:
        """Return a partial LeadAnalysis dict with at least:
        summary, extracted, score, estimated_deal_value, clinic_context_hits, next_best_action.
        """
        raise NotImplementedError


class ChatAdapter(ABC):
    @abstractmethod
    def send(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Post the alert. Return a `notification` dict: {platform, sent, preview_markdown}."""
        raise NotImplementedError
