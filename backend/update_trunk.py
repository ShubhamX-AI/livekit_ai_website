import asyncio
import json
import os
from dotenv import load_dotenv
from services.lvk_services import create_sip_outbound_trunk

load_dotenv(override=True)

async def main():
    try:
        with open("outbound_trunk_exotel.json", "r") as f:
            config = json.load(f)
            
        trunk_data = config["trunk"]
        
        print(f"Creating trunk with: {trunk_data}")
        
        trunk = await create_sip_outbound_trunk(
            trunk_name=trunk_data["name"],
            trunk_address=trunk_data["address"],
            trunk_numbers=trunk_data["numbers"],
            trunk_auth_username=trunk_data["authUsername"],
            trunk_auth_password=trunk_data["authPassword"]
        )
        
        print(f"Trunk created/updated successfully: {trunk}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
