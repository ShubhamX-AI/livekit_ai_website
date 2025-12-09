import os
import uuid
import logging
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

load_dotenv()

app = FastAPI(title="LiveKit Token Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


async def generate_room_name() -> str:
    logger.info("Starting generate_room_name")
    name = "room-" + str(uuid.uuid4())[:8]
    try:
        rooms = await get_rooms()
        logger.info(f"Current rooms: {rooms}")
        while name in rooms:
            logger.info(f"Generated name '{name}' already exists. Generating a new one.")
            name = "room-" + str(uuid.uuid4())[:8]
    except Exception as e:
        logger.error(f"Error in generate_room_name: {e}", exc_info=True)
    logger.info(f"Generated unused room name: {name}")
    return name


@app.get("/api/getToken", response_class=PlainTextResponse)
async def get_token(name: str = Query("guest"), room: Optional[str] = Query(None)):
    logger.info(f"Received getToken request: name={name}, room={room}")
    if not room:
        room = await generate_room_name()

    try:
        token = (
            lk_api.AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET"))
            .with_identity(name)
            .with_name(name)
            .with_grants(
                lk_api.VideoGrants(
                    room_join=True,
                    room=room,
                )
            )
        )
        jwt = token.to_jwt()
        logger.info(f"Generated JWT for room {room}")
        return jwt
    except Exception as e:
        logger.error(f"Error generating JWT: {e}", exc_info=True)
        return "Error generating token."


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"