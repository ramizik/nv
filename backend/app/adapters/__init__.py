"""Adapter factory. main/services call get_inference_adapter()/get_chat_adapter()
and never know whether they're talking to a mock or the real GB10 box."""
from app import config
from app.adapters.base import InferenceAdapter, ChatAdapter
from app.adapters.mock import MockInferenceAdapter
from app.adapters.chat import MockChatAdapter, DiscordChatAdapter


def get_inference_adapter() -> InferenceAdapter:
    if config.INFERENCE_BACKEND == "nemotron":
        # Imported lazily so the demo never fails to boot if httpx/endpoint is unhappy
        from app.adapters.nemotron import NemotronInferenceAdapter
        return NemotronInferenceAdapter()
    return MockInferenceAdapter()


def get_chat_adapter() -> ChatAdapter:
    if config.CHAT_BACKEND == "discord" and config.DISCORD_WEBHOOK_URL:
        return DiscordChatAdapter()
    return MockChatAdapter()
