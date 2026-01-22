from livekit.agents import (Agent)
import logging
from agents.bandhan_banking.bandhan_banking_prompt import BANDHAN_BANKING_AGENT_PROMPT

logger = logging.getLogger("agent")

class BandhanBankingAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=BANDHAN_BANKING_AGENT_PROMPT,
        )
        self.room = room 

    @property
    def welcome_message(self):
        return ("Hi, This is VYOM your bandhan banking agent.")