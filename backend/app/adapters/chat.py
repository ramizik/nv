"""ChatAdapter implementations — how the staff alert gets delivered.

The REAL production path is `HermesChatAdapter`: Hermes (the teammate's running
service on the GB10) OWNS the Discord bot + channel, so we hand the alert off to it
rather than posting Discord ourselves. We never duplicate Hermes' Discord wiring.

  MockChatAdapter   : returns the alert markdown as a preview (sent=True so the demo
                      timeline reads 'posted'). Zero deps — the default.
  HermesChatAdapter : delivers the alert via Hermes. PRIMARY = the webhook platform in
                      `deliver_only` mode (deliver: discord) — no LLM, on-box, verbatim,
                      sub-second. FALLBACK = POST /v1/chat/completions (needs the gateway
                      bearer; routes through the cloud agent model). Fail-safe to preview.
  DiscordChatAdapter: secondary/standalone fallback — raw Discord webhook (no bot).
                      Use only if Hermes is unavailable and you own a webhook URL.
"""
import hashlib
import hmac
import json
from typing import Any, Dict

import httpx

from app import config
from app.adapters.base import ChatAdapter


def build_alert_markdown(analysis: Dict[str, Any]) -> str:
    lead = analysis.get("lead", {})
    score = analysis.get("score", {})
    ext = analysis.get("extracted", {})
    deal = analysis.get("estimated_deal_value", {})
    nba = analysis.get("next_best_action", {})
    emoji = {"hot": "🔥", "warm": "🌤️", "cold": "❄️"}.get(score.get("label"), "📞")
    hours = "after hours" if analysis.get("after_hours") else "business hours"
    svc = ", ".join(ext.get("service_interest") or ["—"])
    return (
        f"{emoji} **{score.get('label', '').upper()} LEAD — {hours}** • BrightSmile Aesthetics\n"
        f"**{lead.get('name', 'Unknown caller')}** · 📞 {lead.get('phone', 'n/a')}\n"
        f"**Wants:** {svc} · **Timeline:** {ext.get('timeline', 'n/a')}\n"
        f"**Score:** {score.get('label', '').upper()} {score.get('value', '?')}/100 "
        f"(conf {score.get('confidence', '?')}) · **Est. value:** ${deal.get('low', 0):,}–${deal.get('high', 0):,}\n"
        f"**Why:** {' · '.join(score.get('reason_tags', []))}\n"
        f"**Next best action:** {nba.get('recommendation', '')}\n"
        f"_Caught by the Local Voice Lead Closer — running locally on Dell Pro Max GB10._"
    )


class MockChatAdapter(ChatAdapter):
    def send(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {"platform": "mock", "sent": True, "preview_markdown": build_alert_markdown(analysis)}


# Fail fast if Hermes is unreachable (4s connect) so the dashboard never freezes.
_HERMES_TIMEOUT = httpx.Timeout(connect=4.0, read=12.0, write=5.0, pool=5.0)


class HermesChatAdapter(ChatAdapter):
    """Deliver the alert through Hermes, which owns the Discord bot + #front-desk channel.

    PRIMARY — webhook `deliver_only` (deliver: discord). When HERMES_WEBHOOK_URL is set we POST
    the markdown straight to a Hermes webhook route the owner adds in ~/.hermes/config.yaml.
    deliver_only skips the agent entirely: the posted body IS the Discord message. No model,
    on-box, deterministic, sub-second — exactly what a live demo needs. Optional per-route HMAC
    (HERMES_WEBHOOK_SECRET); blank = INSECURE_NO_AUTH demo mode.

    FALLBACK — POST /v1/chat/completions. Routes through Hermes' agent + its local default
    model (Qwen3-30B on the GB10 — on-box, NOT cloud) and REQUIRES the gateway bearer
    (HERMES_API_KEY = API_SERVER_KEY). Still on-prem, but LLM-mediated so non-deterministic;
    used only when no webhook URL is configured.

    Either path is fail-safe: never raises; degrades to the preview so the dashboard always renders.
    """

    def send(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        md = build_alert_markdown(analysis)
        if config.HERMES_WEBHOOK_URL:
            return self._send_via_webhook(md)
        return self._send_via_chat(md)

    def _send_via_webhook(self, md: str) -> Dict[str, Any]:
        # Body fields are co-designed with the route template in config.yaml: the template
        # renders `content` as the message; `chat_id` overrides the channel (else the route's
        # default = Discord home channel 1509734278206984194). Serialize once so the bytes we
        # sign are exactly the bytes we send.
        raw = json.dumps({"content": md, "chat_id": config.HERMES_DISCORD_CHANNEL}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if config.HERMES_WEBHOOK_SECRET:
            # HMAC-SHA256 hex over the raw body. NOTE: confirm header name + scheme against
            # gateway/platforms/webhook.py; for the demo INSECURE_NO_AUTH (blank secret) is fine.
            sig = hmac.new(config.HERMES_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
            headers["X-Signature"] = f"sha256={sig}"
        try:
            resp = httpx.post(config.HERMES_WEBHOOK_URL, content=raw, headers=headers, timeout=_HERMES_TIMEOUT)
            resp.raise_for_status()
            return {"platform": "hermes", "sent": True, "preview_markdown": md}
        except Exception as e:  # never let a chat failure break the demo
            return {"platform": "hermes", "sent": False, "preview_markdown": md, "error": str(e)}

    def _send_via_chat(self, md: str) -> Dict[str, Any]:
        instruction = (
            f"Post the following lead alert verbatim to Discord channel "
            f"{config.HERMES_DISCORD_CHANNEL}. Do not summarize or add commentary.\n\n{md}"
        )
        payload = {"messages": [
            {"role": "system", "content": "You relay pre-formatted staff alerts to Discord exactly as given."},
            {"role": "user", "content": instruction},
        ]}
        # The gateway requires its bearer on every route (_check_auth → 401 invalid_api_key).
        headers = {"Content-Type": "application/json"}
        if config.HERMES_API_KEY:
            headers["Authorization"] = f"Bearer {config.HERMES_API_KEY}"
        try:
            resp = httpx.post(f"{config.HERMES_BASE_URL}/v1/chat/completions",
                              json=payload, headers=headers, timeout=_HERMES_TIMEOUT)
            resp.raise_for_status()
            return {"platform": "hermes", "sent": True, "preview_markdown": md}
        except Exception as e:  # never let a chat failure break the demo
            return {"platform": "hermes", "sent": False, "preview_markdown": md, "error": str(e)}


class DiscordChatAdapter(ChatAdapter):
    def send(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        md = build_alert_markdown(analysis)
        try:
            resp = httpx.post(config.DISCORD_WEBHOOK_URL, json={"content": md}, timeout=8.0)
            resp.raise_for_status()
            return {"platform": "discord", "sent": True, "preview_markdown": md}
        except Exception as e:  # never let a chat failure break the demo
            return {"platform": "discord", "sent": False, "preview_markdown": md, "error": str(e)}
