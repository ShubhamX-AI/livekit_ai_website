import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    cli,
    inference,
    room_io,
    BackgroundAudioPlayer, 
    AudioConfig,           
    BuiltinAudioClip       
)
from livekit.plugins import noise_cancellation, silero, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from agents.web_agent import Webagent
from livekit.plugins.openai import realtime
from openai.types.beta.realtime.session import TurnDetection

logger = logging.getLogger("agent")
load_dotenv()
server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: JobContext):

    # session = AgentSession(
    #     stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
    #     llm=inference.LLM(model="openai/gpt-4.1-mini"),
    #     tts=inference.TTS(model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
    #     turn_detection=MultilingualModel(),
    #     vad=silero.VAD.load(min_speech_duration=0.3, activation_threshold=0.6),
    #     preemptive_generation=True, # True = tarts talking immediately.
    # )

    session = AgentSession(
        llm=realtime.RealtimeModel(
            model = "gpt-realtime",
            voice="marin",
            turn_detection=TurnDetection(
                type="semantic_vad",
                eagerness="high",
                create_response=True,
                interrupt_response=True,
            ),
            modalities = ['text']
        ),
        tts=inference.TTS(model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
        turn_detection=MultilingualModel(),
        vad=silero.VAD.load(min_speech_duration=0.3, activation_threshold=0.6),
        preemptive_generation=True,
        use_tts_aligned_transcript=True,
    )

    # --- Background Audio Setup ---
    # background_audio = BackgroundAudioPlayer(
    # ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=1.0),
    # thinking_sound=[
    #     AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=1.0),
    #     ],
    # )
      

    # Start the session
    await session.start(
        agent=Webagent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    # --- Background Audio Setup --- 
    background_audio = BackgroundAudioPlayer(ambient_sound="D:/code/ai_website/livekit_ai_website/office-ambience-6322.mp3")
    await background_audio.start(room=ctx.room, agent_session=session)
        
    # --- INITIATING SPEECH (The Agent Speaks First) ---
    welcome_message = "Welcome to Indus Net Technologies. I am marin. How can I help you today?"
    await session.say(text=welcome_message, allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(server)