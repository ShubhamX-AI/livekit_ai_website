from livekit.agents import (Agent)
import logging
from agents.realestate.realestate_agent_prompt import REALESTATE_PROMPT_5

logger = logging.getLogger("agent")

class RealestateAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=REALESTATE_PROMPT_5,
        )
        self.room = room 

    @property
    def welcome_message(self):
        # welcome_message = f"<emotion value='content' />“Hello sir, good day. May I speak with Avi please?”"
        welcome_message = (
            "Hi Ravi, this is VYOM calling from the House of Abhinandan Lodha. "
            "You had shown interest in one of our residential projects, so I thought I’d reach out personally. "
            "I just wanted to understand what you were looking for and share relevant details accordingly. "
            "Is this a convenient time to speak for a couple of minutes?"
                            )
        return welcome_message