from pydantic import BaseModel, Field


class FlashcardImage(BaseModel):
    url: str | None = None
    alt: str | None = None
    aspectRatio: str | None = None


class SmartIcon(BaseModel):
    type: str = "static"  # "static" | "animated"
    ref: str
    fallback: str | None = "info"


class DynamicMedia(BaseModel):
    source: str = "unsplash"  # "unsplash" | "pexels"
    query: str


class Flashcard(BaseModel):
    type: str = "flashcard"
    id: str | None = None  # Stable ID for deduplication
    title: str
    value: str
    visual_intent: str | None = "neutral"  # "neutral" | "urgent" | "success" | "warning" | "processing" | "cyberpunk"
    animation_style: str | None = "pop"  # "slide" | "pop" | "fade" | "flip" | "scale"
    icon: SmartIcon | str | None = None
    media: DynamicMedia | None = None
    accentColor: str | None = None
    theme: str | None = None
    size: str | None = "md"  # "sm" | "md" | "lg"
    layout: str | None = "default"  # "default" | "horizontal" | "centered" | "media-top"
    image: FlashcardImage | None = None


class UIStreamResponse(BaseModel):
    cards: list[Flashcard] = Field(default_factory=list)
