# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import google.auth
from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.apps.app import App
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool, google_search
from google.genai import types
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.code_executors import BuiltInCodeExecutor
from mcp import StdioServerParameters

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# mcp server path
TARGET_FOLDER_PATH =  "/Users/macbookair/Documents/Code/gradr-agent/gradr-mcp/server.py"

ONLINE_ANSWERS_PROMPT = (
    "You are an OnlineAnswersAgent. Task: given a single exam question, use the google_search tool to "
    "gather up to 10 concise, relevant candidate answers or authoritative references. "
    "Output MUST be valid JSON with the schema: {"
    "\"question_hash\":\"<short-hash>\","
    "\"results\":[{\"snippet\":\"...\",\"source\":\"<short-source-or-url>\",\"confidence\":<0-1>}],"
    "\"timestamp\":\"<ISO8601>\"}"
    "\n\nConstraints: keep each snippet <= 120 characters, include a short source string, include a numeric confidence 0-1."
    "\n\nExample:\n"
    '{ "question_hash":"abcd1234", "results":[{"snippet":"X is the capital of Y","source":"wikipedia.org","confidence":0.9}], "timestamp":"2025-01-01T12:00:00Z" }'
)

SUMMARIZER_PROMPT = (
    "You are SummarizerAgent. Task: given OnlineAnswersAgent JSON in input 'online_answers', produce a concise "
    "3-5 bullet summary of the most reliable points and a single-line 'consensus_answer'. "
    "Output MUST be valid JSON with keys: 'consensus_answer', 'bullets':[...], 'confidence' (0-1), 'sources':[...]."
    "\n\nExample:\n"
    '{\"consensus_answer\":\"...\",\"bullets\":[\"...\",\"...\"],\"confidence\":0.82,\"sources\":[\"wikipedia.org\"]}'
)

GRADER_PROMPT_BASE = (
    "You are the GradingAgent. Your input includes: {question}, {student_answer}, and {markup} (parsed marking guide). "
    "You also have access to a 'final_summary' (from SummarizerAgent) and optional 'external_evidence' (from OnlineAnswersAgent). "
    "TASKS (in order):\n"
    "1) Validate that required inputs exist. If missing, return JSON with an 'error' key and suggested remediation.\n"
    "2) Align the student's answer to rubric items; compute a numeric score and max_score.\n"
    "3) Provide a concise justification (1-3 sentences) citing which rubric points were satisfied or not.\n"
    "4) Provide a model_confidence value between 0 and 1.\n"
    "5) Output MUST be strictly JSON following this schema: (insert GRADE_OUTPUT_SCHEMA). "
    "\n\nIMPORTANT: Use the rubric for numeric allocations. If the rubric is ambiguous, describe ambiguity clearly and set model_confidence <= 0.7.\n"
    "\n\nProvide a single JSON object as the only content of your response."
)

REFEREE_PROMPT = (
    "You are RefereeAgent (validation). Input: the entire graded_questions array produced by the GradingAgent. "
    "TASKS: \n"
    "1) Verify numeric totals, ensure no score > max_score, ensure all required fields present and confidence between 0-1.\n"
    "2) Detect hallucinations: if the justification references facts not present in student_answer or rubric or external_evidence, flag it.\n"
    "3) Return corrected entries or a report of suspected problems. Output must be JSON: { 'ok': bool, 'issues': [...], 'corrected': [...] }"
)

retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1, # Initial delay before first retry (in seconds)
    http_status_codes=[429, 500, 503, 504] # Retry on these HTTP errors
)

def show_python_code_and_result(response):
    for i in range(len(response)):
        # Check if the response contains a valid function call result from the code executor
        if (
            (response[i].content.parts)
            and (response[i].content.parts[0])
            and (response[i].content.parts[0].function_response)
            and (response[i].content.parts[0].function_response.response)
        ):
            response_code = response[i].content.parts[0].function_response.response
            if "result" in response_code and response_code["result"] != "```":
                if "tool_code" in response_code["result"]:
                    print(
                        "Generated Python Code >> ",
                        response_code["result"].replace("tool_code", ""),
                    )
                else:
                    print("Generated Python Response >> ", response_code["result"])

# OnlineAnswersAgent — lightweight model for retrieval + structured output
online_answers_agent = Agent(
    name="OnlineAnswersAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=ONLINE_ANSWERS_PROMPT,
    tools=[google_search],
    output_key="online_answers",
)

# SummarizerAgent — consumes online_answers and produces a compact summary
summarizer_agent = Agent(
    name="SummarizerAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=SUMMARIZER_PROMPT,
    input_keys=["online_answers"],
    output_key="final_summary",
)

# Per-question grading agent (single-question, deterministic, uses builtin code executor for arithmetic)
question_grader_agent = Agent(
    name="QuestionGraderAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=GRADER_PROMPT_BASE,
    tools=[AgentTool(online_answers_agent), AgentTool(summarizer_agent), BuiltInCodeExecutor()],
    input_keys=["question", "student_answer", "rubric", "final_summary", "external_evidence"],
    output_key="graded_question",
)

# LoopAgent to apply question_grader_agent across all questions
loop_grader = LoopAgent(
    name="LoopOverQuestions",
    sub_agent=question_grader_agent,
    loop_input_key="questions",   # expects 'questions' populated by preprocessing_agent
    loop_output_key="graded_questions",
)

# Referee / Validator Agent
referee_agent = Agent(
    name="RefereeAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=REFEREE_PROMPT,
    input_keys=["graded_questions", "rubric", "student_answers", "final_summary"],
    output_key="referee_report",
)

# Final Aggregator (assemble and standardize all outputs)
final_aggregator = Agent(
    name="FinalAggregator",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=(
        "Assemble a final payload with metadata and all graded_questions. "
        "Payload keys: exam_id, generated_at, graded_questions, aggregated_stats (avg_score, low_confidence_items). "
        "Output JSON only."
    ),
    input_keys=["graded_questions", "referee_report", "human_decision"],
    output_key="final_payload",
)

root_agent = SequentialAgent(
    name="GradingPipeline",
    sub_agents=[     
        online_answers_agent,  
        summarizer_agent,
        loop_grader,
        referee_agent,
        final_aggregator,
    ],
)

app = App(root_agent=root_agent, name="gradr_agentic_app")