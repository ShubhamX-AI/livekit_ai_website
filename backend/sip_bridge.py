import asyncio
import logging
import socket
import uuid
import random
import os
import audioop
import struct
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import LiveKitAPI, CreateRoomRequest, CreateAgentDispatchRequest, AccessToken, VideoGrants

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sip_bridge")
load_dotenv(override=True)

# Configuration
EXOTEL_IP = "pstn.in1.exotel.com"
EXOTEL_PORT = 5070
CUSTOMER_IP = "13.234.150.174"  # Start with the IP that worked in test, but ideally should be local IP if NAT traversal needed
CUSTOMER_PORT = 5061
MEDIA_IP = "13.234.150.174"     # Same note as above
RTP_PORT = 18232                # Port we listen on
CALLER_ID = "08044319240"       # Exophone
FROM_DOMAIN = "lokaviveka1m.sip.exotel.com"

# LiveKit Config
LK_URL = os.getenv("LIVEKIT_URL")
LK_API_KEY = os.getenv("LIVEKIT_API_KEY")
LK_API_SECRET = os.getenv("LIVEKIT_API_SECRET")


class RTPBridge:
    def __init__(self, local_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))  # Bind to any available port
        self.port = self.sock.getsockname()[1]
        logger.info(f"RTP Bridge bound to local port: {self.port}")
        self.sock.setblocking(False)
        self.remote_addr = None
        self.running = False
        self.audio_source = None  # LiveKit AudioSource
        self.loop = asyncio.get_event_loop()

    def set_remote_address(self, ip, port):
        self.remote_addr = (ip, port)
        logger.info(f"RTP Remote set to: {self.remote_addr}")

    async def start(self, room: rtc.Room):
        self.running = True
        # Create a source for the microphone (audio FROM SIP -> TO LiveKit)
        self.audio_source = rtc.AudioSource(48000, 1)
        track = rtc.LocalAudioTrack.create_audio_track("sip_mic", self.audio_source)
        await room.local_participant.publish_track(track)
        
        asyncio.create_task(self._read_incoming_rtp())
    
    async def _read_incoming_rtp(self):
        """Reads UDP packets from SIP, decodes G.711, sends to LiveKit."""
        logger.info("Starting RTP listener...")
        while self.running:
            try:
                data, addr = await self.loop.sock_recvfrom(self.sock, 4096)
                # Basic RTP parsing
                if len(data) > 12:
                    # header = data[:12]
                    payload = data[12:]
                    
                    # G.711 u-law to PCM (16-bit linear)
                    # LiveKit expects 16-bit PCM at 48kHz (usually)
                    # G.711 is 8kHz. We need to decode and resample.
                    
                    pcm_8k = audioop.ulaw2lin(payload, 2)
                    
                    # Simple resampling 8k -> 48k (6x)
                    # ratecv(fragment, width, nchannels, inrate, outrate, state[, weightA[, weightB]])
                    pcm_48k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 48000, None)
                    
                    # Capture frame to LiveKit source
                    # AudioSource.capture_frame expects an AudioFrame or bytes? 
                    # Checking Python SDK, capture_frame(frame: AudioFrame)
                    # We need to construct an AudioFrame. 
                    # For now simplicity, assuming we can figure this out or use a simpler method.
                    # Actually, rtc.AudioSource.capture_frame takes an AudioFrame.
                    # We need to create an AudioFrame from raw bytes.
                    
                    frame = rtc.AudioFrame(
                        data=pcm_48k,
                        sample_rate=48000,
                        num_channels=1,
                        samples_per_channel=len(pcm_48k) // 2
                    )
                    await self.audio_source.capture_frame(frame)
                    
            except Exception as e:
                pass
                # logger.error(f"RTP Read Error: {e}")
            
            await asyncio.sleep(0.001)

    async def send_audio(self, frame: rtc.AudioFrame):
        """Receives AudioFrame from LiveKit, encodes to G.711, sends via UDP to SIP."""
        if not self.remote_addr:
            return

        try:
            # Resample 48k (or whatever) -> 8k
            data_in = frame.data.tobytes()
            
            # Resample 48k -> 8k
            # state is None for now (stateless resampling for simplicity, might click)
            # audioop.ratecv returns (new_fragment, new_state)
            pcm_8k, _ = audioop.ratecv(data_in, 2, 1, frame.sample_rate, 8000, None)
            
            # Encode Linear to G.711 u-law
            ulaw_payload = audioop.lin2ulaw(pcm_8k, 2)
            
            # RTP Header Construction
            # V=2 (10), P=0, X=0, CC=0 -> 0x80
            # M=0, PT=0 (PCMU) -> 0x00
            # Seq (16 bit), TS (32 bit), SSRC (32 bit)
            
            if not hasattr(self, 'seq'): self.seq = 0
            if not hasattr(self, 'ts'): self.ts = 0
            if not hasattr(self, 'ssrc'): self.ssrc = random.randint(0, 0xFFFFFFFF)
            
            self.seq = (self.seq + 1) & 0xFFFF
            self.ts = (self.ts + len(pcm_8k)//2) & 0xFFFFFFFF # 1 sample = 1 tick for 8k audio? No, 8000Hz clock.
            
            header = struct.pack('!BBHII', 0x80, 0x00, self.seq, self.ts, self.ssrc)
            
            packet = header + ulaw_payload
            self.sock.sendto(packet, self.remote_addr)
            
        except Exception as e:
            logger.error(f"RTP Send Error: {e}")


class SipClient:
    def __init__(self, callee):
        self.callee = callee
        self.branch = f"z9hG4bK-{uuid.uuid4().hex}"
        self.tag = f"trunk{random.randint(10000, 99999)}"
        self.call_id = str(uuid.uuid4())
        self.rtp_bridge = RTPBridge(0) # Port assigned dynamically

    def _build_invite(self):
        sdp = f"""v=0
o=- {random.randint(1000000000, 2000000000)} {random.randint(1000000000, 2000000000)} IN IP4 {MEDIA_IP}
s=-
c=IN IP4 {MEDIA_IP}
t=0 0
m=audio {self.rtp_bridge.port} RTP/AVP 0 101
a=rtpmap:0 PCMU/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-15
a=ptime:20
a=sendrecv
"""
        content_length = len(sdp.encode())
        
        invite = f"""INVITE sip:{self.callee}@{EXOTEL_IP}:{EXOTEL_PORT} SIP/2.0
Via: SIP/2.0/TCP {CUSTOMER_IP}:{CUSTOMER_PORT};branch={self.branch};rport
Max-Forwards: 70
From: "{CALLER_ID}" <sip:{CALLER_ID}@{FROM_DOMAIN}>;tag={self.tag}
To: <sip:{self.callee}@{EXOTEL_IP}:{EXOTEL_PORT}>
Call-ID: {self.call_id}
CSeq: 1 INVITE
Contact: <sip:+91{CALLER_ID}@{CUSTOMER_IP}:{CUSTOMER_PORT};transport=tcp>
Supported: 100rel, timer
Allow: INVITE, ACK, CANCEL, BYE, OPTIONS, UPDATE
Content-Type: application/sdp
Content-Length: {content_length}

{sdp}"""
        return invite.encode()

    def _build_ack(self, to_tag):
        ack = f"""ACK sip:{self.callee}@{EXOTEL_IP}:{EXOTEL_PORT} SIP/2.0
Via: SIP/2.0/TCP {CUSTOMER_IP}:{CUSTOMER_PORT};branch={self.branch};rport
Max-Forwards: 70
From: "{CALLER_ID}" <sip:{CALLER_ID}@{FROM_DOMAIN}>;tag={self.tag}
To: <sip:{self.callee}@{EXOTEL_IP}:{EXOTEL_PORT}>;tag={to_tag}
Call-ID: {self.call_id}
CSeq: 1 ACK
Content-Length: 0
"""
        return ack.encode()

    async def start_call(self):
        logger.info(f"Starting SIP Call to {self.callee}")
        
        # Open TCP connection
        reader, writer = await asyncio.open_connection(EXOTEL_IP, EXOTEL_PORT)
        
        # Send INVITE
        invite = self._build_invite()
        logger.info("Sending INVITE...")
        writer.write(invite)
        await writer.drain()
        
        to_tag = None
        
        # Read loop
        while True:
            line = await reader.readuntil(b'\r\n')
            line_str = line.decode().strip()
            logger.info(f"SIP RX: {line_str}")
            
            if line_str.startswith("SIP/2.0 200 OK"):
                logger.info("Call Answered (200 OK)")
                
                # We need to extract the To tag and SDP from the response to know where to send audio
                # This is a simplified parser
                
                # Read headers
                headers = {}
                while True:
                    h_line = await reader.readuntil(b'\r\n')
                    h_str = h_line.decode().strip()
                    if not h_str: break
                    if ":" in h_str:
                        k, v = h_str.split(":", 1)
                        headers[k.strip().lower()] = v.strip()
                
                # Read Body (SDP)
                cl = int(headers.get("content-length", 0))
                sdp_bytes = await reader.readexactly(cl)
                sdp = sdp_bytes.decode()
                logger.info(f"Remote SDP: {sdp}")
                
                # Parse SDP for IP/Port (simple regex or string find)
                remote_ip = None
                remote_port = 0
                
                for s_line in sdp.splitlines():
                    if s_line.startswith("c=IN IP4"):
                        remote_ip = s_line.split(" ")[-1]
                    if s_line.startswith("m=audio"):
                        parts = s_line.split(" ")
                        remote_port = int(parts[1])
                
                if remote_ip and remote_port:
                    self.rtp_bridge.set_remote_address(remote_ip, remote_port)
                
                # Extract To Tag
                to_header = headers.get("to", "")
                if "tag=" in to_header:
                    to_tag = to_header.split("tag=")[1].split(";")[0]
                
                # Send ACK
                ack = self._build_ack(to_tag)
                logger.info("Sending ACK...")
                writer.write(ack)
                await writer.drain()
                
                return True # Call established

            if line_str.startswith("SIP/2.0 4") or line_str.startswith("SIP/2.0 5"):
                 logger.error(f"Call failed: {line_str}")
                 return False


async def stream_audio_to_sip(audio_stream: rtc.AudioStream, client: SipClient):
    async for event in audio_stream:
        # event is AudioFrame
        await client.rtp_bridge.send_audio(event)

async def run_bridge(phone_number, agent_type="invoice"):
    # 1. Setup LiveKit Room
    room_name = f"sip-bridge-{phone_number}-{uuid.uuid4().hex[:6]}"
    logger.info(f"Connecting to LiveKit Room: {room_name}")
    
    room = rtc.Room()
    token = (
        AccessToken(LK_API_KEY, LK_API_SECRET)
        .with_identity("sip-bridge-user")
        .with_name("Phone User")
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )
    
    await room.connect(LK_URL, token)
    logger.info("Connected to LiveKit")
    
    # 2. Dispatch Agent
    logger.info(f"Dispatching Agent {agent_type}...")
    api = LiveKitAPI(LK_URL, LK_API_KEY, LK_API_SECRET)
    await api.agent_dispatch.create_dispatch(
        CreateAgentDispatchRequest(
            room=room_name,
            agent_name="vyom_demos",
            metadata=f'{{"agent": "{agent_type}", "phone": "{phone_number}"}}'
        )
    )
    await api.aclose()
    
    # 3. Start SIP Call & Bridge
    client = SipClient(phone_number)
    
    # Start RTP listener
    await client.rtp_bridge.start(room)
    
    # Start Signaling
    connected = await client.start_call()
    
    if connected:
        logger.info("Bridge Active. Press Ctrl+C to stop.")
        
        # Subscribe to Agent Audio
        @room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(f"Subscribed to Agent Audio: {participant.identity}")
                audio_stream = rtc.AudioStream(track)
                asyncio.create_task(stream_audio_to_sip(audio_stream, client))

        # Keep alive
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    PHONE = "08697421450"
    try:
        asyncio.run(run_bridge(PHONE))
    except KeyboardInterrupt:
        pass
