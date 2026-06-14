"""ChatAdapter implementations — how the staff alert gets delivered.

The REAL production path is `HermesChatAdapter`: Hermes (the teammate's running
service on the GB10) OWNS the Discord bot + channel, so we hand the alert off to it
rather than posting Discord ourselves. We never duplicate Hermes' Discord wiring.

  MockChatAdapter   : returns the alert markdown as a preview (sent=True so the demo
                      timeline reads 'posted'). Zero deps — the default.
  HermesChatAdapter : POSTs the alert to Hermes' OpenAI-compatible gateway (:8642) so
                      Hermes' bot relays it to #front-desk. Fail-safe to preview.
  DiscordChatAdapter: secondary/standalone fallback — raw Discord webhook (no bot).
                      Use only if Hermes is unavailable and you own a webhook URL.
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


class HermesChatAdapter(ChatAdapter):
    """Hand the alert to the teammate's Hermes service, which owns the Discord bot.

    PROVISIONAL CONTRACT: built against Hermes' CONFIRMED endpoint
    `POST {HERMES_BASE_URL}/v1/chat/completions`. Hermes runs LOCALLY on the box and needs
    no API key, so the bearer header is only sent if HERMES_API_KEY happens to be set. We ask
    the Hermes agent to post the pre-formatted alert to the staff channel.

    ⚠️ This routes a fixed message through an LLM agent, which is non-deterministic. The
    PREFERRED path is a thin, deterministic Hermes endpoint (e.g. POST /discord/send
    {channel, content}) — once the teammate exposes it, swap the body below to call it.
    See docs/hermes-integration.md. Either way: never raises; degrades to preview.
    """

    def send(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        md = build_alert_markdown(analysis)
        instruction = (
            f"Post the following lead alert verbatim to Discord channel "
            f"{config.HERMES_DISCORD_CHANNEL}. Do not summarize or add commentary.\n\n{md}"
        )
        payload = {
            "messages": [
                {"role": "system", "content": "You relay pre-formatted staff alerts to Discord exactly as given."},
                {"role": "user", "content": instruction},
            ],
        }
        # Hermes is local + keyless; only attach a bearer if one was explicitly configured.
        headers = {"Content-Type": "application/json"}
        if config.HERMES_API_KEY:
            headers["Authorization"] = f"Bearer {config.HERMES_API_KEY}"
        # Fail fast if Hermes is unreachable (4s connect) so the dashboard never freezes;
        # allow a little read room (12s) for the agent to relay. Same stance as nemotron.py.
        timeout = httpx.Timeout(connect=4.0, read=12.0, write=5.0, pool=5.0)
        try:
            resp = httpx.post(f"{config.HERMES_BASE_URL}/v1/chat/completions",
                              json=payload, headers=headers, timeout=timeout)
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
