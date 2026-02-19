import os
import uuid
import logging
import json
from typing import Optional 

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from livekit.api import AccessToken, VideoGrants
from pydantic import BaseModel
from api_data_structure.structure import OutboundCallRequest, OutboundTrunkCreate, SIPTestRequest
import asyncio

# Import the outbound call function
from outbound.outbound_call import OutboundCall
from inbound.config_manager import set_agent_for_number, get_agent_for_number

# Import centralized LiveKit services
from services.lvk_services import (
    list_rooms,
    create_room,
    create_agent_dispatch
)

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
ALLOWED_AGENTS = {"web", "invoice", "restaurant", "bank", "tour", 
"realestate", "distributor", "bandhan_banking", "ambuja", "hirebot"}

# Initialize the classes
outbound_call = OutboundCall()

# Removed helper functions - now using centralized services from lvk_services
# - get_rooms() -> list_rooms()
# - dispatch_request() -> create_agent_dispatch()
# - create_room() -> create_room()


async def generate_room_name(agent: str) -> str:
    """
    Generate a unique room per user, namespaced by agent.
    Example: web-a1b2c3d4
    """
    room_name = f"{agent}-{uuid.uuid4().hex[:8]}"
    
    # Use centralized services
    await create_room(
        room_name=room_name,
        agent=agent,
        empty_timeout=30,
        max_participants=2
    )
    
    await create_agent_dispatch(
        room=room_name,
        agent_name="vyom_demos",
        metadata={"agent": agent, "source": "token_server"}
    )
    
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
            AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET"))
            .with_identity(name)
            .with_name(name)
            .with_metadata(json.dumps({"agent": agent}))
            .with_grants(
                VideoGrants(
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


# Make outbound call
@app.post("/api/makeCall")
async def trigger_outbound_call(data: OutboundCallRequest):
    logger.info(f"Received outbound call request: {data}")
    
    if data.agent_type not in ALLOWED_AGENTS:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {data.agent_type}. Allowed: {ALLOWED_AGENTS}")
        
    try:
        res = await outbound_call.make_call(data.phone_number, data.agent_type, data.call_from)
        return res
    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Create Outboud trunk
@app.post("/api/createOutboundTrunk")
async def create_outbound_trunk(data: OutboundTrunkCreate):
    logger.info(f"Received outbound trunk request: {data}")
    
    try:
        res = await outbound_call.create_outbound_trunk(data.trunk_name, 
                                          data.trunk_address, 
                                          data.trunk_numbers, 
                                          data.trunk_auth_username, 
                                          data.trunk_auth_password,
                                          data.trunk_type
                                          )
        return res
    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

# List outbound trunks
@app.get("/api/listOutboundTrunks")
async def list_outbound_trunks():
    try:
        res = await outbound_call.list_outbound_trunks()
        return res
    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))





class InboundAgentRequest(BaseModel):
    phone_number: str
    agent_type: str

@app.post("/api/setInboundAgent")
async def set_inbound_agent(request: InboundAgentRequest):
    logger.info(f"Received inbound agent set request: {request}")
    
    if request.agent_type not in ALLOWED_AGENTS:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {request.agent_type}. Allowed: {ALLOWED_AGENTS}")
    
    set_agent_for_number(request.phone_number, request.agent_type)
    return JSONResponse(content={"status": "success", "message": f"Linked {request.phone_number} to agent {request.agent_type}"})

@app.get("/api/getInboundAgent")
async def get_inbound_agent(phone_number: str = Query(...)):
    mapped_agent = get_agent_for_number(phone_number)
    return JSONResponse(content={"phone_number": phone_number, "agent_type": mapped_agent})

@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"

# Test SIP
from sip_test import make_exotel_call

# {
#   "exotel_ip": "pstn.in4.exotel.com",
#   "exotel_port": 5070,
#   "customer_ip": "13.234.150.174",
#   "customer_port": 5061,
#   "media_ip": "13.234.150.174",
#   "rtp_port": 18232,
#   "caller": "+918044319240",
#   "callee": "+918697421450"
# }

@app.post("/api/testsip")
async def trigger_sip_test_call(data: SIPTestRequest):
    logger.info(f"Received SIP test call request: {data}")
        
    try:
        # Since make_exotel_call uses blocking sockets, run it in a thread
        res = await asyncio.to_thread(
            make_exotel_call,
            exotel_ip=data.exotel_ip,
            exotel_port=data.exotel_port,
            customer_ip=data.customer_ip,
            customer_port=data.customer_port,
            media_ip=data.media_ip,
            rtp_port=data.rtp_port,
            caller=data.caller,
            callee=data.callee
        )
        return res
    except Exception as e:
        logger.error(f"Failed to initiate SIP test call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)