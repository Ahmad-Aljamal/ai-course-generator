"""Groq connection, error handling and structured (JSON) generation."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, TypeVar

import groq
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # reads GROQ_API_KEY from a local .env file, if present

MODEL = "openai/gpt-oss-20b"
_PLACEHOLDER_KEYS = {"", "your_api_key_here", "your-api-key-here"}

SYSTEM_PROMPT = (
    "You are an expert curriculum designer and teacher. You write accurate, "
    "clear and engaging educational content. You always answer with valid JSON only."
)

T = TypeVar("T", bound=BaseModel)


class CourseGeneratorError(Exception):
    """Base class for errors whose message can be shown directly to the user."""


class MissingAPIKeyError(CourseGeneratorError):
    pass


class GroqAPIError(CourseGeneratorError):
    pass


class InvalidResponseError(CourseGeneratorError):
    pass


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
def get_api_key() -> str | None:
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    return None if key in _PLACEHOLDER_KEYS else key


def api_key_configured() -> bool:
    return get_api_key() is not None


def get_client() -> groq.Groq:
    key = get_api_key()
    if key is None:
        raise MissingAPIKeyError(
            "No Groq API key found. Copy .env.example to .env, set GROQ_API_KEY "
            "to your key from https://console.groq.com/keys, then restart the app."
        )
    return groq.Groq(api_key=key, timeout=90.0, max_retries=2)


def chat(
    messages: list[dict[str, str]],
    *,
    client: Any | None = None,
    json_mode: bool = False,
    temperature: float = 0.4,
    max_tokens: int = 8192,
) -> str:
    """Send a chat request to Groq and return the text of the reply."""
    client = client or get_client()
    kwargs: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "reasoning_effort": "low",  # keeps gpt-oss fast and cheap for this task
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except groq.AuthenticationError as exc:
        raise GroqAPIError(
            "Groq rejected the API key. Check GROQ_API_KEY in your .env file."
        ) from exc
    except groq.RateLimitError as exc:
        raise GroqAPIError("Groq rate limit reached. Wait a moment and try again.") from exc
    except groq.APIConnectionError as exc:  # includes timeouts
        raise GroqAPIError(
            "Could not reach Groq. Check your internet connection and try again."
        ) from exc
    except groq.BadRequestError as exc:
        if "json_validate_failed" in str(exc):
            raise InvalidResponseError("The AI returned malformed JSON.") from exc
        raise GroqAPIError(f"Groq could not process the request: {exc}") from exc
    except groq.APIStatusError as exc:
        raise GroqAPIError(
            f"Groq returned an error (HTTP {exc.status_code}). Try again shortly."
        ) from exc

    if not getattr(response, "choices", None):
        raise InvalidResponseError("The AI returned an empty response.")
    choice = response.choices[0]
    if getattr(choice, "finish_reason", None) == "length":
        raise InvalidResponseError("The AI response was cut off before it finished.")
    content = choice.message.content
    if not content or not content.strip():
        raise InvalidResponseError("The AI returned an empty response.")
    return content


# --------------------------------------------------------------------------- #
# Structured output
# --------------------------------------------------------------------------- #
def extract_json(text: str) -> Any:
    """Parse a JSON object from model output (tolerates code fences / chatter)."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def generate_structured(
    prompt: str,
    model_cls: type[T],
    *,
    client: Any | None = None,
    system: str = SYSTEM_PROMPT,
    check: Callable[[T], None] | None = None,
    max_attempts: int = 3,
    temperature: float = 0.4,
    max_tokens: int = 8192,
) -> T:
    """Ask Groq for JSON, validate it with Pydantic and retry on bad output.

    `check` may raise ValueError for extra rules (e.g. an exact lesson count);
    the error message is sent back to the model on the next attempt.
    """
    client = client or get_client()
    schema = json.dumps(model_cls.model_json_schema())
    messages = [
        {
            "role": "system",
            "content": f"{system}\n\nReturn ONLY one JSON object that matches this "
            f"JSON Schema (no markdown, no commentary):\n{schema}",
        },
        {"role": "user", "content": prompt},
    ]

    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            raw = chat(
                messages,
                client=client,
                json_mode=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except InvalidResponseError as exc:  # empty / truncated / malformed JSON
            last_error = exc
            continue

        try:
            result = model_cls.model_validate(extract_json(raw))
            if check is not None:
                check(result)
            return result
        except ValueError as exc:  # JSONDecodeError and pydantic.ValidationError
            last_error = exc
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": "That response was not valid: "
                    f"{str(exc)[:600]}\nReturn the complete, corrected JSON object only.",
                }
            )

    raise InvalidResponseError(
        "The AI returned an incomplete or invalid response. Please try again."
    ) from last_error
