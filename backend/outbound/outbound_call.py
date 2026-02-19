import os
import logging
import uuid
from typing import Literal
from google.protobuf.json_format import MessageToDict

# Import centralized LiveKit services
from services.lvk_services import (
    create_room,
    create_agent_dispatch,
    create_sip_participant,
    create_sip_outbound_trunk,
    list_sip_outbound_trunks,
    format_success_response,
    format_success_response,
    format_error_response
)
import sys
# Allow importing sip_bridge from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from custom_sip_reach import run_bridge
import asyncio


class OutboundCall:

    def __init__(self):
        self.exotel_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID_EXOTEL")
        self.twilio_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID_TWILIO")
        self.room_name = "outbound-call"
        self.logger = logging.getLogger("outbound-call")
    

    # Create dispatch and add a SIP participant to call the phone number   
    async def make_call(self, phone_number: str, 
                        agent_type: str = "invoice", 
                        call_from: Literal["exotel", "twilio"] = "exotel"):
        try:
            # Ensure unique room name
            unique_room_name = f"{agent_type}-outbound-{phone_number[-4:]}-{uuid.uuid4().hex[:6]}"

            # Room metadata
            room_metadata = {
                "call_type": "outbound",
                "agent": agent_type,
                "phone": phone_number,
                "trunk": call_from
            }
            
            # Create room using centralized service
            room = await create_room(
                room_name=unique_room_name,
                agent=agent_type,
                empty_timeout=60,           # Close 1 min after last participant
                max_participants=3,         # Agent + SIP participant only
                metadata=room_metadata
            )
            
            # Metadata for dispatch and participant
            metadata = {
                "agent": agent_type,
                "phone": phone_number,
                "call_type": "outbound"
            }
            
            self.logger.info(f"Creating dispatch for agent {agent_type} in room {unique_room_name}")
            
            # Create agent dispatch using centralized service
            dispatch = await create_agent_dispatch(
                room=unique_room_name,
                agent_name="vyom_demos",
                metadata=metadata
            )

            self.logger.info(f"Created dispatch: {dispatch}")
            self.logger.info(f"Dialing {phone_number} to room {unique_room_name}")

            
            if call_from == "exotel":
                # Use custom SIP bridge — pass the EXISTING room name
                # so the bridge joins the same room where the agent was dispatched.
                self.logger.info(
                    f"Triggering SIP Bridge for {phone_number} "
                    f"with agent {agent_type} in room {unique_room_name}"
                )
                
                asyncio.create_task(
                    run_bridge(
                        phone_number=phone_number,
                        agent_type=agent_type,
                        room_name=unique_room_name,
                    )
                )
                
                return format_success_response(
                    message="SIP Bridge Initiated",
                    data={
                        "room": unique_room_name,
                        "call_to_phone_number": phone_number,
                        "agent": agent_type,
                        "method": "custom_bridge"
                    }
                )

            # Standard Logic for Twilio/Others
            # Select trunk based on call_from parameter
            trunk_id = self.exotel_trunk_id if call_from == "exotel" else self.twilio_trunk_id
            
            # Create SIP participant using centralized service
            sip_participant = await create_sip_participant(
                room_name=unique_room_name,
                trunk_id=trunk_id,
                call_to=phone_number,
                identity=phone_number,
                metadata=metadata,
                krisp_enabled=True
            )

            self.logger.info(f"SIP participant created: {sip_participant}")
            
            # Format success response
            return format_success_response(
                message="SIP participant request created",
                data={
                    "room": unique_room_name,
                    "participant": MessageToDict(sip_participant),
                    "dispatch": MessageToDict(dispatch),
                    "trunk_id": trunk_id,
                    "call_from": call_from,
                    "call_to_phone_number": phone_number
                }
            )

        except Exception as e:
            self.logger.error(f"Error creating SIP participant: {e}")
            return format_error_response(
                message="Error creating SIP participant",
                error=e
            )

    # Create Outbound trunk
    async def create_outbound_trunk(self, 
                                    trunk_name: str = "", 
                                    trunk_address: str = "", 
                                    trunk_numbers: list = [], 
                                    trunk_auth_username: str = "", 
                                    trunk_auth_password: str = "",
                                    trunk_type: Literal["exotel", "twilio"] = "exotel"
                                    ):
        try:
            self.logger.info(f"Received outbound trunk request: {trunk_name}, {trunk_address}, {trunk_numbers}, {trunk_auth_username}, {trunk_auth_password}, {trunk_type}")

            # Create trunk using centralized service
            trunk = await create_sip_outbound_trunk(
                trunk_name=trunk_name,
                trunk_address=trunk_address,
                trunk_numbers=trunk_numbers,
                trunk_auth_username=trunk_auth_username,
                trunk_auth_password=trunk_auth_password
            )

            self.logger.info(f"Successfully created {trunk}")
            
            # Format success response
            return format_success_response(
                message=f"Successfully created trunk for {trunk_type}",
                data=MessageToDict(trunk)
            )

        except Exception as e:
            self.logger.error(f"Error creating SIP outbound trunk: {e}")
            return format_error_response(
                message="Error creating SIP outbound trunk",
                error=e
            )


    # List the outbound trunks 
    async def list_outbound_trunks(self):
        try:
            # List trunks using centralized service
            trunks_dict = await list_sip_outbound_trunks()

            self.logger.info(f"Successfully listed outbound trunks: {trunks_dict}")
            
            # Format success response
            return format_success_response(
                message="Successfully listed outbound trunks",
                data=trunks_dict
            )

        except Exception as e:
            self.logger.error(f"Error listing SIP outbound trunks: {e}")
            return format_error_response(
                message="Error listing SIP outbound trunks",
                error=e
            )