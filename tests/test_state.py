"""Lesson switching, quiz isolation and retakes (state logic runs on a plain dict)."""
import pytest

from course_generator import state as S
from course_generator.grading import grade_quiz
from course_generator.models import (
    CourseOutline,
    Lesson,
    Quiz,
    validate_course_config,
)
from tests.factories import lesson_dict, outline_dict, quiz_dict


@pytest.fixture
def st():
    state = {}
    S.init_state(state)
    config = validate_course_config("SQL", "Beginner", 3)
    S.start_new_course(state, config, CourseOutline.model_validate(outline_dict(3)))
    return state


def make_quiz(correct):
    data = quiz_dict()
    for q in data["questions"]:
        q["correct_index"] = correct
    return Quiz.model_validate(data)


def test_init_state_is_idempotent_and_keeps_data(st):
    st["lessons"][0] = "kept"
    S.init_state(st)
    assert st["lessons"][0] == "kept"


def test_lessons_are_kept_when_switching(st):
    lesson_a, lesson_b = Lesson.model_validate(lesson_dict(2)), Lesson.model_validate(lesson_dict(4))
    S.store_lesson(st, 0, lesson_a)
    S.store_lesson(st, 1, lesson_b)
    st["selected_lesson"] = 0
    st["selected_lesson"] = 1
    st["selected_lesson"] = 0
    assert st["lessons"][0] is lesson_a and st["lessons"][1] is lesson_b
    assert 2 not in st["lessons"]


def test_quiz_results_do_not_mix_between_lessons(st):
    quiz0, quiz1 = make_quiz(0), make_quiz(1)
    S.store_quiz(st, 0, quiz0)
    S.store_quiz(st, 1, quiz1)
    S.store_result(st, 0, grade_quiz(quiz0, [0] * 5))
    assert st["quiz_results"][0].score == 5
    assert 1 not in st["quiz_results"]
    S.store_result(st, 1, grade_quiz(quiz1, [0] * 5))
    assert st["quiz_results"][1].score == 0
    assert st["quiz_results"][0].score == 5  # unchanged


def test_widget_keys_unique_per_lesson_and_question(st):
    keys = {S.quiz_widget_key(st, lesson, q) for lesson in range(3) for q in range(5)}
    assert len(keys) == 15


def test_retake_keeps_questions_but_clears_result_and_answers(st):
    quiz = make_quiz(0)
    S.store_quiz(st, 0, quiz)
    S.store_result(st, 0, grade_quiz(quiz, [0] * 5))
    old_key = S.quiz_widget_key(st, 0, 0)

    S.retake_quiz(st, 0)

    assert 0 not in st["quiz_results"]
    assert st["quizzes"][0] is quiz  # same questions, nothing regenerated
    assert S.quiz_widget_key(st, 0, 0) != old_key  # fresh, unanswered widgets


def test_retake_only_affects_one_lesson(st):
    quiz = make_quiz(0)
    for i in (0, 1):
        S.store_quiz(st, i, quiz)
        S.store_result(st, i, grade_quiz(quiz, [0] * 5))
    key_before = S.quiz_widget_key(st, 1, 0)
    S.retake_quiz(st, 0)
    assert 1 in st["quiz_results"]
    assert S.quiz_widget_key(st, 1, 0) == key_before


def test_new_course_clears_everything(st):
    S.store_lesson(st, 0, Lesson.model_validate(lesson_dict()))
    S.store_quiz(st, 0, make_quiz(0))
    S.store_result(st, 0, grade_quiz(make_quiz(0), [0] * 5))
    old_course_id = st["course_id"]
    st["selected_lesson"], st["view"] = 2, "Quiz"

    S.start_new_course(
        st, validate_course_config("Python", "Advanced", 2), CourseOutline.model_validate(outline_dict(2))
    )

    assert st["lessons"] == st["quizzes"] == st["quiz_results"] == st["quiz_attempts"] == {}
    assert (st["selected_lesson"], st["view"]) == (0, "Outline")
    assert st["course_id"] == old_course_id + 1
