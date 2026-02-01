# from agents.base_agent import BaseAgentWithCustomSTT
from livekit.agents import function_tool, RunContext, Agent
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
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
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddings,
            collection_name="indus_net_knowledge"
        )
        self.db_fetch_size = 10
        self.db_results = ""
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
        """
        logger.info(f"Searching knowledge base for: {question}")
        await self._vector_db_search(question)
        return self.db_results
        
    # Publish UI Stream to frontend
    @function_tool
    async def publish_ui_stream(self, context: RunContext, user_input: str, agent_response: str) -> None:
        """
        Publish the UI stream to the frontend.
        Call this tool AFTER searching the knowledge base.
        Pass the original 'user_input', and your formulated 'agent_response'.
        This will generate and display flashcards on the user's screen.
        """
        logger.info(f"Publishing UI stream for: {user_input}")
        
        # This runs in the background to ensure the voice response isn't delayed
        asyncio.create_task(self._publish_ui_stream(user_input, self.db_results, agent_response))
        return "UI stream published."

    # Publish UI Stream to frontend
    async def _publish_ui_stream(self, user_input: str, db_results: str, agent_response: str) -> None:
        """Generate and publish UI cards, filtering out already-visible content."""
        
        # Generate a unique stream ID for this specific generation batch
        stream_id = str(uuid.uuid4())
        card_index = 0
        
        async for payload in self.ui_agent_functions.query_process_stream(
            user_input=user_input, db_results=db_results, agent_response=agent_response
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

    # Vector db search and retun in Markdown
    async def _vector_db_search(self, query: str) -> str:
        """Search the vector database for relevant information."""
        # 1. Fetch from Vector DB
        results = self.vectorstore.similarity_search(
            query=query, k=self.db_fetch_size
        )
        
        formatted_results = []
        for i, doc in enumerate(results):
            content = doc.page_content.strip()
            meta = doc.metadata
            
            # Start with the main content
            md_chunk = f"### Result {i+1}\n\n{content}\n"
            
            # 2. Extract and format ALL metadata dynamically
            details = []
            for key, val in meta.items():
                # Skip internal/empty keys if necessary (e.g., 'source_content_focus')
                if not val or key in ["source_content_focus"]:
                    continue

                human_key = key.replace("_", " ").title()
                
                # Check if it's a JSON string (list or dict)
                if isinstance(val, str) and val.strip().startswith(("[", "{")):
                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, list):
                            formatted_val = ", ".join(map(str, parsed))
                        elif isinstance(parsed, dict):
                            formatted_val = ", ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in parsed.items()])
                        else:
                            formatted_val = str(parsed)
                        
                        details.append(f"**{human_key}:** {formatted_val}")
                    except:
                        # Fallback for invalid JSON
                        details.append(f"**{human_key}:** {val}")
                else:
                    # Regular value
                    details.append(f"**{human_key}:** {val}")

            if details:
                md_chunk += "\n" + "\n".join([f"- {d}" for d in details])
            
            formatted_results.append(md_chunk)

        self.db_results = "\n\n---\n\n".join(formatted_results)
        logger.info(f"✅ DB results converted to markdown")
        return self.db_results

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

    # Update instructions with current active elements/UI state
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
        
