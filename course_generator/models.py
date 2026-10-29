"""Pydantic models for user input and AI-generated content."""
from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

LEVELS = ("Beginner", "Intermediate", "Advanced")
MIN_LESSONS = 2
MAX_LESSONS = 5
QUIZ_SIZE = 5
OPTIONS_PER_QUESTION = 4
EXERCISES_PER_LESSON = 2

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# --------------------------------------------------------------------------- #
# User input
# --------------------------------------------------------------------------- #
class ConfigError(ValueError):
    """Raised when the course configuration entered by the user is invalid."""


class CourseConfig(BaseModel):
    topic: NonEmptyStr
    level: Literal["Beginner", "Intermediate", "Advanced"]
    num_lessons: int = Field(ge=MIN_LESSONS, le=MAX_LESSONS)


def validate_course_config(topic: str, level: str, num_lessons: int) -> CourseConfig:
    """Validate raw form values and return a CourseConfig.

    Raises ConfigError with a message that can be shown directly to the user.
    """
    topic = " ".join((topic or "").split())
    if not topic:
        raise ConfigError("Enter a course topic to get started.")
    if len(topic) < 3:
        raise ConfigError("The topic is too short. Use at least 3 characters.")
    if len(topic) > 100:
        raise ConfigError("The topic is too long. Keep it under 100 characters.")
    if not any(ch.isalnum() for ch in topic):
        raise ConfigError("The topic must contain letters or numbers.")
    if level not in LEVELS:
        raise ConfigError(f"Choose a difficulty level: {', '.join(LEVELS)}.")
    if (
        isinstance(num_lessons, bool)
        or not isinstance(num_lessons, int)
        or not MIN_LESSONS <= num_lessons <= MAX_LESSONS
    ):
        raise ConfigError(f"Choose between {MIN_LESSONS} and {MAX_LESSONS} lessons.")
    return CourseConfig(topic=topic, level=level, num_lessons=num_lessons)


# --------------------------------------------------------------------------- #
# Course outline
# --------------------------------------------------------------------------- #
ObjectiveList = Annotated[list[NonEmptyStr], Field(min_length=2, max_length=6)]


class LessonOutline(BaseModel):
    title: NonEmptyStr
    objectives: ObjectiveList
    summary: NonEmptyStr


class CourseOutline(BaseModel):
    title: NonEmptyStr
    description: NonEmptyStr
    objectives: ObjectiveList
    lessons: Annotated[
        list[LessonOutline], Field(min_length=MIN_LESSONS, max_length=MAX_LESSONS)
    ]


# --------------------------------------------------------------------------- #
# Lesson content
# --------------------------------------------------------------------------- #
class LessonSection(BaseModel):
    heading: NonEmptyStr
    explanation: NonEmptyStr
    example: NonEmptyStr


class Exercise(BaseModel):
    prompt: NonEmptyStr
    hint: NonEmptyStr


class Lesson(BaseModel):
    introduction: NonEmptyStr
    sections: Annotated[list[LessonSection], Field(min_length=2, max_length=4)]
    summary: NonEmptyStr
    exercises: Annotated[
        list[Exercise],
        Field(min_length=EXERCISES_PER_LESSON, max_length=EXERCISES_PER_LESSON),
    ]


# --------------------------------------------------------------------------- #
# Quiz
# --------------------------------------------------------------------------- #
_LETTER_PREFIX = re.compile(r"^\s*\(?[A-Da-d][\).:]\s+")


class QuizQuestion(BaseModel):
    question: NonEmptyStr
    options: Annotated[
        list[NonEmptyStr],
        Field(min_length=OPTIONS_PER_QUESTION, max_length=OPTIONS_PER_QUESTION),
    ]
    correct_index: int = Field(ge=0, le=OPTIONS_PER_QUESTION - 1)
    explanation: NonEmptyStr

    @field_validator("options", mode="before")
    @classmethod
    def _strip_letter_prefixes(cls, value):
        # Models sometimes return "A) text"; the UI shows its own markers.
        if isinstance(value, list):
            return [
                _LETTER_PREFIX.sub("", opt) if isinstance(opt, str) else opt
                for opt in value
            ]
        return value

    @field_validator("correct_index", mode="before")
    @classmethod
    def _accept_letters(cls, value):
        # Accept "B" or "2" in addition to a real integer.
        if isinstance(value, str):
            text = value.strip().upper()
            if len(text) == 1 and text in "ABCD":
                return "ABCD".index(text)
            if text.isdigit():
                return int(text)
        return value

    @model_validator(mode="after")
    def _options_are_distinct(self):
        if len({opt.strip().lower() for opt in self.options}) != len(self.options):
            raise ValueError("Answer options must be different from each other.")
        return self


class Quiz(BaseModel):
    questions: Annotated[
        list[QuizQuestion], Field(min_length=QUIZ_SIZE, max_length=QUIZ_SIZE)
    ]


class QuestionResult(BaseModel):
    selected_index: int
    correct_index: int
    is_correct: bool


class QuizResult(BaseModel):
    score: int
    total: int
    details: list[QuestionResult]
