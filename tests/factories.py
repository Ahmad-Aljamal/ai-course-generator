"""Builders for valid AI-style JSON payloads and a fake Groq client."""
import json
from types import SimpleNamespace


def outline_dict(n=3):
    return {
        "title": "Introduction to SQL",
        "description": "Learn to query relational databases.",
        "objectives": ["Write queries", "Join tables", "Filter data"],
        "lessons": [
            {
                "title": f"Topic {i + 1}",
                "objectives": ["Understand it", "Use it"],
                "summary": f"Summary {i + 1}.",
            }
            for i in range(n)
        ],
    }


def lesson_dict(sections=3, exercises=2):
    return {
        "introduction": "Intro text.",
        "sections": [
            {"heading": f"Heading {i}", "explanation": "Explained.", "example": "Example."}
            for i in range(sections)
        ],
        "summary": "Recap.",
        "exercises": [{"prompt": f"Do task {i}", "hint": "Think."} for i in range(exercises)],
    }


def quiz_dict(n=5):
    return {
        "questions": [
            {
                "question": f"Question {i}?",
                "options": ["Right", "Wrong 1", "Wrong 2", "Wrong 3"],
                "correct_index": 0,
                "explanation": "Because.",
            }
            for i in range(n)
        ]
    }


class FakeClient:
    """Mimics `groq.Groq().chat.completions.create` with scripted replies.

    Each item is either a string/dict (returned as the message content)
    or an Exception (raised).
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        content = item if isinstance(item, str) else json.dumps(item)
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])
