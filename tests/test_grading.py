import pytest

from course_generator.grading import grade_quiz
from course_generator.models import Quiz
from tests.factories import quiz_dict


@pytest.fixture
def quiz():
    data = quiz_dict()
    for i, q in enumerate(data["questions"]):
        q["correct_index"] = i % 4  # 0,1,2,3,0
    return Quiz.model_validate(data)


def test_perfect_score(quiz):
    result = grade_quiz(quiz, [0, 1, 2, 3, 0])
    assert (result.score, result.total) == (5, 5)
    assert all(d.is_correct for d in result.details)


def test_zero_score(quiz):
    assert grade_quiz(quiz, [1, 2, 3, 0, 1]).score == 0


def test_partial_score_and_details(quiz):
    result = grade_quiz(quiz, [0, 0, 2, 0, 0])
    assert result.score == 3
    assert [d.is_correct for d in result.details] == [True, False, True, False, True]
    assert result.details[1].selected_index == 0
    assert result.details[1].correct_index == 1


def test_unanswered_question_rejected(quiz):
    with pytest.raises(ValueError, match="Question 2"):
        grade_quiz(quiz, [0, None, 2, 3, 0])


def test_wrong_number_of_answers_rejected(quiz):
    with pytest.raises(ValueError):
        grade_quiz(quiz, [0, 1])


def test_out_of_range_answer_rejected(quiz):
    with pytest.raises(ValueError):
        grade_quiz(quiz, [0, 1, 2, 3, 9])
