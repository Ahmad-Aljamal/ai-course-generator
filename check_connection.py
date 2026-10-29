"""Quick check that your API key works and Groq answers with openai/gpt-oss-20b.

Run:  python check_connection.py
"""
import sys

from course_generator.llm import MODEL, CourseGeneratorError, chat


def main() -> int:
    try:
        reply = chat(
            [{"role": "user", "content": "Reply with the single word: ready"}],
            max_tokens=512,
        )
    except CourseGeneratorError as exc:
        print(f"Connection failed: {exc}")
        return 1
    print(f"Connected to Groq ({MODEL}). Model replied: {reply.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
