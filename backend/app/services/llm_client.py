"""
Single Groq client used by all services.
All LLM calls go through here — one place to swap models, add retries, log tokens.
"""

from groq import Groq

from app.core.config import settings

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat(system: str, user: str, max_tokens: int = 1024) -> str:
    """Simple single-turn call. Returns the text content."""
    client = get_client()
    completion = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return completion.choices[0].message.content.strip()


def chat_with_history(
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> str:
    """Multi-turn call. `messages` is a list of {role, content} dicts."""
    client = get_client()
    completion = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, *messages],
    )
    return completion.choices[0].message.content.strip()
