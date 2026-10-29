"""Prompts and generation functions for outlines, lessons and quizzes."""
from __future__ import annotations

import random
from typing import Any

from .llm import generate_structured
from .models import (
    EXERCISES_PER_LESSON,
    OPTIONS_PER_QUESTION,
    QUIZ_SIZE,
    CourseConfig,
    CourseOutline,
    Lesson,
    Quiz,
)

LEVEL_GUIDE = {
    "Beginner": "Assume no prior knowledge. Define every term and use plain language and everyday analogies.",
    "Intermediate": "Assume the basics are known. Focus on practical application, common patterns and pitfalls.",
    "Advanced": "Assume solid experience. Go deep: edge cases, trade-offs, internals and best practices.",
}


# --------------------------------------------------------------------------- #
# Outline
# --------------------------------------------------------------------------- #
def generate_outline(config: CourseConfig, client: Any | None = None) -> CourseOutline:
    prompt = f"""Design a {config.level}-level course on: "{config.topic}".
{LEVEL_GUIDE[config.level]}

Requirements:
- A course title, a 2-3 sentence description and 3-5 course learning objectives.
- EXACTLY {config.num_lessons} lessons, in a logical order where each builds on the previous one.
- Each lesson needs a title, 2-4 learning objectives and a 1-2 sentence summary.
- Lesson titles must be specific and must not include numbering such as "Lesson 1:"."""

    def check(outline: CourseOutline) -> None:
        if len(outline.lessons) != config.num_lessons:
            raise ValueError(
                f"The course must contain exactly {config.num_lessons} lessons "
                f"but {len(outline.lessons)} were returned."
            )

    return generate_structured(prompt, CourseOutline, client=client, check=check)


# --------------------------------------------------------------------------- #
# Lesson
# --------------------------------------------------------------------------- #
def generate_lesson(
    config: CourseConfig,
    outline: CourseOutline,
    lesson_index: int,
    client: Any | None = None,
) -> Lesson:
    target = outline.lessons[lesson_index]
    others = "\n".join(
        f"{i + 1}. {item.title}" for i, item in enumerate(outline.lessons)
    )
    objectives = "\n".join(f"- {o}" for o in target.objectives)
    prompt = f"""Write the full content of lesson {lesson_index + 1} of {len(outline.lessons)}
in the {config.level}-level course "{outline.title}" (topic: {config.topic}).
{LEVEL_GUIDE[config.level]}

Course lessons (for context, avoid repeating the other lessons):
{others}

This lesson: "{target.title}"
Summary: {target.summary}
Learning objectives:
{objectives}

Requirements:
- "introduction": a short paragraph that motivates the lesson.
- "sections": between 2 and 4 sections. Each has a "heading", a clear "explanation"
  (a few paragraphs, Markdown allowed) and a concrete "example"
  (use fenced code blocks if the topic involves code).
- "summary": a short recap of the key points.
- "exercises": EXACTLY {EXERCISES_PER_LESSON} practice exercises, each with a "prompt" and a helpful "hint"
  that guides the learner without giving away the answer."""
    return generate_structured(prompt, Lesson, client=client, max_tokens=10000)


def lesson_to_text(title: str, lesson: Lesson) -> str:
    """Plain-text version of a lesson, used as source material for the quiz."""
    parts = [f"# {title}", lesson.introduction]
    for section in lesson.sections:
        parts += [f"## {section.heading}", section.explanation, f"Example: {section.example}"]
    parts += ["## Summary", lesson.summary]
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# Quiz
# --------------------------------------------------------------------------- #
def shuffle_quiz_options(quiz: Quiz, rng: random.Random | None = None) -> Quiz:
    """Shuffle each question's options and keep correct_index pointing at the right one.

    LLMs tend to favour certain answer positions, so Python randomises them.
    """
    rng = rng or random.Random()
    questions = []
    for q in quiz.questions:
        correct_text = q.options[q.correct_index]
        options = list(q.options)
        rng.shuffle(options)
        questions.append(
            q.model_copy(
                update={"options": options, "correct_index": options.index(correct_text)}
            )
        )
    return quiz.model_copy(update={"questions": questions})


def generate_quiz(
    config: CourseConfig,
    outline: CourseOutline,
    lesson_index: int,
    lesson: Lesson,
    client: Any | None = None,
    rng: random.Random | None = None,
) -> Quiz:
    title = outline.lessons[lesson_index].title
    prompt = f"""Write a multiple-choice quiz for the {config.level}-level lesson below.

Requirements:
- EXACTLY {QUIZ_SIZE} questions that test understanding of THIS lesson only.
- Each question has a "question", EXACTLY {OPTIONS_PER_QUESTION} "options" (plain text, no "A)" prefixes),
  "correct_index" (zero-based position 0-{OPTIONS_PER_QUESTION - 1} of the single correct option) and a short "explanation"
  of why that answer is correct.
- Exactly one option is correct. Wrong options must be plausible but clearly incorrect.
- Do not use "all of the above" or "none of the above".

LESSON CONTENT:
{lesson_to_text(title, lesson)}"""
    quiz = generate_structured(prompt, Quiz, client=client, max_tokens=6000)
    return shuffle_quiz_options(quiz, rng)
