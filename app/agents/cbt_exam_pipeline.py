import logging

from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini

from app.toolsets import retry_config

from app.callbacks import generic_callback, skip_if_extract_only

logger = logging.getLogger(__name__)

topic_extraction_agent = Agent(
    name="TopicExtractionAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=(
        "<role>\n"
        "You are the TopicExtractionAgent, an elite academic content parser and educational researcher. "
        "You excel at distilling massive volumes of text into their core pedagogical axes.\n"
        "</role>\n\n"
        "<task>\n"
        "Analyze the provided document(s) and extract the top 5 to 10 most significant academic topics discussed within.\n"
        "</task>\n\n"
        "<constraints>\n"
        "- You MUST provide a relative concentration weight for each topic as an integer percentage between 1 and 100 (e.g., 25 for 25%).\n"
        "- The sum of all weights across extracted topics should equal 100.\n"
        "- Topics MUST be significant, comprehensive, and accurately reflect the primary content of the text.\n"
        "</constraints>"
    ),
    output_key="extracted_topics",
)

question_generation_agent = Agent(
    name="QuestionGenerationAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=(
        "<role>\n"
        "You are a senior academic curriculum mapping specialist. Your expertise lies in crafting challenging, curriculum-aligned assessments that definitively test human comprehension.\n"
        "</role>\n\n"
        "<task>\n"
        "Generate unique test questions purely based on the provided document(s) or notes, adhering to the requested parameters (difficulty, type, etc).\n"
        "</task>\n\n"
        "<specific_rules>\n"
        "- If requested type is multiple-choice, provide the specified number of options and a correctOptionId.\n"
        "- If hybrid, mix multiple-choice and essay questions according to mcqCount and essayCount.\n"
        "- If topic priorities are provided, prioritize generating questions from those topics.\n"
        "- Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation.\n"
        "</specific_rules>\n\n"
        "<output_format>\n"
        "[\n"
        "  {\n"
        '    "id": "Q1",\n'
        '    "question": "...",\n'
        '    "type": "multiple-choice",\n'
        '    "options": [{ "id": 1, "text": "..." }, { "id": 2, "text": "..." }],\n'
        '    "correctOptionId": 1\n'
        "  }\n"
        "]\n"
        "</output_format>"
    ),
    output_key="generated_questions_raw",
    before_agent_callback=skip_if_extract_only,
    after_agent_callback=generic_callback("generated_questions"),
)


class CBTExamGenerationPipelineAgent(SequentialAgent):
    pass


cbt_exam_generation_pipeline = CBTExamGenerationPipelineAgent(
    name="CBTExamGenerationPipeline",
    sub_agents=[
        topic_extraction_agent,
        question_generation_agent,
    ],
)
