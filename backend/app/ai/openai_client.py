"""
Shared OpenAI client wrapper.

Centralizes: client construction, retries, timeouts, and enforcing
structured JSON output. Every AI feature (Recruitment Officer, Community
Manager, Event Planner, etc.) calls `ask_for_json()` instead of touching
the OpenAI SDK directly, so retry/error handling logic lives in one place.
"""
from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("guildos.ai.client")

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_TIMEOUT_SECONDS)


class AIServiceError(Exception):
    """Raised when the AI backend fails after all retries are exhausted."""


@retry(
    retry=retry_if_exception_type((APIError, APITimeoutError, RateLimitError)),
    stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _create_completion(system_prompt: str, user_prompt: str) -> str:
    response = await _client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return response.choices[0].message.content or "{}"


async def ask_for_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Send a prompt to the model and parse the JSON response.

    Raises `AIServiceError` if the call fails after retries or the model
    returns content that isn't valid JSON — callers should catch this and
    degrade gracefully (e.g. flag for manual review) rather than crash.
    """
    try:
        raw = await _create_completion(system_prompt, user_prompt)
    except (APIError, APITimeoutError, RateLimitError) as exc:
        logger.error("OpenAI request failed after retries: %s", exc)
        raise AIServiceError(str(exc)) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("OpenAI returned non-JSON content: %s", raw[:500])
        raise AIServiceError("Model returned invalid JSON") from exc
