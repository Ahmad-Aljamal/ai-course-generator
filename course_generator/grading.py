"""Quiz grading. Pure Python: the AI never decides the score."""
from __future__ import annotations

from typing import Sequence

from .models import QuestionResult, Quiz, QuizResult


def grade_quiz(quiz: Quiz, answers: Sequence[int | None]) -> QuizResult:
    """Grade selected option indexes against the quiz's correct answers.

    `answers[i]` is the option index chosen for question i. Raises ValueError
    if any question is unanswered or an index is out of range.
    """
    if len(answers) != len(quiz.questions):
        raise ValueError("Provide one answer for every question.")

    details: list[QuestionResult] = []
    for number, (question, selected) in enumerate(zip(quiz.questions, answers), start=1):
        if selected is None:
            raise ValueError(f"Question {number} has not been answered.")
        if not 0 <= selected < len(question.options):
            raise ValueError(f"Question {number} has an invalid answer.")
        details.append(
            QuestionResult(
                selected_index=selected,
                correct_index=question.correct_index,
                is_correct=selected == question.correct_index,
            )
        )

    return QuizResult(
        score=sum(d.is_correct for d in details),
        total=len(details),
        details=details,
    )
