# AI Course Generator

Type a topic, pick a difficulty and a lesson count, and get a structured course: an outline, full lessons with exercises, and graded five-question quizzes. Built with Python, Streamlit and Groq (`openai/gpt-oss-20b`).

## How it works

1. **Configure**: topic, difficulty (Beginner / Intermediate / Advanced) and 2 to 5 lessons. Inputs are validated before any API call.
2. **Outline**: Groq returns a course title, description, objectives and exactly the requested number of lessons (title, objectives, summary).
3. **Lesson**: pick a lesson and generate it: introduction, 2 to 4 sections (heading, explanation, example), a summary and exactly two exercises with hints.
4. **Quiz**: generate five multiple-choice questions based on the lesson, answer them, and Python grades them and shows the score out of 5 with the correct answers and explanations. You can retake the same quiz.

Every AI response is requested as JSON, validated with Pydantic (exact counts, required fields) and retried with the error message if it is incomplete. Grading is plain Python, never done by the AI.

## Setup

You need Python 3.10 or newer and a free Groq API key from <https://console.groq.com/keys>.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows (PowerShell or cmd)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key
cp .env.example .env              # Windows: copy .env.example .env
#    then open .env and set GROQ_API_KEY=your real key

# 4. (Optional) verify the connection
python check_connection.py

# 5. Run the app
streamlit run app.py
```

In VS Code, choose the `venv` interpreter (Ctrl/Cmd+Shift+P, "Python: Select Interpreter") before running.

## Tests

The tests use a fake Groq client, so they need no API key and no internet.

```bash
pip install -r requirements-dev.txt
pytest
```

They cover connection and API error handling, input validation, exact lesson/section/exercise/question counts, retries on invalid AI output, grading, and state handling (switching lessons, per-lesson quiz results, retakes, starting a new course).

## Project structure

```
app.py                    Streamlit interface
check_connection.py       One-off Groq connection test
course_generator/
  llm.py                  Groq client, error handling, JSON generation with retries
  models.py               Pydantic models and input validation
  generators.py           Prompts: outline, lesson, quiz
  grading.py              Quiz grading
  state.py                Session-state helpers (per-lesson storage, retakes)
tests/                    pytest suite
```

## Notes

- `reasoning_effort="low"` is sent to `gpt-oss-20b` to keep responses quick.
- Quiz answer options are shuffled in Python, because language models tend to favour certain answer positions.
- Free-tier rate limits can apply; the app shows a message and you can click again after a moment.
