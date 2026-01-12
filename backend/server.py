import os
import uuid
import logging
import json
from typing import Optional 

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from livekit import api as lk_api
from livekit.api import LiveKitAPI, ListRoomsRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

app = FastAPI(title="LiveKit Token Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

## The agent currently supported
ALLOWED_AGENTS = {"web", "invoice", "restaurant", "bank", "tour"}


async def get_rooms() -> list[str]:
    logger.info("Starting get_rooms")
    client = LiveKitAPI()
    try:
        rooms = await client.room.list_rooms(ListRoomsRequest())
        logger.info(f"Retrieved rooms: {[room.name for room in rooms.rooms]}")
        return [room.name for room in rooms.rooms]
    except Exception as e:
        logger.error(f"Error in get_rooms: {e}", exc_info=True)
        return []
    finally:
        await client.aclose()
        logger.info("Closed LiveKitAPI client in get_rooms")


async def generate_room_name(agent: str) -> str:
    """
    Generate a unique room per user, namespaced by agent.
    Example: web-a1b2c3d4
    """
    while True:
        room_name = f"{agent}-{uuid.uuid4().hex[:8]}"
        existing_rooms = await get_rooms()
        if room_name not in existing_rooms:
            return room_name


@app.get("/api/getToken", response_class=PlainTextResponse)
async def get_token(name: str = Query("guest"), agent: str = Query("web") ,room: Optional[str] = Query(None)):
    logger.info(f"Received getToken request: name={name}, room={room}, agent={agent}")
    
    # Validation for each agent
    if agent not in ALLOWED_AGENTS:
        return "Invalid agent"
    if not room:
        room = await generate_room_name(agent=agent)

    try:
        token = (
            lk_api.AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET"))
            .with_identity(name)
            .with_name(name)
            .with_metadata(json.dumps({"agent": agent}))
            .with_grants(
                lk_api.VideoGrants(
                    room_join=True,
                    room=room,
                )
            )
        )
        jwt = token.to_jwt()
        logger.info(f"JWT issued | room={room} | agent={agent}")
        return jwt
    except Exception as e:
        logger.error(f"Error generating JWT: {e}", exc_info=True)
        return "Error generating token."


# Pssword check
@app.get("/api/checkPassword", response_class=PlainTextResponse)
async def check_password(password: str = Query("guest")):
    if password.lower() == 'lvk_agents':
        return "ok"
    else:
        return "Unauthorized"

@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)