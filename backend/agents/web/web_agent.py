# from agents.base_agent import BaseAgentWithCustomSTT
from livekit.agents import function_tool, RunContext, Agent
import chromadb
import logging
import json
import asyncio
from agents.web.web_agent_prompt import WEB_AGENT_PROMPT
from shared_humanization_prompt.tts_humanificaiton_elevnlabs import (
    TTS_HUMANIFICATION_ELEVNLABS,
)

logger = logging.getLogger(__name__)


class Webagent(Agent):
    def __init__(self, room) -> None:
        self._base_instructions = WEB_AGENT_PROMPT + TTS_HUMANIFICATION_ELEVNLABS
        super().__init__(
            # Instructions for the agent
            instructions=self._base_instructions,
        )
        self.room = room
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="indusnet_website"
        )
        self.db_fetch_size = 5
        self.ui_context: dict[str, object] = {}

    def _build_ui_context_prompt(self) -> str:
        if not self.ui_context:
            return ""
        lines = ["\n# Runtime UI Context (ALWAYS RESPECT)", "ui_context_runtime:"]
        for key in ("maxCardChars", "cardSize", "screen", "density", "theme"):
            value = self.ui_context.get(key)
            if value is None:
                continue
            lines.append(f"  {key}: {value}")
        if len(lines) == 2:
            return ""
        lines.extend(
            [
                "rules:",
                "  - 'Use maxCardChars to keep markdown concise'",
                "  - 'Use cardSize when available; otherwise infer from screen'",
                "  - 'Keep visual choices consistent with density and theme'",
            ]
        )
        return "\n".join(lines) + "\n"

    def _refresh_instructions(self) -> None:
        updated = self._base_instructions + self._build_ui_context_prompt()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._instructions = updated
            return
        loop.create_task(self.update_instructions(updated))

    def update_ui_context(self, context_payload: dict) -> None:
        if not isinstance(context_payload, dict):
            logger.info("UI context ignored (non-dict payload)")
            return
        logger.info("UI context received: %s", context_payload)
        max_chars = context_payload.get("maxCardChars")
        if max_chars is None:
            max_chars = context_payload.get("maxChars")
        if isinstance(max_chars, int) and max_chars > 0:
            self.ui_context["maxCardChars"] = max_chars
        card_size = context_payload.get("cardSize")
        if isinstance(card_size, str) and card_size.strip():
            self.ui_context["cardSize"] = card_size.strip()
        screen = context_payload.get("screen") or context_payload.get("screenType")
        if isinstance(screen, str) and screen.strip():
            self.ui_context["screen"] = screen.strip()
        density = context_payload.get("density")
        if isinstance(density, str) and density.strip():
            self.ui_context["density"] = density.strip()
        theme = context_payload.get("theme") or context_payload.get("themeToken")
        if isinstance(theme, str) and theme.strip():
            self.ui_context["theme"] = theme.strip()
        logger.info("UI context applied: %s", self.ui_context)
        self._refresh_instructions()

    def _truncate_markdown(self, value: str) -> str:
        max_chars = self.ui_context.get("maxCardChars")
        if not isinstance(max_chars, int) or max_chars <= 0:
            return value
        if len(value) <= max_chars:
            return value
        if max_chars <= 3:
            return value[:max_chars]
        trimmed = value[: max_chars - 3].rstrip()
        return f"{trimmed}..."

    def _normalize_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.lower() in {"undefined", "null", "none", "nil"}:
            return None
        return cleaned

    def _normalize_size(self, value: str | None) -> str | None:
        cleaned = self._normalize_optional(value)
        if not cleaned:
            return None
        size_map = {
            "small": "sm",
            "medium": "md",
            "large": "lg",
            "sm": "sm",
            "md": "md",
            "lg": "lg",
        }
        return size_map.get(cleaned.lower())

    def _normalize_list(self, values: list[str] | None) -> list[str] | None:
        if not values:
            return None
        cleaned: list[str] = []
        for item in values:
            if not isinstance(item, str):
                continue
            normalized = self._normalize_optional(item)
            if normalized:
                cleaned.append(normalized)
        return cleaned or None

    @property
    def welcome_message(self):
        return (
            "Welcome to Indus Net Technologies."
            " I'm Vyom, your web assistant. How can I help you today?"
        )

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

        return cleaned

    @function_tool
    async def emit_flashcard(
        self,
        context: RunContext,
        title: str,
        value: str,
        card_id: str | None = None,
        accent_color: str | None = None,
        icon: str | None = None,
        theme: str | None = None,
        size: str | None = None,
        image_url: str | None = None,
        image_alt: str | None = None,
        image_aspect_ratio: str | None = None,
        layout: str | None = None,
        priority: int | None = None,
        expiry_ms: int | None = None,
        source: str | None = None,
        citation: list[str] | None = None,
        tags: list[str] | None = None,
    ):
        """
        Emit a flashcard fact.
        This tool is called by the LLM during answer generation.
        """
        logger.info(f"Emitting flashcard: {title}")

        value = self._truncate_markdown(value)
        payload: dict[str, object] = {
            "type": "flashcard",
            "title": title,
            "value": value,
        }

        normalized_card_id = self._normalize_optional(card_id)
        normalized_accent_color = self._normalize_optional(accent_color)
        normalized_icon = self._normalize_optional(icon)
        normalized_theme = self._normalize_optional(theme)
        normalized_layout = self._normalize_optional(layout)
        normalized_image_url = self._normalize_optional(image_url)
        normalized_image_alt = self._normalize_optional(image_alt)
        normalized_image_aspect_ratio = self._normalize_optional(image_aspect_ratio)
        normalized_source = self._normalize_optional(source)
        normalized_size = self._normalize_size(size)

        if normalized_card_id:
            payload["id"] = normalized_card_id
        if normalized_accent_color:
            payload["accentColor"] = normalized_accent_color
        if normalized_icon:
            payload["icon"] = normalized_icon
        if normalized_theme:
            payload["theme"] = normalized_theme
        resolved_size = None
        if normalized_size:
            payload["size"] = normalized_size
            resolved_size = normalized_size
        else:
            card_size = self.ui_context.get("cardSize")
            if isinstance(card_size, str) and card_size.strip():
                payload["size"] = card_size.strip()
                resolved_size = card_size.strip()
            else:
                screen = self.ui_context.get("screen")
                if screen == "mobile":
                    payload["size"] = "sm"
                    resolved_size = "sm"
                elif screen == "desktop":
                    payload["size"] = "md"
                    resolved_size = "md"
                elif screen == "vr":
                    payload["size"] = "lg"
                    resolved_size = "lg"
        if resolved_size or isinstance(self.ui_context.get("maxCardChars"), int):
            logger.info(
                "Flashcard ui context applied: size=%s maxCardChars=%s",
                resolved_size,
                self.ui_context.get("maxCardChars"),
            )
        if normalized_image_url:
            payload["image"] = {
                "url": normalized_image_url,
                "alt": normalized_image_alt or "",
                "aspectRatio": normalized_image_aspect_ratio or "",
            }
        if normalized_layout:
            payload["layout"] = normalized_layout
        if priority is not None:
            payload["priority"] = priority
        if expiry_ms is not None:
            payload["expiryMs"] = expiry_ms
        if normalized_source:
            payload["source"] = normalized_source
        normalized_citation = self._normalize_list(citation)
        if normalized_citation:
            payload["citation"] = normalized_citation
        normalized_tags = self._normalize_list(tags)
        if normalized_tags:
            payload["tags"] = normalized_tags

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
