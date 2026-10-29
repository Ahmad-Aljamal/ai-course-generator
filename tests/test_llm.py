import groq
import httpx
import pytest

from course_generator import llm
from course_generator.llm import (
    GroqAPIError,
    InvalidResponseError,
    MissingAPIKeyError,
    extract_json,
    generate_structured,
)
from course_generator.models import Quiz
from tests.factories import FakeClient, quiz_dict

REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def status_error(cls, code):
    return cls("boom", response=httpx.Response(code, request=REQUEST), body=None)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert not llm.api_key_configured()
    with pytest.raises(MissingAPIKeyError):
        llm.get_client()


def test_placeholder_key_counts_as_missing(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "your_api_key_here")
    assert not llm.api_key_configured()


def test_real_key_builds_client(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    assert llm.api_key_configured()
    assert llm.get_client() is not None


def test_uses_required_model_and_json_mode():
    client = FakeClient(["hello"])
    assert llm.chat([{"role": "user", "content": "hi"}], client=client, json_mode=True) == "hello"
    call = client.calls[0]
    assert call["model"] == "openai/gpt-oss-20b"
    assert call["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    "error, fragment",
    [
        (groq.APIConnectionError(request=REQUEST), "Could not reach Groq"),
        (status_error(groq.AuthenticationError, 401), "API key"),
        (status_error(groq.RateLimitError, 429), "rate limit"),
        (status_error(groq.InternalServerError, 500), "HTTP 500"),
    ],
)
def test_api_errors_become_friendly_errors(error, fragment):
    with pytest.raises(GroqAPIError, match=fragment):
        llm.chat([{"role": "user", "content": "hi"}], client=FakeClient([error]))


def test_extract_json_handles_fences_and_chatter():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 1} Hope that helps') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_invalid_json_is_retried_with_feedback():
    client = FakeClient(["not json", quiz_dict()])
    quiz = generate_structured("make quiz", Quiz, client=client)
    assert len(quiz.questions) == 5
    assert len(client.calls) == 2
    assert "not valid" in client.calls[1]["messages"][-1]["content"]


def test_incomplete_response_is_retried():
    client = FakeClient([quiz_dict(4), quiz_dict(5)])
    assert len(generate_structured("q", Quiz, client=client).questions) == 5


def test_gives_up_after_max_attempts():
    client = FakeClient(["bad", "bad", "bad"])
    with pytest.raises(InvalidResponseError):
        generate_structured("q", Quiz, client=client)
    assert len(client.calls) == 3


def test_connection_errors_are_not_retried():
    client = FakeClient([groq.APIConnectionError(request=REQUEST), quiz_dict()])
    with pytest.raises(GroqAPIError):
        generate_structured("q", Quiz, client=client)
    assert len(client.calls) == 1
