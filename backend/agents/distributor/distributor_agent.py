from livekit.agents import (Agent)
import logging
from agents.distributor.distributor_agent_prompt import DISTRIBUTOR_PROMPT
# from agents.shared.tts_humanification_framework import TTS_HUMANIFICATION_FRAMEWORK

logger = logging.getLogger("agent")

class DistributorAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=DISTRIBUTOR_PROMPT,
        )
        self.room = room 

    @property
    def welcome_message(self):
        # welcome_message = f"<emotion value='content' />“Hello sir, good day. May I speak with Avi please?”"
        welcome_message = '<emotion value="warm"/> Namaste, this is Vilok from Aryan Veda. <break time="300ms"/> <emotion value="respectful"/> Am I speaking with Suresh Agarwal?'
        return welcome_message