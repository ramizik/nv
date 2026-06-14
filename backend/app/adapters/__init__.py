"""Adapter factory. main/services call get_inference_adapter()/get_chat_adapter()
and never know whether they're talking to a mock or the real GB10 box."""
from app import config
from app.adapters.base import InferenceAdapter, ChatAdapter
from app.adapters.mock import MockInferenceAdapter
from app.adapters.chat import MockChatAdapter, HermesChatAdapter, DiscordChatAdapter


def get_inference_adapter() -> InferenceAdapter:
    # Imported lazily so the demo never fails to boot if httpx/endpoint is unhappy.
    # 'qwen'/'nemotron' = primary GB10 path: direct local Qwen through Ollama.
    # 'hermes' = gateway path: use Hermes' configured provider.
    if config.INFERENCE_BACKEND == "hermes":
        from app.adapters.inference import HermesInferenceAdapter
        return HermesInferenceAdapter()
    if config.INFERENCE_BACKEND in ("qwen", "nemotron"):
        from app.adapters.inference import QwenInferenceAdapter
        return QwenInferenceAdapter()
    return MockInferenceAdapter()


def get_chat_adapter() -> ChatAdapter:
    # 'hermes' = hand off to the teammate's bot/gateway; 'discord' = raw webhook fallback;
    # anything else stays on the safe mock preview.
    if config.CHAT_BACKEND == "hermes":
        return HermesChatAdapter()
    if config.CHAT_BACKEND == "discord" and config.DISCORD_WEBHOOK_URL:
        return DiscordChatAdapter()
    return MockChatAdapter()
