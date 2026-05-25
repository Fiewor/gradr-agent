import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    """Robustly extract JSON substring between first '{' or '[' and last '}' or ']':."""
    s = raw.strip()
    # Find first occurrence of { or [
    start_curly = s.find("{")
    start_bracket = s.find("[")

    start_idx = -1
    end_idx = -1

    if start_curly != -1 and (start_bracket == -1 or start_curly < start_bracket):
        start_idx = start_curly
        end_idx = s.rfind("}")
    elif start_bracket != -1:
        start_idx = start_bracket
        end_idx = s.rfind("]")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return s[start_idx : end_idx + 1]

    # Fallback to basic clean if no braces found
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def _log_agent_complete(agent_name: str, output_key: str) -> None:
    """Emit a structured log entry for agent completion."""
    logger.info(
        json.dumps(
            {
                "agent": agent_name,
                "status": "complete",
                "output_key": output_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )
