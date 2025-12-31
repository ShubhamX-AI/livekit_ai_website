from livekit.agents import (Agent, 
                            function_tool,
                            RunContext)
import chromadb
import logging
import json
from agents.agent_prompts import WEB_AGENT_PROMPT


logger = logging.getLogger("agent")

class Webagent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=WEB_AGENT_PROMPT,
        )
        self.room = room 
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(name="indusnet_website")
        self.db_fetch_size = 5
    

    @property
    def welcome_message(self):
        return (
            "Welcome to Indus Net Technologies. "
            "I’m Aarti, your web assistant. How can I help you today?"
        )

    @function_tool
    async def lookup_website_information(self, context: RunContext, question: str):
        """Use this tool to answer any questions about Indus net Technologies."""
        logger.info(f"looking for {question}")
        results = self.collection.query(
                query_texts=[question],
                n_results=self.db_fetch_size
            )
        documents = results.get("documents", [])
        
        # Flatten and join all text into a single clean markdown string
        flat_documents = [item for sublist in documents for item in sublist]
        joined = "\n\n---\n\n".join(doc.strip() for doc in flat_documents if doc.strip())

        # Optionally strip excessive whitespace, remove duplicate consecutive lines
        cleaned = "\n".join(line for i, line in enumerate(joined.splitlines()) 
                            if line.strip() and (i == 0 or line.strip() != joined.splitlines()[i-1].strip()))

        return cleaned
    
    @function_tool
    async def emit_flashcard(
        self,
        context: RunContext,
        title: str,
        value: str,
    ):
        """
        Emit a flashcard fact.
        This tool is called by the LLM during answer generation.
        """
        logger.info(f"Emitting flashcard: {title}")

        payload = {
            "type": "flashcard",
            "title": title,
            "value": value,
        }

        try:
            await self.room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"),
                reliable=True,
                topic="ui.flashcard",
            )
            logger.info("✅ Data packet sent successfully")
        except Exception as e:
            logger.error(f"❌ Failed to publish data: {e}")

        return f"Flashcard '{title}' has been displayed to the user."

