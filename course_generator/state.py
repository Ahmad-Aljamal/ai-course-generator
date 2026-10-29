"""Session-state helpers.

Everything is keyed by lesson index and scoped to a course, so lessons and
quizzes never leak into each other. The functions take any dict-like object,
which is `st.session_state` in the app and a plain dict in the tests.
"""
from __future__ import annotations

from typing import Any, MutableMapping

VIEWS = ("Outline", "Lesson", "Quiz")

_DEFAULTS = {
    "config": lambda: None,
    "course": lambda: None,
    "course_id": lambda: 0,  # bumps for every new course; used in widget keys
    "lessons": dict,  # lesson index -> Lesson
    "quizzes": dict,  # lesson index -> Quiz
    "quiz_results": dict,  # lesson index -> QuizResult
    "quiz_attempts": dict,  # lesson index -> retake counter (resets widget keys)
    "selected_lesson": lambda: 0,
    "view": lambda: VIEWS[0],
}


def init_state(state: MutableMapping[str, Any]) -> None:
    for key, factory in _DEFAULTS.items():
        if key not in state:
            state[key] = factory()


def start_new_course(state: MutableMapping[str, Any], config: Any, course: Any) -> None:
    """Replace the current course and discard all lessons, quizzes and results."""
    state["config"] = config
    state["course"] = course
    state["course_id"] = state.get("course_id", 0) + 1
    state["lessons"] = {}
    state["quizzes"] = {}
    state["quiz_results"] = {}
    state["quiz_attempts"] = {}
    state["selected_lesson"] = 0
    state["view"] = VIEWS[0]


def quiz_widget_key(state: MutableMapping[str, Any], lesson_index: int, question_index: int) -> str:
    """Unique widget key per course, lesson, attempt and question."""
    attempt = state["quiz_attempts"].get(lesson_index, 0)
    return f"quiz_{state['course_id']}_{lesson_index}_{attempt}_{question_index}"


def store_lesson(state: MutableMapping[str, Any], lesson_index: int, lesson: Any) -> None:
    state["lessons"][lesson_index] = lesson


def store_quiz(state: MutableMapping[str, Any], lesson_index: int, quiz: Any) -> None:
    state["quizzes"][lesson_index] = quiz


def store_result(state: MutableMapping[str, Any], lesson_index: int, result: Any) -> None:
    state["quiz_results"][lesson_index] = result


def retake_quiz(state: MutableMapping[str, Any], lesson_index: int) -> None:
    """Clear the result for one lesson and start a fresh attempt on the same questions."""
    state["quiz_results"].pop(lesson_index, None)
    state["quiz_attempts"][lesson_index] = state["quiz_attempts"].get(lesson_index, 0) + 1
