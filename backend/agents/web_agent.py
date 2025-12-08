from livekit.agents import (Agent, 
                            function_tool,
                            RunContext)
import chromadb
import asyncio
import logging
from openai import OpenAI
from agents.agent_prompts import WEB_AGENT_PROMPT

logger = logging.getLogger("agent")

class Webagent(Agent):
    def __init__(self) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=WEB_AGENT_PROMPT,
        )
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(name="indusnet_website")
        self.db_fetch_size = 3
        self.openai_client = OpenAI()

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str):
        """Use this tool to look up current weather information."""
        logger.info(f"Looking up weather for {location}")
        await asyncio.sleep(5)
        return "sunny with a temperature of 70 degrees."
    
    @function_tool
    async def lookup_website_information(self, context: RunContext, question: str):
        """Use this tool to answer any questions about Indus net Technologies."""
        logger.info(f"looking for {question}")
        results = self.collection.query(
                query_texts=[question],
                n_results=self.db_fetch_size
            )
        documents = results.get("documents", [])
        return documents
        # response = self.openai_client.responses.create(
        #     model="gpt-4.1",
        #     tools=[{ "type": "web_search_preview" }],
        #     input=question,
        #     prompt_cache_retention = "24h",
        # )

        # return response.output_text

