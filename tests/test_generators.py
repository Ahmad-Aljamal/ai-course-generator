import random

import pytest

from course_generator.generators import (
    generate_lesson,
    generate_outline,
    generate_quiz,
    lesson_to_text,
)
from course_generator.llm import InvalidResponseError
from course_generator.models import CourseOutline, Lesson, validate_course_config
from tests.factories import FakeClient, lesson_dict, outline_dict, quiz_dict


@pytest.fixture
def config():
    return validate_course_config("SQL", "Beginner", 3)


@pytest.fixture
def outline():
    return CourseOutline.model_validate(outline_dict(3))


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_outline_has_exact_lesson_count(n):
    config = validate_course_config("SQL", "Intermediate", n)
    outline = generate_outline(config, client=FakeClient([outline_dict(n)]))
    assert len(outline.lessons) == n
    assert all(l.title and l.objectives and l.summary for l in outline.lessons)


def test_outline_with_wrong_count_is_retried(config):
    client = FakeClient([outline_dict(2), outline_dict(3)])
    assert len(generate_outline(config, client=client).lessons) == 3
    assert "exactly 3 lessons" in client.calls[1]["messages"][-1]["content"]


def test_outline_wrong_count_every_time_fails(config):
    with pytest.raises(InvalidResponseError):
        generate_outline(config, client=FakeClient([outline_dict(4)] * 3))


def test_outline_missing_fields_fails(config):
    broken = outline_dict(3)
    del broken["lessons"][1]["summary"]
    with pytest.raises(InvalidResponseError):
        generate_outline(config, client=FakeClient([broken] * 3))


def test_lesson_has_all_required_parts(config, outline):
    lesson = generate_lesson(config, outline, 1, client=FakeClient([lesson_dict()]))
    assert lesson.introduction and lesson.summary
    assert 2 <= len(lesson.sections) <= 4
    assert all(s.heading and s.explanation and s.example for s in lesson.sections)
    assert len(lesson.exercises) == 2
    assert all(e.prompt and e.hint for e in lesson.exercises)


def test_lesson_prompt_targets_selected_lesson(config, outline):
    client = FakeClient([lesson_dict()])
    generate_lesson(config, outline, 2, client=client)
    assert "This lesson: \"Topic 3\"" in client.calls[0]["messages"][-1]["content"]


def test_quiz_has_five_questions_with_four_options(config, outline):
    lesson = Lesson.model_validate(lesson_dict())
    quiz = generate_quiz(config, outline, 0, lesson, client=FakeClient([quiz_dict()]))
    assert len(quiz.questions) == 5
    assert all(len(q.options) == 4 and q.explanation for q in quiz.questions)


def test_shuffling_keeps_correct_answer_correct(config, outline):
    lesson = Lesson.model_validate(lesson_dict())
    quiz = generate_quiz(
        config, outline, 0, lesson, client=FakeClient([quiz_dict()]), rng=random.Random(7)
    )
    for q in quiz.questions:
        assert q.options[q.correct_index] == "Right"
        assert sorted(q.options) == ["Right", "Wrong 1", "Wrong 2", "Wrong 3"]


def test_quiz_prompt_contains_lesson_text(config, outline):
    lesson = Lesson.model_validate(lesson_dict())
    client = FakeClient([quiz_dict()])
    generate_quiz(config, outline, 0, lesson, client=client)
    assert "Intro text." in client.calls[0]["messages"][-1]["content"]
    assert "Heading 0" in lesson_to_text("Topic 1", lesson)
