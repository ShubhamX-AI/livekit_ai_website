from livekit.agents import (Agent)
import logging
from agents.restaurant_agent_prompt import RESTAURANT_AGENT_PROMPT

logger = logging.getLogger("agent")

class RestaurantAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=RESTAURANT_AGENT_PROMPT,
        )
        self.room = room 

    @property
    def welcome_message(self):
        return ("Hi, This is VYOM, your restaurant reservation calling agent. How can I help you today?")