from openai import OpenAI
from agents.web.ai_integration.ui_agent_prompt import SYSTEM_INSTRUCTION
from agents.web.ai_integration.structure import UIStreamResponse
from typing import Any, AsyncGenerator
import json
import re
import os
import logging
from dotenv import load_dotenv
load_dotenv(override=True)


class UIAgentFunctions:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.llm_model = "gpt-4.1"
        self.logger = logging.getLogger(__name__)
        self.instructions = SYSTEM_INSTRUCTION

    async def query_process_stream(
        self, user_input: str, db_results: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        try:
            self.logger.info("Starting UI stream generation with user input: %s", user_input)
            
            with self.openai_client.responses.stream(
                model=self.llm_model,
                input=[
                    {"role": "system", "content": self.instructions},
                    {
                        "role": "user",
                        "content": f"""## Database Results
                        {db_results}

                        ## User Query
                        {user_input}

                        ## Your Task
                        Generate flashcards for NEW information only. Check active_elements above and skip any content already displayed.""",
                    },
                ],
                text_format=UIStreamResponse,
                temperature=0.3,
            ) as stream:
                buffer = ""

                # --- STATES ---
                # 0: Searching for "cards": [
                # 1: Parsing Card Objects { ... }
                state = 0

                for event in stream:
                    if event.type == "response.output_text.delta":
                        chunk = event.delta
                        buffer += chunk

                        # === STATE 0: LOOK FOR START OF CARDS ARRAY ===
                        if state == 0:
                            # We are looking for: "cards": [
                            # Use Regex to ignore whitespace/newlines/commas
                            match = re.search(r'"cards"\s*:\s*\[', buffer)
                            if match:
                                buffer = buffer[match.end() :]  # Cut past the [
                                state = 1

                        # === STATE 1: EXTRACT JSON OBJECTS ===
                        if state == 1:
                            # We are inside the array [ ... ]
                            # We need to find matching { and }

                            while True:
                                # Find the first opening brace
                                start_idx = buffer.find("{")
                                if start_idx == -1:
                                    break  # No object started yet, wait for more chunks

                                # Now scan for the matching closing brace
                                # We must count depth in case of nested objects (though unlikely for cards)
                                depth = 0
                                end_idx = -1

                                for k in range(start_idx, len(buffer)):
                                    if buffer[k] == "{":
                                        depth += 1
                                    elif buffer[k] == "}":
                                        depth -= 1
                                        if depth == 0:
                                            end_idx = k
                                            break

                                if end_idx != -1:
                                    # We have a full JSON string: { ... }
                                    raw_json = buffer[start_idx : end_idx + 1]

                                    try:
                                        card_obj = json.loads(raw_json)
                                        payload = await self._normalize_card_payload(card_obj)
                                        if payload:
                                            yield payload
                                    except:
                                        pass  # Skip if malformed

                                    # Remove this object from buffer and continue loop
                                    buffer = buffer[end_idx + 1 :]
                                else:
                                    # Object started but not finished (wait for next chunk)
                                    break

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    async def _normalize_card_payload(self, card_obj: dict) -> dict | None:
        if not isinstance(card_obj, dict):
            return None

        payload: dict[str, Any] = {"type": "flashcard"}
        
        # Include id for deduplication tracking
        for key in (
            "id",
            "title",
            "value",
            "visual_intent",
            "animation_style",
            "icon",
            "media",
            "accentColor",
            "theme",
            "size",
            "layout",
            "image",
        ):
            if key in card_obj and card_obj[key] is not None:
                payload[key] = card_obj[key]

        if "visual_intent" not in payload and "intent" in card_obj:
            payload["visual_intent"] = card_obj["intent"]
        
        if "animation_style" not in payload and "animation" in card_obj:
            payload["animation_style"] = card_obj["animation"]

        if "accent_color" in card_obj and "accentColor" not in payload:
            payload["accentColor"] = card_obj["accent_color"]
        if (
            "image_url" in card_obj
            or "image_alt" in card_obj
            or "image_aspect_ratio" in card_obj
        ):
            payload.setdefault("image", {})
            image = payload["image"] if isinstance(payload["image"], dict) else {}
            if "image_url" in card_obj:
                image["url"] = card_obj["image_url"]
            if "image_alt" in card_obj:
                image["alt"] = card_obj["image_alt"]
            if "image_aspect_ratio" in card_obj:
                image["aspectRatio"] = card_obj["image_aspect_ratio"]
            payload["image"] = image

        if "title" not in payload or "value" not in payload:
            return None

        return payload

    # Update the instructions with current active elements/UI state
    async def update_instructions_with_context(self, ui_context: dict) -> None:
        
        logging.info("Updating the instructions with UI context")
        # Comvert UI context to markdown format
        md = []
        for key, value in ui_context.items():
            md.append(f"**{key}**: `{json.dumps(value, indent=2) if isinstance(value, (dict, list)) else value}`")

        self.instructions = SYSTEM_INSTRUCTION +"\n\n The following is the current UI state. Generate the visual accodingly:\n\n" +"\n".join(md)