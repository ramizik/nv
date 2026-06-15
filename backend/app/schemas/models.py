"""Request/response models. The LeadAnalysis object itself is passed as a dict
(its contract lives in shared/schemas/lead_analysis.schema.json) to stay fast and
avoid friction when adapters add fields. We only strongly type the inbound request.
"""
from typing import List, Optional
from pydantic import BaseModel


class TranscriptTurn(BaseModel):
    speaker: str  # 'lead' | 'agent'
    text: str
    ts: Optional[str] = None


class Lead(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """A live lead transcript (e.g. from a Discord voice/text interaction) to analyze."""
    transcript: Optional[List[TranscriptTurn]] = None
    lead: Optional[Lead] = None
    channel: str = "voice"
    after_hours: bool = True
    notify: bool = True  # whether to fire the chat alert
