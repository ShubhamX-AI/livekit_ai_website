import asyncio
import os
from dotenv import load_dotenv
from outbound.outbound_call import OutboundCall

load_dotenv(override=True)

async def main():
    outbound = OutboundCall()
    
    # Using the number from sip_test2.py
    # callee="08697421450"
    # Note: LiveKit might expect E.164 or might pass as is depending on trunk.
    # sip_test2.py used "08697421450" (without +91). 
    # Let's try to stick to what worked.
    
    phone_number = "08697421450" 
    agent_type = "invoice" # Or any other agent you want to test
    
    print(f"Initiating call to {phone_number} with agent {agent_type}...")
    
    result = await outbound.make_call(
        phone_number=phone_number,
        agent_type=agent_type,
        call_from="exotel"
    )
    
    print("Call result:", result)

if __name__ == "__main__":
    asyncio.run(main())
