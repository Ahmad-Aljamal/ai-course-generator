"""Streamlit front end for the AI Course Generator.

Run with:  streamlit run app.py
"""
import streamlit as st

from course_generator import state as S
from course_generator.generators import generate_lesson, generate_outline, generate_quiz
from course_generator.grading import grade_quiz
from course_generator.llm import CourseGeneratorError, api_key_configured
from course_generator.models import (
    LEVELS,
    MAX_LESSONS,
    MIN_LESSONS,
    ConfigError,
    validate_course_config,
)

st.set_page_config(page_title="AI Course Generator", page_icon="🎓", layout="wide")
S.init_state(st.session_state)


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
def create_course(topic: str, level: str, num_lessons: int) -> None:
    """Validate the form, generate the outline and make it the active course."""
    try:
        config = validate_course_config(topic, level, num_lessons)
    except ConfigError as exc:
        st.error(str(exc))
        return
    try:
        with st.spinner("Designing your course…"):
            course = generate_outline(config)
    except CourseGeneratorError as exc:
        st.error(str(exc))
        return
    S.start_new_course(st.session_state, config, course)


def open_view(lesson_index: int, view: str) -> None:
    """Button callback: jump to a lesson and a view (runs before the rerun)."""
    st.session_state["selected_lesson"] = lesson_index
    st.session_state["view"] = view


def go_to_quiz() -> None:
    st.session_state["view"] = "Quiz"


# --------------------------------------------------------------------------- #
# Sidebar: course configuration + lesson picker
# --------------------------------------------------------------------------- #
def render_sidebar() -> None:
    with st.sidebar:
        st.header("Create a course")
        if not api_key_configured():
            st.error(
                "No Groq API key found. Add GROQ_API_KEY to your .env file "
                "and restart the app."
            )
        with st.form("course_config"):
            topic = st.text_input(
                "Course topic", placeholder="e.g. Introduction to SQL", max_chars=100
            )
            level = st.selectbox("Difficulty level", LEVELS)
            num_lessons = st.slider("Number of lessons", MIN_LESSONS, MAX_LESSONS, 3)
            submitted = st.form_submit_button("Generate course", type="primary")
        if submitted:
            create_course(topic, level, num_lessons)

        course = st.session_state["course"]
        if course is not None:
            st.divider()
            st.radio(
                "Lessons",
                options=list(range(len(course.lessons))),
                format_func=lambda i: f"{i + 1}. {course.lessons[i].title}",
                key="selected_lesson",
            )


# --------------------------------------------------------------------------- #
# Main views
# --------------------------------------------------------------------------- #
def render_welcome() -> None:
    st.title("AI Course Generator")
    st.write(
        "Turn any topic into a short course with lessons, exercises and graded quizzes."
    )
    st.markdown(
        "1. Enter a topic, pick a level and the number of lessons in the sidebar.\n"
        "2. Review the outline and open a lesson.\n"
        "3. Take the quiz and see your score right away."
    )


def render_outline() -> None:
    course = st.session_state["course"]
    st.write(course.description)
    st.subheader("What you will learn")
    for objective in course.objectives:
        st.markdown(f"- {objective}")

    st.subheader("Lessons")
    course_id = st.session_state["course_id"]
    for i, lesson in enumerate(course.lessons):
        with st.container(border=True):
            st.markdown(f"**Lesson {i + 1}: {lesson.title}**")
            st.write(lesson.summary)
            for objective in lesson.objectives:
                st.markdown(f"- {objective}")

            result = st.session_state["quiz_results"].get(i)
            if result is not None:
                status = f"Quiz score: {result.score} / {result.total}"
            elif i in st.session_state["lessons"]:
                status = "Lesson ready"
            else:
                status = "Not started"
            st.caption(status)
            st.button(
                "Open lesson",
                key=f"open_{course_id}_{i}",
                on_click=open_view,
                args=(i, "Lesson"),
            )


def render_lesson(idx: int) -> None:
    course = st.session_state["course"]
    config = st.session_state["config"]
    course_id = st.session_state["course_id"]
    outline = course.lessons[idx]
    st.header(f"Lesson {idx + 1}: {outline.title}")

    lesson = st.session_state["lessons"].get(idx)
    if lesson is None:
        st.info("This lesson has not been written yet.")
        if st.button("Generate lesson", type="primary", key=f"gen_lesson_{course_id}_{idx}"):
            try:
                with st.spinner("Writing the lesson…"):
                    lesson = generate_lesson(config, course, idx)
            except CourseGeneratorError as exc:
                st.error(str(exc))
            else:
                S.store_lesson(st.session_state, idx, lesson)
        if lesson is None:
            return

    st.write(lesson.introduction)
    for n, section in enumerate(lesson.sections, start=1):
        st.subheader(f"{n}. {section.heading}")
        st.markdown(section.explanation)
        st.markdown("**Example**")
        st.info(section.example)

    st.subheader("Summary")
    st.write(lesson.summary)

    st.subheader("Exercises")
    for n, exercise in enumerate(lesson.exercises, start=1):
        with st.container(border=True):
            st.markdown(f"**Exercise {n}**")
            st.markdown(exercise.prompt)
            with st.expander("Show hint"):
                st.markdown(exercise.hint)

    st.button("Take the quiz", type="primary", on_click=go_to_quiz, key=f"to_quiz_{course_id}_{idx}")


def render_quiz(idx: int) -> None:
    course = st.session_state["course"]
    config = st.session_state["config"]
    course_id = st.session_state["course_id"]
    st.header(f"Quiz: {course.lessons[idx].title}")

    lesson = st.session_state["lessons"].get(idx)
    if lesson is None:
        st.info("Generate this lesson first. The quiz is based on its content.")
        st.button(
            "Go to lesson",
            on_click=open_view,
            args=(idx, "Lesson"),
            key=f"quiz_to_lesson_{course_id}_{idx}",
        )
        return

    quiz = st.session_state["quizzes"].get(idx)
    if quiz is None:
        st.info("This lesson has no quiz yet.")
        if st.button("Generate quiz", type="primary", key=f"gen_quiz_{course_id}_{idx}"):
            try:
                with st.spinner("Writing five questions…"):
                    quiz = generate_quiz(config, course, idx, lesson)
            except CourseGeneratorError as exc:
                st.error(str(exc))
            else:
                S.store_quiz(st.session_state, idx, quiz)
        if quiz is None:
            return

    result = st.session_state["quiz_results"].get(idx)
    if result is None:
        render_quiz_form(idx, quiz)
    else:
        render_quiz_results(idx, quiz, result)


def render_quiz_form(idx: int, quiz) -> None:
    state = st.session_state
    attempt = state["quiz_attempts"].get(idx, 0)
    with st.form(f"quiz_form_{state['course_id']}_{idx}_{attempt}"):
        for q_i, question in enumerate(quiz.questions):
            st.markdown(f"**{q_i + 1}. {question.question}**")
            st.radio(
                question.question,
                question.options,
                index=None,
                key=S.quiz_widget_key(state, idx, q_i),
                label_visibility="collapsed",
            )
        submitted = st.form_submit_button("Submit answers", type="primary")

    if not submitted:
        return

    answers = []
    for q_i, question in enumerate(quiz.questions):
        chosen = state.get(S.quiz_widget_key(state, idx, q_i))
        answers.append(question.options.index(chosen) if chosen in question.options else None)

    unanswered = [str(n) for n, a in enumerate(answers, start=1) if a is None]
    if unanswered:
        st.warning(f"Answer every question before submitting. Missing: {', '.join(unanswered)}.")
        return

    S.store_result(state, idx, grade_quiz(quiz, answers))
    st.rerun()


def render_quiz_results(idx: int, quiz, result) -> None:
    st.metric("Your score", f"{result.score} / {result.total}")
    st.progress(result.score / result.total)

    for q_i, (question, detail) in enumerate(zip(quiz.questions, result.details), start=1):
        with st.container(border=True):
            icon = "✅" if detail.is_correct else "❌"
            st.markdown(f"**{icon} {q_i}. {question.question}**")
            st.write(f"Your answer: {question.options[detail.selected_index]}")
            if not detail.is_correct:
                st.write(f"Correct answer: {question.options[detail.correct_index]}")
            st.caption(question.explanation)

    st.button(
        "Retake quiz",
        on_click=S.retake_quiz,
        args=(st.session_state, idx),
        key=f"retake_{st.session_state['course_id']}_{idx}",
    )


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
render_sidebar()

course = st.session_state["course"]
if course is None:
    render_welcome()
else:
    config = st.session_state["config"]
    st.title(course.title)
    st.caption(f"{config.level} course on {config.topic}, {config.num_lessons} lessons")

    st.radio("View", S.VIEWS, horizontal=True, key="view", label_visibility="collapsed")
    view = st.session_state["view"]
    lesson_index = st.session_state["selected_lesson"]

    if view == "Outline":
        render_outline()
    elif view == "Lesson":
        render_lesson(lesson_index)
    else:
        render_quiz(lesson_index)
