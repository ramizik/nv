"""ChatAdapter implementations.

MockChatAdapter: builds the alert markdown and returns it as a preview (sent=False-ish
but we mark sent=True so the timeline reads 'posted' in the all-mock demo). Zero deps.
DiscordChatAdapter: POSTs the same markdown to a Discord webhook (just a URL — no bot).
"""
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


class DiscordChatAdapter(ChatAdapter):
    def send(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        md = build_alert_markdown(analysis)
        try:
            resp = httpx.post(config.DISCORD_WEBHOOK_URL, json={"content": md}, timeout=8.0)
            resp.raise_for_status()
            return {"platform": "discord", "sent": True, "preview_markdown": md}
        except Exception as e:  # never let a chat failure break the demo
            return {"platform": "discord", "sent": False, "preview_markdown": md, "error": str(e)}
