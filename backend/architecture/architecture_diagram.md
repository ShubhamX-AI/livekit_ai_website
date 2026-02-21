# SIP Architecture Diagram

This document presents the detailed architecture and sequence flow of the custom SIP bridge (`custom_sip_reach`) that connects Exotel SIP Trunks to LiveKit Agents. It outlines how both Inbound (Exotel → LiveKit) and Outbound (LiveKit → Exotel) calls are orchestrated.

## 1. System Components

### External Actors
- **Exotel SIP Proxy**: Handles PSTN routing and SIP signaling.
- **Exotel Media Server**: Handles RTP (audio) routing.
- **Client Phone**: The physical phone initiating or receiving the call.

### Internal Components (`custom_sip_reach`)
- **`inbound_listener`**: A persistent TCP server listening on port 5061 for inbound SIP messages (`INVITE`, `OPTIONS`, `BYE`) from Exotel.
- **`inbound_bridge`**: Orchestrates new inbound calls, establishes RTP ports, and creates LiveKit agent dispatches.
- **`sip_client (ExotelSipClient)`**: Handles outbound SIP signaling over TCP to Exotel (port 5070), including digest authentication.
- **`rtp_bridge (RTPMediaBridge)`**: An `aiortc` Datagram (UDP) server that receives PCMA/PCMU audio from Exotel and forwards it to LiveKit, and vice versa.
- **`port_pool`**: Manages a range of safe UDP ports for RTP allocation (avoiding LiveKit RTC port conflicts).
- **[bridge](file:///home/shubham_halder/CODE/lvk_agents/livekit_ai_website/backend/custom_sip_reach/bridge.py#42-191)**: The orchestrator for outbound calls.

### LiveKit Ecosystem
- **LiveKit Server (SFU)**: Manages WebRTC connections.
- **LiveKit Agent (`vyom_demos`)**: Python/Rust process analyzing audio and generating TTS responses.

---

## 2. Inbound Call Flow (Exotel → LiveKit)

This sequence illustrates the flow when a user dials the Exotel number.

```mermaid
sequenceDiagram
    autonumber
    actor Phone as Client Phone
    participant Exotel as Exotel SIP/RTP
    participant Listener as inbound_listener (TCP:5061)
    participant InBridge as inbound_bridge
    participant RTP as rtp_bridge (UDP:21000+)
    participant LK_Server as LiveKit Server
    participant LK_Agent as LiveKit Agent

    %% Call Initiation
    Phone->>Exotel: Dials Number
    Exotel->>Listener: SIP INVITE (SDP, pt=8)
    Listener->>InBridge: handle_inbound_call(INVITE)
    
    %% Setup internal resources
    InBridge->>InBridge: get_agent_for_number()
    InBridge->>InBridge: port_pool.acquire() -> Port X
    InBridge->>RTP: RTPMediaBridge(bind_port=Port X)
    InBridge->>LK_Server: Create Room & Dispatch Agent
    
    %% Connect LiveKit
    InBridge->>LK_Server: connect(Room Token)
    Note over InBridge, LK_Server: Bridge connects to LiveKit Room
    InBridge->>RTP: start_inbound(room)
    
    %% Accept Call
    InBridge->>RTP: set_remote_endpoint(Exotel Media IP, Port)
    InBridge->>Listener: Write SIP 200 OK (SDP, pt=8, Port X)
    Listener->>Exotel: SIP 200 OK
    Exotel->>Phone: Call Connected (Ringing Stops)
    Exotel->>Listener: SIP ACK
    
    %% Data Flow
    Note over Exotel, LK_Agent: --- Bidirectional Audio Flow ---
    par Audio from Phone to Agent
        Phone->>Exotel: Audio
        Exotel->>RTP: PCMA RTP Packets (Port X)
        RTP->>LK_Server: RTC Audio Track (Opus)
        LK_Server->>LK_Agent: Track Subscribed
    and Audio from Agent to Phone
        LK_Agent->>LK_Server: TTS Output Track
        LK_Server->>RTP: Track Data
        RTP->>RTP: _forward_audio()
        RTP->>Exotel: PCMA RTP Packets
        Exotel->>Phone: Audio Playback
    end
    
    %% Call Data Event
    InBridge->>LK_Server: publish_data("call_answered")
    LK_Server->>LK_Agent: event: call_answered

    %% Call Termination
    Note over Phone, LK_Agent: --- Call Disconnection ---
    Phone->>Exotel: Hangs up
    Exotel->>Listener: SIP BYE
    Listener->>InBridge: register_call_id().set() (Event Triggered)
    Listener->>Exotel: SIP 200 OK (BYE)
    
    %% Teardown
    InBridge->>RTP: rtp_bridge.stop()
    InBridge->>LK_Server: room.disconnect()
    InBridge->>InBridge: port_pool.release(Port X)
```

---

## 3. Outbound Call Flow (LiveKit → Exotel)

This sequence illustrates the flow when the system dials out to a user.

```mermaid
sequenceDiagram
    autonumber
    participant System as Outbound Trigger (API)
    participant Bridge as bridge.py
    participant RTP as rtp_bridge (UDP:21000+)
    participant SIP as sip_client (TCP:5070)
    participant LK_Server as LiveKit Server
    participant Exotel as Exotel SIP/RTP
    actor Phone as Client Phone

    %% Call Initiation
    System->>Bridge: run_bridge(phone="+91...")
    Bridge->>Bridge: port_pool.acquire() -> Port Y
    Bridge->>RTP: RTPMediaBridge(bind_port=Port Y)
    Bridge->>SIP: ExotelSipClient(callee, rtp_port=Port Y)
    
    %% Connect LiveKit First
    Bridge->>LK_Server: connect(Room Token)
    Bridge->>RTP: start_inbound(room)
    
    %% SIP Signaling & Auth
    Bridge->>SIP: connect() (TCP to Exotel)
    Bridge->>SIP: send_invite()
    SIP->>Exotel: SIP INVITE (SDP)
    
    alt Exotel challenges auth
        Exotel->>SIP: SIP 401/407 Unauthorized
        SIP->>Exotel: SIP ACK
        SIP->>SIP: calculate_digest_auth()
        SIP->>Exotel: SIP INVITE (With Auth Header)
    end
    
    Exotel->>Phone: Rings Phone
    Exotel->>SIP: SIP 180 Ringing / 183 Session Progress
    
    %% Call Connected
    Phone->>Exotel: Answers Phone
    Exotel->>SIP: SIP 200 OK (SDP, pt=8, Contact, Record-Route)
    SIP->>SIP: Extract Remote IP, Port, Route, Contact
    SIP->>Exotel: SIP ACK (With Route & Contact URI)
    SIP->>Bridge: Return res (remote_ip, remote_port)
    
    Bridge->>RTP: set_remote_endpoint(remote_ip, remote_port)
    
    %% Data Flow
    Note over LK_Server, Phone: --- Bidirectional Audio Flow ---
    par Audio from Agent to Phone
        LK_Server->>RTP: Agent Track Subscribed
        RTP->>Exotel: PCMA RTP Packets
        Exotel->>Phone: Audio Playback
    and Audio from Phone to Agent
        Phone->>Exotel: Audio
        Exotel->>RTP: PCMA RTP Packets (Port Y)
        RTP->>LK_Server: RTC Audio Track
    end

    %% Call Data Event
    Bridge->>LK_Server: publish_data("call_answered")
    
    %% Call Termination (Agent Hangs up)
    Note over LK_Server, Phone: --- Call Disconnection (Agent Initiated) ---
    LK_Server->>Bridge: Room Disconnected (Agent left)
    Bridge->>SIP: send_bye()
    SIP->>Exotel: SIP BYE (With Route & Contact URI)
    Exotel->>SIP: SIP 200 OK (BYE)
    
    %% Teardown
    Bridge->>RTP: rtp_bridge.stop()
    Bridge->>SIP: close() TCP connection
    Bridge->>Bridge: port_pool.release(Port Y)
```

## 4. Disconnection Strategies
The system implements robust fallback logic for call disconnection since SIP can be unreliable over WAN:

1. **SIP `BYE`**: Primary mechanism. The system watches the `inbound_listener` and the active outbound TCP socket.
2. **RTP Silence Threshold**: If `seconds_since_rx()` exceeds `RTP_SILENCE_TIMEOUT_SECONDS` (default: 30s) after audio has started flowing, the caller is assumed to be disconnected.
3. **No RTP After Answer**: If the call is answered but zero RTP packets arrive within `NO_RTP_AFTER_ANSWER_SECONDS` (default: 60s), the call is terminated.
4. **LiveKit Disconnect**: If the agent terminates the room from the WebRTC side, the bridge issues a SIP `BYE` and frees resources.
