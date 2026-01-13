from livekit.agents import (Agent)
import logging
from agents.banking.banking_agent_prompt import BANKING_AGENT_PROMPT2
from agents.shared import TTS_HUMANIFICATION_FRAMEWORK

logger = logging.getLogger("agent")

class BankingAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=BANKING_AGENT_PROMPT2 + TTS_HUMANIFICATION_FRAMEWORK,
        )
        self.room = room 

    @property
    def welcome_message(self):
        return ("<emotion value='content' />Hi, This is VYOM your banking agent.")