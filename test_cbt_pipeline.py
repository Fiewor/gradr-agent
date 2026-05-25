import asyncio

from app.agent_engine_app import cbt_grading_engine


async def test_pipeline() -> None:
    session_id = "test-cbt-123"
    print("Sending query to pipeline...")
    async for response in cbt_grading_engine.async_stream_query(
        session_id=session_id,
        user_id="test_user",
        message="Grade this student's CBT attempt.",
        run_config={"state": {"attemptId": "69cabc860502046e4e3a25f7"}},
    ):
        print("Response:", response)


if __name__ == "__main__":
    asyncio.run(test_pipeline())
