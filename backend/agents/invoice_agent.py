from livekit.agents import (Agent)
import logging
from agents.invoice_agent_prompt import INVOICE_PROMPT

logger = logging.getLogger("agent")

class InvoiceAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=INVOICE_PROMPT,
        )
        self.room = room 

    @property
    def welcome_message(self):
        return ("Hi, This is VYOM calling from ITC’s accounts team.")