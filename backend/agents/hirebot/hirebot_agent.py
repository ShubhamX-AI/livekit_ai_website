from livekit.agents import Agent
from agents.hirebot.hirebot_agent_prompt import HIREBOT_PROMPT
from shared_humanization_prompt.tts_humanification_cartesia import TTS_HUMANIFICATION_CARTESIA

class HirebotAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions= HIREBOT_PROMPT + TTS_HUMANIFICATION_CARTESIA,
        )
        self.room = room

    @property
    def welcome_message(self):
        return ("Hello")