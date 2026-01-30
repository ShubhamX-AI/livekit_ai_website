from livekit.agents import Agent
from agents.restaurant.restaurant_agent_prompt import RESTAURANT_AGENT_PROMPT
from shared_humanization_prompt.tts_humanification_cartesia import TTS_HUMANIFICATION_CARTESIA


class RestaurantAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=RESTAURANT_AGENT_PROMPT + TTS_HUMANIFICATION_CARTESIA,
        )
        self.room = room

    @property
    def welcome_message(self):
        return ("Hi, This is VYOM, your restaurant reservation calling agent. How can I help you today?")