import pytest
from pydantic import ValidationError

from course_generator.models import (
    ConfigError,
    Lesson,
    Quiz,
    QuizQuestion,
    validate_course_config,
)
from tests.factories import lesson_dict, quiz_dict


def test_valid_config_is_normalised():
    config = validate_course_config("  Python   basics ", "Beginner", 3)
    assert config.topic == "Python basics"
    assert (config.level, config.num_lessons) == ("Beginner", 3)


@pytest.mark.parametrize(
    "topic, level, n",
    [
        ("", "Beginner", 3),
        ("   ", "Beginner", 3),
        ("ab", "Beginner", 3),
        ("!!!???", "Beginner", 3),
        ("x" * 101, "Beginner", 3),
        ("Python", "Expert", 3),
        ("Python", "Beginner", 1),
        ("Python", "Beginner", 6),
        ("Python", "Beginner", True),
    ],
)
def test_invalid_config_rejected(topic, level, n):
    with pytest.raises(ConfigError):
        validate_course_config(topic, level, n)


@pytest.mark.parametrize("n", [2, 5])
def test_lesson_count_boundaries_allowed(n):
    assert validate_course_config("Python", "Advanced", n).num_lessons == n


@pytest.mark.parametrize("sections", [2, 3, 4])
def test_lesson_accepts_2_to_4_sections(sections):
    assert len(Lesson.model_validate(lesson_dict(sections=sections)).sections) == sections


@pytest.mark.parametrize("kwargs", [{"sections": 1}, {"sections": 5}, {"exercises": 1}, {"exercises": 3}])
def test_lesson_rejects_wrong_counts(kwargs):
    with pytest.raises(ValidationError):
        Lesson.model_validate(lesson_dict(**kwargs))


def test_quiz_requires_exactly_five_questions():
    for n in (4, 6):
        with pytest.raises(ValidationError):
            Quiz.model_validate(quiz_dict(n))


def test_question_needs_four_distinct_options():
    base = quiz_dict(1)["questions"][0]
    with pytest.raises(ValidationError):
        QuizQuestion.model_validate({**base, "options": ["a", "b", "c"]})
    with pytest.raises(ValidationError):
        QuizQuestion.model_validate({**base, "options": ["a", "A", "c", "d"]})
    with pytest.raises(ValidationError):
        QuizQuestion.model_validate({**base, "correct_index": 4})


def test_question_accepts_letter_answer_and_prefixed_options():
    base = quiz_dict(1)["questions"][0]
    q = QuizQuestion.model_validate(
        {**base, "options": ["A) one", "B) two", "C) three", "D) four"], "correct_index": "C"}
    )
    assert q.options == ["one", "two", "three", "four"]
    assert q.correct_index == 2
