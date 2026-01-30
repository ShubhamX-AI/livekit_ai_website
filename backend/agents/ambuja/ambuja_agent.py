from livekit.agents import Agent
from agents.ambuja.ambuja_agent_prompt import AMBUJA_AGENT_PROMPT
from shared_humanization_prompt.tts_humanification_cartesia import TTS_HUMANIFICATION_CARTESIA

class AmbujaAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=AMBUJA_AGENT_PROMPT + TTS_HUMANIFICATION_CARTESIA,
        )
        self.room = room

    @property
    def welcome_message(self):
        return ("Namaskar ... Welcome to Ambuja Neotia. I'm Pratik. How can I assist you with Utalika Luxury today? ...")