import json
import logging
import typing

from google.adk.agents.callback_context import CallbackContext

from app.app_utils.common import _clean_json, _log_agent_complete

logger = logging.getLogger(__name__)


def preprocessing_after_callback(callback_context: CallbackContext) -> None:
    raw_context = callback_context.state.get("preprocessing_context")
    if not raw_context:
        return
    try:
        data = json.loads(_clean_json(raw_context))
        if data.get("skipped"):
            logger.info(
                f"Preprocessing skipped: {data.get('message', 'Result already exists')}"
            )
            callback_context.state["skipped"] = True
            return
        if data.get("error"):
            logger.error(f"Preprocessing aborted pipeline: {data.get('error')}")
            raise ValueError(
                f"CRITICAL: Preprocessing missing dependencies: {data.get('error')}"
            )
        callback_context.state["questions"] = data.get("questions", [])
        callback_context.state["rubric"] = data.get("rubric", {})
        callback_context.state["historical_performance"] = data.get(
            "historical_performance", []
        )
        callback_context.state["linked_user_id"] = data.get("linked_user_id")
        callback_context.state["max_score"] = data.get("max_score")
        callback_context.state["exam_type"] = data.get("exam_type", "WAEC")
        # Defensive default state initialization for downstream agents
        callback_context.state["weakness_profile"] = []
        callback_context.state["referee_status"] = "COMPLETED"
        callback_context.state["practice_session_id"] = ""
        _log_agent_complete("PreprocessingAgent", "preprocessing_context")
    except Exception as e:
        logger.error(f"Error parsing preprocessing_context: {e}")
        raise e


def grading_after_callback(callback_context: CallbackContext) -> None:
    raw_res = callback_context.state.get("graded_result")
    if not raw_res:
        callback_context.state["graded_questions"] = []
        return
    try:
        data = json.loads(_clean_json(raw_res))
        callback_context.state["graded_questions"] = data.get("graded_questions", [])
        _log_agent_complete("GradingAgent", "graded_result")
    except Exception as e:
        logger.error(f"Error parsing graded_result: {e}")
        callback_context.state["graded_questions"] = []


def referee_after_callback(callback_context: CallbackContext) -> None:
    raw_rep = callback_context.state.get("referee_report")
    if not raw_rep:
        callback_context.state["referee_status"] = "COMPLETED"
        return
    try:
        data = json.loads(_clean_json(raw_rep))
        callback_context.state["referee_status"] = data.get("status", "COMPLETED")
        _log_agent_complete("RefereeAgent", "referee_report")
    except Exception as e:
        logger.error(f"Error parsing referee_report: {e}")
        callback_context.state["referee_status"] = "COMPLETED"


def final_after_callback(callback_context: CallbackContext) -> None:
    _log_agent_complete("FinalAggregator", "final_payload")


def weakness_after_callback(callback_context: CallbackContext) -> None:
    raw_profile = callback_context.state.get("weakness_profile_raw")
    if not raw_profile:
        callback_context.state["weakness_profile"] = {
            "weakTopics": [],
            "classWeakTopics": [],
        }
        return
    try:
        callback_context.state["weakness_profile"] = json.loads(
            _clean_json(raw_profile)
        )
        _log_agent_complete("WeaknessDetectionAgent", "weakness_profile_raw")
    except Exception as e:
        logger.error(f"Error parsing weakness_profile_raw: {e}")
        callback_context.state["weakness_profile"] = {
            "weakTopics": [],
            "classWeakTopics": [],
        }


def smart_prep_after_callback(callback_context: CallbackContext) -> None:
    raw_res = callback_context.state.get("practice_sessions_created_raw")
    if not raw_res:
        callback_context.state["practice_sessions_created"] = []
        return
    try:
        data = json.loads(_clean_json(raw_res))
        callback_context.state["practice_sessions_created"] = data.get(
            "practice_sessions_created", []
        )
        _log_agent_complete("SmartPrepAgent", "practice_sessions_created_raw")
    except Exception as e:
        logger.error(f"Error parsing practice_sessions_created: {e}")
        callback_context.state["practice_sessions_created"] = []


def generic_callback(output_key: str) -> typing.Callable[[CallbackContext], None]:
    def callback(callback_context: CallbackContext) -> None:
        raw = callback_context.state.get(f"{output_key}_raw")
        if not raw:
            callback_context.state[output_key] = {}
            return
        try:
            data = json.loads(_clean_json(raw))
            # Merge keys directly into state for downstream agents if needed
            if isinstance(data, dict):
                for k, v in data.items():
                    callback_context.state[k] = v
            callback_context.state[output_key] = data
            _log_agent_complete("Agent", f"{output_key}_raw")
        except Exception as e:
            logger.error(f"Error parsing {output_key}_raw: {e}")
            callback_context.state[output_key] = {}

    return callback

def _get_message_payload(callback_context: CallbackContext) -> dict:
    # 1. Try to get message from state or session state
    msg = callback_context.state.get("message") or callback_context.session.state.get("message")
    
    # 2. If not found in state, try user_content
    if not msg and callback_context.user_content:
        user_content = callback_context.user_content
        if isinstance(user_content, str):
            msg = user_content
        elif isinstance(user_content, dict):
            return user_content
        elif hasattr(user_content, "parts") and user_content.parts:
            texts = [part.text for part in user_content.parts if hasattr(part, "text") and part.text]
            if texts:
                msg = "".join(texts)
                
    if not msg:
        return {}
        
    if isinstance(msg, dict):
        return msg
        
    if isinstance(msg, str):
        try:
            return json.loads(msg)
        except Exception:
            pass
            
    return {}

def skip_if_extract_only(callback_context: CallbackContext) -> typing.Optional[typing.Any]:
    payload = _get_message_payload(callback_context)
    if payload.get("task") == "extract_topics_only":
        callback_context.state["skipped"] = True
        logger.info("Skipping agent because task is extract_topics_only")
        from google.genai import types as genai_types
        return genai_types.Content(parts=[genai_types.Part(text='{"skipped": true}')])
    return None

def skip_if_generate_only(callback_context: CallbackContext) -> typing.Optional[typing.Any]:
    payload = _get_message_payload(callback_context)
    if payload.get("task") == "generate_questions_only":
        callback_context.state["skipped"] = True
        logger.info("Skipping agent because task is generate_questions_only")
        from google.genai import types as genai_types
        return genai_types.Content(parts=[genai_types.Part(text='{"skipped": true}')])
    return None


