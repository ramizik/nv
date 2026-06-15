"""Send appointment-confirmation emails via the Gmail API.

Uses the on-box Google OAuth token (refresh_token + gmail.send scope) at
config.GMAIL_TOKEN_PATH — no SMTP password, no new deps (httpx only). Every call is
FAIL-SAFE: it never raises; on any error it returns {"sent": False, "error": ...} so a
mail hiccup can never break the scheduling flow or the demo.

Recipients are fixed (config.APPOINTMENT_EMAIL_RECIPIENTS) per the requirement that EVERY
scheduled appointment notifies the clinic owners.
"""
import base64
import json
from email.mime.text import MIMEText
from typing import Any, Dict, List

import httpx

from app import config

_TOKEN_URI_DEFAULT = "https://oauth2.googleapis.com/token"
_GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _load_token() -> Dict[str, Any]:
    return json.loads(config.GMAIL_TOKEN_PATH.read_text(encoding="utf-8"))


def _access_token(tok: Dict[str, Any]) -> str:
    """Exchange the refresh token for a fresh access token."""
    resp = httpx.post(
        tok.get("token_uri", _TOKEN_URI_DEFAULT),
        data={
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "client_id": tok["client_id"],
            "client_secret": tok["client_secret"],
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _build_raw(sender: str, recipients: List[str], subject: str, body: str) -> str:
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = ", ".join(recipients)
    msg["From"] = sender
    msg["Subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def send_email(subject: str, body: str, recipients: List[str] | None = None) -> Dict[str, Any]:
    """Send a plain-text email to the configured clinic recipients. Never raises."""
    to = recipients or config.APPOINTMENT_EMAIL_RECIPIENTS
    try:
        tok = _load_token()
        sender = tok.get("account") or "me"
        access = _access_token(tok)
        raw = _build_raw(sender, to, subject, body)
        resp = httpx.post(
            _GMAIL_SEND_URL,
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
            json={"raw": raw},
            timeout=20.0,
        )
        resp.raise_for_status()
        return {"sent": True, "to": to, "from": sender, "id": resp.json().get("id")}
    except Exception as e:  # never break the scheduling flow
        return {"sent": False, "to": to, "error": str(e)}


def appointment_email(lead: Dict[str, Any], appt: Dict[str, Any]) -> Dict[str, Any]:
    """Compose + send the appointment-confirmation email for a scheduled patient."""
    person = lead.get("lead", {})
    ext = lead.get("extracted", {})
    score = lead.get("score", {})
    deal = lead.get("estimated_deal_value", {})
    name = person.get("name", "Unknown caller")
    services = ", ".join(ext.get("service_interest") or ["—"])
    subject = f"[BrightSmile] Appointment scheduled — {name} ({services})"
    body = (
        f"A consultation has been scheduled for an inbound lead.\n\n"
        f"Patient:        {name}\n"
        f"Phone:          {person.get('phone', 'n/a')}\n"
        f"Service:        {services}\n"
        f"Appointment:    {appt.get('when') or 'to be confirmed with patient'}\n"
        f"Timeline:       {ext.get('timeline', 'n/a')}\n"
        f"Lead score:     {str(score.get('label', '')).upper()} {score.get('value', '?')}/100\n"
        f"Est. value:     ${deal.get('low', 0):,}-${deal.get('high', 0):,}\n"
        f"After hours:    {'yes' if lead.get('after_hours') else 'no'}\n"
        f"Notes:          {appt.get('notes') or '—'}\n\n"
        f"Lead ID {lead.get('lead_id')} — auto-sent by the Local Voice Lead Closer (GB10, on-prem)."
    )
    return send_email(subject, body)
