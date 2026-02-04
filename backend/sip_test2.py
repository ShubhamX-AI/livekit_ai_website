import socket
import uuid
import random
import time

# --- CONFIGURATION (UPDATE THESE) ---
EXOTEL_PROXY = "pstn.in4.exotel.com"  # From Doc: Mumbai DC
EXOTEL_PORT = 5070                    # From Doc: TCP Port 5070
YOUR_PUBLIC_IP = "13.234.150.174"        # MUST be the IP whitelisted by Exotel
YOUR_LOCAL_PORT = 5060                # Port you are listening on
FROM_NUMBER = "+918044319240"         # Your Exotel Virtual Number (Exophone)
TO_NUMBER = "+918697421450"           # The destination mobile number

# --- GENERATE UNIQUE IDs ---
call_id = f"{uuid.uuid4()}@exotelt.pstn.exotel.com"
branch_id = f"z9hG4bK{uuid.uuid4()}"
tag_id = f"as{random.randint(100000, 999999)}"
local_rtp_port = 18232  # The port where you would expect audio (SDP)

# --- CONSTRUCT SDP BODY (Media Negotiation) ---
# As per doc: G.711 PCMA/PCMU
sdp_body = (
    f"v=0\r\n"
    f"o=root 1002281923 1002281923 IN IP4 {YOUR_PUBLIC_IP}\r\n"
    f"c=IN IP4 {YOUR_PUBLIC_IP}\r\n"
    f"t=0 0\r\n"
    f"m=audio {local_rtp_port} RTP/AVP 8 0 101\r\n"
    f"a=rtpmap:8 PCMA/8000\r\n"
    f"a=rtpmap:0 PCMU/8000\r\n"
    f"a=rtpmap:101 telephone-event/8000\r\n"
    f"a=fmtp:101 0-16\r\n"
    f"a=ptime:20\r\n"
    f"a=maxptime:150\r\n"
    f"a=sendrecv\r\n"
)

# --- CONSTRUCT SIP HEADERS ---
# Note: Content-Length must match the byte size of sdp_body
sip_invite = (
    f"INVITE sip:{TO_NUMBER}@{EXOTEL_PROXY}:{EXOTEL_PORT} SIP/2.0\r\n"
    f"Via: SIP/2.0/TCP {YOUR_PUBLIC_IP}:{YOUR_LOCAL_PORT};branch={branch_id}\r\n"
    f"Max-Forwards: 70\r\n"
    f"From: \"{FROM_NUMBER}\" <sip:{FROM_NUMBER}@exotelt.pstn.exotel.com>;tag={tag_id}\r\n"
    f"To: <sip:{TO_NUMBER}@{EXOTEL_PROXY}>\r\n"
    f"Contact: <sip:{FROM_NUMBER}@{YOUR_PUBLIC_IP}:{YOUR_LOCAL_PORT};transport=tcp>\r\n"
    f"Call-ID: {call_id}\r\n"
    f"CSeq: 102 INVITE\r\n"
    f"Allow: INVITE, ACK, CANCEL, OPTIONS, BYE, REFER, SUBSCRIBE, NOTIFY, INFO, PUBLISH, MESSAGE\r\n"
    f"Supported: replaces, timer\r\n"
    f"Content-Type: application/sdp\r\n"
    f"Content-Length: {len(sdp_body.encode('utf-8'))}\r\n"
    f"\r\n"
    f"{sdp_body}"
)

print(f"--- SENDING INVITE TO {EXOTEL_PROXY}:{EXOTEL_PORT} ---")
print(sip_invite)

# --- NETWORK SOCKET OPERATIONS ---
try:
    # 1. Create a TCP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5) # 5 second timeout
    
    # 2. Connect to Exotel
    sock.connect((EXOTEL_PROXY, EXOTEL_PORT))
    
    # 3. Send the INVITE
    sock.sendall(sip_invite.encode('utf-8'))
    
    # 4. Listen for Response
    print("\n--- WAITING FOR RESPONSE ---")
    while True:
        data = sock.recv(4096)
        if not data:
            break
        
        response = data.decode('utf-8')
        print(response)
        
        # LOGIC: If we receive a 200 OK, we MUST send an ACK or the call will drop
        if "SIP/2.0 200 OK" in response:
            print("\n--- CALL ANSWERED (200 OK) - SENDING ACK ---")
            
            # Extract tags needed for ACK from the response
            # (In a real app, you would parse the 'To' tag properly)
            ack_packet = (
                f"ACK sip:{TO_NUMBER}@{EXOTEL_PROXY}:{EXOTEL_PORT} SIP/2.0\r\n"
                f"Via: SIP/2.0/TCP {YOUR_PUBLIC_IP}:{YOUR_LOCAL_PORT};branch={branch_id}\r\n"
                f"Max-Forwards: 70\r\n"
                f"From: \"{FROM_NUMBER}\" <sip:{FROM_NUMBER}@exotelt.pstn.exotel.com>;tag={tag_id}\r\n"
                f"To: <sip:{TO_NUMBER}@{EXOTEL_PROXY}>;tag=REQUIRED_FROM_RESPONSE\r\n" # You must parse the actual tag here
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 102 ACK\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            # Note: ACK logic here is simplified. You need to parse the 'To' header 
            # from the 200 OK to get the remote tag.
            
        if "403 Forbidden" in response:
            print("ERROR: 403 Forbidden. Check your IP Whitelisting or Exophone.")
            break

except Exception as e:
    print(f"Connection Error: {e}")
finally:
    sock.close()