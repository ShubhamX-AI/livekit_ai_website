from livekit.agents import Agent
from agents.tour.tour_agent_prompt import TOUR_AGENT_PROMPT
from agents.shared import TTS_HUMANIFICATION_FRAMEWORK

class TourAgent(Agent):
    def __init__(self, room) -> None:
        super().__init__(
            # Instructions for the agent
            instructions=TOUR_AGENT_PROMPT + TTS_HUMANIFICATION_FRAMEWORK,
        )
        self.room = room 

    @property
    def welcome_message(self):
        return ("<emotion value='content' />Johar! Welcome to the Land of Forests! I am VYOM, your official Jharkhand Tourism (JTDC) Concierge.")