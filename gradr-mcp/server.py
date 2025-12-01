from typing import Any, Dict
import json
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gradr")


def json_string(data: Dict[str, Any]) -> str:
    """Utility: Always return JSON string."""
    return json.dumps(data, ensure_ascii=False, indent=2)


# In-memory cache (replace later with Redis / Postgres)
CACHE: Dict[str, Any] = {}

@mcp.tool()
def parse_questions(text: str) -> str:
    """
    Parses raw question text into a structured list.

    Expected Format:
        Q1. What is photosynthesis?
        Q2. Define osmosis.

    Real version should use NLP. Here is structured mock logic.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    questions = []
    for idx, line in enumerate(lines):
        questions.append({
            "question_id": f"q{idx+1}",
            "text": line
        })

    return json_string({
        "ok": True,
        "questions": questions,
        "count": len(questions)
    })

@mcp.tool()
def parse_marking_guide(text: str) -> str:
    """
    Converts marking guide text into rubric structure.

    Example Input:
        Q1: Definition (2 marks), Example (1 mark)
        Q2: Explanation (3 marks)

    Output:
        { question_id: { rubric_items: [...] , max_score: X } }
    """
    # Minimal mock implementation
    rubric = {
        "rubric_items": [
            {"label": "accuracy", "points": 2},
            {"label": "clarity", "points": 1},
            {"label": "completeness", "points": 2}
        ],
        "max_score": 5
    }

    return json_string({
        "ok": True,
        "rubric": rubric
    })


@mcp.tool()
def normalize_answers(text: str) -> str:
    """
    Normalizes student answers (lowercasing, removing noise).
    """
    cleaned = text.strip().lower()

    return json_string({
        "ok": True,
        "normalized": cleaned
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
