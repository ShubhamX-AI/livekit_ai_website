# from agents.base_agent import BaseAgentWithCustomSTT
from livekit.agents import function_tool, RunContext, Agent
import chromadb
import logging
import json
import asyncio
from agents.web.ai_integration.functions import UIAgentFunctions
from agents.web.web_agent_prompt import WEB_AGENT_PROMPT2
from shared_humanization_prompt.tts_humanificaiton_elevnlabs import (
    TTS_HUMANIFICATION_ELEVNLABS,
)

logger = logging.getLogger(__name__)


class Webagent(Agent):
    def __init__(self, room) -> None:
        self.agent_instruction = WEB_AGENT_PROMPT2 + TTS_HUMANIFICATION_ELEVNLABS
        super().__init__(
            # Instructions for the agent
            instructions=self.agent_instruction,
        )
        self.room = room
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="indusnet_website"
        )
        self.db_fetch_size = 5
        self.ui_context: dict[str, object] = {}
        self.ui_agent_functions = UIAgentFunctions()

    # Get UI context from frontend
    def update_ui_context(self, context_payload: dict) -> None:
        if not isinstance(context_payload, dict):
            logger.info("UI context ignored (non-dict payload)")
            return
        logger.info("UI context received: %s", context_payload)
        self.ui_context.update(context_payload)
        self.ui_context["markdown"] = self._ui_context_to_markdown(context_payload)

    # Convert json to markdown format
    def _ui_context_to_markdown(self, context_payload: dict) -> str:
        lines: list[str] = []
        for key in sorted(context_payload.keys(), key=str):
            value = context_payload.get(key)
            if isinstance(value, (dict, list)):
                rendered = json.dumps(value, ensure_ascii=True)
            else:
                rendered = "" if value is None else str(value)
            lines.append(f"- {key}: {rendered}")
        return "\n".join(lines)

    # Welcome message property
    @property
    def welcome_message(self):
        return (
            "Welcome to Indus Net Technologies."
            " I'm Vyom, your web assistant. How can I help you today?"
        )

    # lookup_website_information tool
    @function_tool
    async def lookup_website_information(self, context: RunContext, question: str):
        """Use this tool to answer any questions about Indus net Technologies."""
        logger.info(f"looking for {question}")
        results = self.collection.query(
            query_texts=[question], n_results=self.db_fetch_size
        )
        documents = results.get("documents") or []

        # Flatten and join all text into a single clean markdown string
        flat_documents = [item for sublist in documents for item in sublist]
        joined = "\n\n---\n\n".join(
            doc.strip() for doc in flat_documents if doc.strip()
        )

        # Optionally strip excessive whitespace, remove duplicate consecutive lines
        cleaned = "\n".join(
            line
            for i, line in enumerate(joined.splitlines())
            if line.strip()
            and (i == 0 or line.strip() != joined.splitlines()[i - 1].strip())
        )

        # Stream UI updates as a background task
        asyncio.create_task(
            self._publish_ui_stream(
                user_input=question, db_results=cleaned, ui_context=self.ui_context
            )
        )
        return cleaned

    async def _publish_ui_stream(
        self, user_input: str, db_results: str, ui_context: dict
    ) -> None:
        async for payload in self.ui_agent_functions.query_process_stream(
            user_input=user_input, db_results=db_results, ui_context=ui_context
        ):
            try:
                await self.room.local_participant.publish_data(
                    json.dumps(payload).encode("utf-8"),
                    reliable=True,
                    topic="ui.flashcard",
                )
                logger.info("✅ Data packet sent successfully")
            except Exception as e:
                logger.error(f"❌ Failed to publish data: {e}")
