# from agents.base_agent import BaseAgentWithCustomSTT
from livekit.agents import function_tool, RunContext, Agent
import chromadb
import logging
import json
import asyncio
import uuid
from agents.web.ai_integration.functions import UIAgentFunctions
from agents.web.web_agent_prompt import WEB_AGENT_PROMPT
from shared_humanization_prompt.tts_humanification_cartesia import TTS_HUMANIFICATION_CARTESIA

logger = logging.getLogger(__name__)


class Webagent(Agent):
    def __init__(self, room) -> None:
        self._base_instruction = WEB_AGENT_PROMPT + TTS_HUMANIFICATION_CARTESIA
        super().__init__(
            # Instructions for the agent (will be updated dynamically with UI context)
            instructions=self._base_instruction,
        )
        self.room = room
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="indusnet_website_v2"
        )
        self.db_fetch_size = 5
        # UI Context Manager for state tracking and redundancy prevention
        self.ui_agent_functions = UIAgentFunctions()

    # Welcome message property
    @property
    def welcome_message(self):
        return (
            "Welcome to Indus Net Technologies."
            " Tell me how can I help you today?"
        )

    # Indus Net Knowledge Base Search tool
    @function_tool
    async def search_indus_net_knowledge_base(self, context: RunContext, question: str):
        """
        Search the official Indus Net Knowledge Base for information about the company. 
        Calling this tool will also trigger a visual update on the user interface.
        """
        logger.info(f"Searching knowledge base for: {question}")
        
        # 1. Fetch from Vector DB
        results = self.collection.query(
            query_texts=[question], n_results=self.db_fetch_size
        )
        documents = results.get("documents") or []

        # 2. Clean and Format Data
        flat_documents = [item for sublist in documents for item in sublist]
        joined = "\n\n---\n\n".join(doc.strip() for doc in flat_documents if doc.strip())
        cleaned = "\n".join(
            line for i, line in enumerate(joined.splitlines())
            if line.strip() and (i == 0 or line.strip() != joined.splitlines()[i-1].strip())
        )

        # 3. Trigger UI Stream (Visual Presenter Logic)
        # This runs in the background to ensure the voice response isn't delayed
        asyncio.create_task(
            asyncio.to_thread(
                lambda: asyncio.run(self._publish_ui_stream(question, cleaned))
            )
        )
        
        # 4. Return data to the LLM to narrate
        return cleaned

    # Publish UI Stream to frontend
    async def _publish_ui_stream(self, user_input: str, db_results: str) -> None:
        """Generate and publish UI cards, filtering out already-visible content."""
        
        # Generate a unique stream ID for this specific generation batch
        stream_id = str(uuid.uuid4())
        card_index = 0
        
        async for payload in self.ui_agent_functions.query_process_stream(
            user_input=user_input, db_results=db_results
        ):
            # Check for redundancy before publishing
            title = payload.get("title", "")
            _ = payload.get("id", payload.get("card_id", ""))
            
            # Inject grouping info
            payload["stream_id"] = stream_id
            payload["card_index"] = card_index
            card_index += 1
            
            try:
                await self.room.local_participant.publish_data(
                    json.dumps(payload).encode("utf-8"),
                    reliable=True,
                    topic="ui.flashcard",
                )
                logger.info("✅ Data packet sent successfully: %s (Stream: %s, Index: %s)", title, stream_id, payload["card_index"])
            except Exception as e:
                logger.error(f"❌ Failed to publish data: {e}")

        # ---- SEND END-OF-STREAM MARKER ----
        end_of_stream_payload = {
            "type": "end_of_stream",
            "stream_id": stream_id,
            "card_count": card_index
        }
        try:
            await self.room.local_participant.publish_data(
                json.dumps(end_of_stream_payload).encode("utf-8"),
                reliable=True,
                topic="ui.flashcard",
            )
            logger.info(f"✅ End-of-stream marker sent for stream: {stream_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send end-of-stream marker: {e}")

    # Get UI context from frontend and update agent instructions
    async def update_ui_context(self, context_payload: dict) -> None:
        """Process UI context sync from frontend and update agent state."""
        # Extract data from the payload
        screen = context_payload.get("viewport", {}).get("screen", "desktop")
        theme = context_payload.get("viewport", {}).get("theme", "light")
        max_visible_cards = context_payload.get("viewport", {}).get("capabilities", {}).get("maxVisibleCards", 4)
        active_elements = context_payload.get("active_elements", [])

        # Update the UI agent with the UI context
        ui_agent_context_payload = {"screen": screen, 
                                     "theme": theme, 
                                     "max_visible_cards": max_visible_cards,
                                     "active_elements": active_elements}
        await self.ui_agent_functions.update_instructions_with_context(ui_agent_context_payload)


        # Update the instructions with current active elements/UI state
        await self._update_instructions_with_context(active_elements)

    
    async def _update_instructions_with_context(self, active_elements: list = []) -> None:
        """Inject current UI state into agent instructions."""
        logger.debug("Agent instructions updated with UI context")
        if not active_elements:
            return

        # Change the active elements into markdown
        active_elements_md = "\n\n".join(f"- {element}" for element in active_elements)

        new_instructions = self._base_instruction + "\n Elements Currently Present in UI: \n" + active_elements_md

        # 🎯 This actually updates the LLM system prompt
        await self.update_instructions(new_instructions)
        
