import logging

from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini

from app.toolsets import retry_config

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
        "- You MUST provide a relative concentration weight for each topic.\n"
        "- Topics MUST be significant, comprehensive, and accurately reflect the primary content of the text.\n"
        "</constraints>"
    ),
    output_key="extracted_topics",
)


class CBTExamGenerationPipelineAgent(SequentialAgent):
    pass


cbt_exam_generation_pipeline = CBTExamGenerationPipelineAgent(
    name="CBTExamGenerationPipeline",
    sub_agents=[
        topic_extraction_agent,
    ],
)
