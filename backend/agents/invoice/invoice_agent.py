from livekit.agents import (Agent)
import logging
from agents.invoice.invoice_agent_prompt import INVOICE_PROMPT
from agents.shared import TTS_HUMANIFICATION_FRAMEWORK

logger = logging.getLogger("agent")

class InvoiceAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=INVOICE_PROMPT + TTS_HUMANIFICATION_FRAMEWORK,
        )
        self.room = room 

    @property
    def welcome_message(self):
        return ("<emotion value='content' />Hi, This is VYOM calling from ITC’s accounts team.")