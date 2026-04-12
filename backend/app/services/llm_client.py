"""
Single Anthropic client used by all services.
All LLM calls go through here — one place to swap models, add retries, log tokens.
"""

import anthropic

from app.core.config import settings

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def chat(system: str, user: str, max_tokens: int = 1024) -> str:
    """Simple single-turn call. Returns the text content."""
    client = get_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()


def chat_with_history(
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> str:
    """Multi-turn call. `messages` is a list of {role, content} dicts."""
    client = get_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return message.content[0].text.strip()
