import logging

from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini

from app.toolsets import retry_config

logger = logging.getLogger(__name__)

topic_extraction_agent = Agent(
    name="TopicExtractionAgent",
    model=Gemini(model="gemini-3.1-flash-lite", retry_options=retry_config),
    instruction="Extract topics from resources.",
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
