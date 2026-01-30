from livekit.agents import Agent    
from agents.invoice.invoice_agent_prompt import INVOICE_PROMPT
from shared_humanization_prompt.tts_humanification_cartesia import TTS_HUMANIFICATION_CARTESIA

class InvoiceAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=INVOICE_PROMPT + TTS_HUMANIFICATION_CARTESIA,
        )
        self.room = room

    @property
    def welcome_message(self):
        return ("Hi, This is VYOM calling from ITC's accounts team.")