import json
import os
import logging
import uuid
from typing import Literal
from livekit import api
from livekit.api import CreateRoomRequest
from livekit.protocol.sip import (CreateSIPOutboundTrunkRequest, 
                                  SIPOutboundTrunkInfo, 
                                  ListSIPOutboundTrunkRequest)
from google.protobuf.json_format import MessageToDict


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
            lkapi = api.LiveKitAPI()

            # Ensure unique room name
            unique_room_name = f"{agent_type}-outbound-{phone_number[-4:]}-{uuid.uuid4().hex[:6]}"

            room_request = CreateRoomRequest(
                name=unique_room_name,
                empty_timeout=60,           # Close 1 min after last participant
                max_participants=3,          # Agent + SIP participant only
                metadata=json.dumps({
                    "call_type": "outbound",
                    "agent": agent_type,
                    "phone": phone_number,
                    "trunk": call_from
                })
            )
            
            room = await lkapi.room.create_room(room_request)
            self.logger.info(f"Created room: {room.name} (sid: {room.sid})")
            
            # Metadata for dispatch
            metadata = json.dumps({"agent": agent_type, "phone": phone_number, "call_type": "outbound"})
            
            self.logger.info(f"Creating dispatch for agent {agent_type} in room {unique_room_name} trunk id {self.exotel_trunk_id}")
            
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="vyom_demos", room=unique_room_name, metadata=metadata
                )
            )

            self.logger.info(f"Created dispatch: {dispatch}")
            self.logger.info(f"Dialing {phone_number} to room {unique_room_name}")

            
            sip_participant = await lkapi.sip.create_sip_participant(
                    api.CreateSIPParticipantRequest(
                        room_name=unique_room_name,
                        sip_trunk_id=self.exotel_trunk_id if call_from == "exotel" else self.twilio_trunk_id,
                        sip_call_to=phone_number,
                        participant_identity=phone_number,
                        participant_metadata=metadata,
                        krisp_enabled=True,
                    )
                )

            self.logger.info(f"SIP participant created: {sip_participant}")
            
            payload = {
                "status" : 0,
                "message" : f"SIP participant request created",
                "data" :
                    {
                        "room" : unique_room_name,
                        "participant" : MessageToDict(sip_participant),
                        "dispatch" : MessageToDict(dispatch),
                        "trunk_id" : self.exotel_trunk_id,
                        "call_from" : call_from,
                        "call_to_phone_number" : phone_number
                    }
                
            }
            return payload

        except Exception as e:
            self.logger.error(f"Error creating SIP participant: {e}")
            return {
                "status" : -1,
                "message" : f"Error creating SIP participant: {e}",
                "data" : {}
            }
        finally:
            await lkapi.aclose()

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

            lkapi = api.LiveKitAPI()

            trunk = SIPOutboundTrunkInfo(
                name = trunk_name,
                address = trunk_address,
                numbers = trunk_numbers,
                auth_username = trunk_auth_username,
                auth_password = trunk_auth_password
            )

            request = CreateSIPOutboundTrunkRequest(
                trunk = trunk
            )

            trunk = await lkapi.sip.create_sip_outbound_trunk(request)

            self.logger.info(f"Successfully created {trunk}")
            
            payload = {
                "status" : 0,
                "message" : f"Successfully created trunk for {trunk_type}",
                "data" : MessageToDict(trunk)
            }

            return payload

        except Exception as e:
            self.logger.error(f"Error creating SIP outbound trunk: {e}")
            return {
                "status" : -1,
                "message" : f"Error creating SIP outbound trunk: {e}",
                "data" : {}
            }
        finally:
            await lkapi.aclose()


    # Lsit the outbound trunks 
    async def list_outbound_trunks(self):
        try:
            lkapi = api.LiveKitAPI()

            rules = await lkapi.sip.list_sip_outbound_trunk(
                    ListSIPOutboundTrunkRequest()
                )

            self.logger.info(f"Successfully listed outbound trunks: {rules}")
            rules_dict = MessageToDict(rules)
            
            payload = {
                "status" : 0,
                "message" : f"Successfully listed outbound trunks",
                "data" : rules_dict
            }

            return payload
        except Exception as e:
            self.logger.error(f"Error creating SIP outbound trunk: {e}")
            return {
                "status" : -1,
                "message" : f"Error creating SIP outbound trunk: {e}",
                "data" : {}
            }
        finally:
            await lkapi.aclose()