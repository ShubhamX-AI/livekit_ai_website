# Exotel SIP Bridge — Implementation Plan

## Date: 2026-02-17

## Status: Ready for implementation

---

## 1. Problem Statement

When making outbound calls via Exotel, the SIP INVITE succeeds and the phone rings,
but the call is **blank** — no audio flows between the AI agent and the phone user.

### Root Cause

LiveKit's built-in SIP service handles Twilio end-to-end (signaling + media + room bridging).
Exotel requires custom SIP handling (TCP transport, specific headers, `nat=force_rport`)
that LiveKit's SIP service does not natively support. The current `sip_bridge.py` attempts
to bridge the gap but has several critical bugs preventing audio flow.

---

## 2. Identified Bugs (Ordered by Severity)

### BUG-1: Room Duplication (Critical)

- **Where:** `outbound_call.py` + `sip_bridge.py`
- **What:** `outbound_call.py` creates a room + dispatches an agent, then calls
  `run_bridge()` which creates a **second** room + dispatches a **second** agent.
  The bridge joins Room B but the original dispatch was to Room A.
- **Fix:** Pass the already-created room name to `run_bridge()`. Remove room
  creation and agent dispatch from inside `sip_bridge.py`.

### BUG-2: Event Handler Race Condition (Critical)

- **Where:** `sip_bridge.py`, line 312
- **What:** `@room.on("track_subscribed")` is registered AFTER the SIP call
  connects. If the agent publishes its audio track before the handler is set up,
  the agent's audio is never bridged to the phone → one-way or no audio.
- **Fix:** Register ALL room event handlers BEFORE connecting to LiveKit room
  and BEFORE starting the SIP call.

### BUG-3: Event Loop Reference (High)

- **Where:** `sip_bridge.py`, `RTPBridge.__init__`, line 44
- **What:** `asyncio.get_event_loop()` is called at construction time. When
  `run_bridge()` is spawned via `asyncio.create_task()` from FastAPI, the loop
  reference may not be correct. This causes `sock_recvfrom()` to silently fail.
- **Fix:** Use `asyncio.get_running_loop()` inside the async methods that need it,
  not in `__init__`.

### BUG-4: RTP Port Binding (High)

- **Where:** `sip_bridge.py`, `RTPBridge.__init__`, line 37
- **What:** Binds to `0.0.0.0:0` (random port) but the SDP in `SipClient._build_invite()`
  uses `self.rtp_bridge.port` — i.e., the random port. This part is actually correct
  in principle, BUT the SDP advertises `MEDIA_IP = "13.234.150.174"` which must match
  the actual server IP. Since the bridge runs on the same server (13.234.150.174), this
  is correct. However, we need to verify 0.0.0.0 binding on that interface actually
  receives packets from the internet.
- **Fix:** Bind explicitly to `MEDIA_IP` instead of `0.0.0.0` for reliability.

### BUG-5: Missing G.711 A-law Handling (Medium)

- **Where:** `sip_bridge.py`, `RTPBridge._read_incoming_rtp()`
- **What:** The code only decodes G.711 μ-law (`audioop.ulaw2lin`), but the SDP
  in `sip_test3.py` offers PCMA (8) as the preferred codec. If Exotel chooses PCMA,
  the audio will be decoded incorrectly.
- **Fix:** Parse the payload type from the RTP header and decode accordingly
  (PCMA vs PCMU). OR only offer PCMU in the SDP to simplify.

### BUG-6: AudioFrame Construction (Medium)

- **Where:** `sip_bridge.py`, lines 88-93
- **What:** The `rtc.AudioFrame` constructor may have a different API than assumed.
  Need to verify against the actual `livekit-agents` SDK version (1.3.x).
- **Fix:** Verify constructor args against the SDK and test with actual data.

### BUG-7: SIP Response Parsing (Medium)

- **Where:** `sip_bridge.py`, `SipClient.start_call()`, lines 206-262
- **What:** Uses `readuntil(b'\r\n')` which may not work reliably for SIP message
  parsing. SIP messages are terminated by `\r\n\r\n` for headers, and the 200 OK
  detection (`line_str.startswith("SIP/2.0 200 OK")`) should be the first line
  of the response. If a `100 Trying` or `180 Ringing` comes first, the loop
  handles it correctly by continuing. But the header parsing inside the `200 OK`
  block is fragile.
- **Fix:** Implement a more robust SIP message parser that reads the full message
  (status line + headers + body) as a unit.

---

## 3. Implementation Steps

### Step 1: Refactor `outbound_call.py` — Eliminate Room Duplication

**Goal:** The Exotel path should create ONE room, ONE agent dispatch, and pass
the room name to the bridge.

**Changes in `outbound_call.py`:**

```python
# BEFORE (current code, lines 79-94):
if call_from == "exotel":
    asyncio.create_task(run_bridge(phone_number, agent_type))
    return format_success_response(...)

# AFTER:
if call_from == "exotel":
    # Room and dispatch already created above (lines 51-73)
    # Pass the existing room name to the bridge
    asyncio.create_task(
        run_bridge(
            phone_number=phone_number,
            agent_type=agent_type,
            room_name=unique_room_name  # ← Use the room already created
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
```

**Files modified:** `outbound/outbound_call.py`

---

### Step 2: Rewrite `sip_bridge.py` — Clean Architecture

**Goal:** Rewrite with clean separation of concerns, proper error handling,
and all bugs fixed.

**Architecture of the new bridge:**

```
┌─────────────────────────────────────────────────┐
│                  run_bridge()                    │
│                                                  │
│  1. Connect to LiveKit Room as "sip-phone-user" │
│  2. Register event handlers (track_subscribed)   │
│  3. Publish local audio track (SIP → LiveKit)    │
│  4. Start SIP call to Exotel                     │
│  5. On 200 OK: start RTP bridge                  │
│  6. Bidirectional audio bridging                 │
│     • RTP (from Exotel) → decode G.711 → LiveKit│
│     • LiveKit (agent audio) → encode G.711 → RTP│
│  7. On BYE or disconnect: cleanup                │
│                                                  │
│  Classes:                                        │
│  ├── ExotelSipClient       (SIP signaling)       │
│  ├── RTPMediaBridge        (RTP ↔ LiveKit audio) │
│  └── run_bridge()          (orchestrator)        │
└─────────────────────────────────────────────────┘
```

**Key design decisions:**

1. **`run_bridge()` accepts `room_name`** — it does NOT create rooms or dispatch agents.
   It only joins the existing room as a "phone user" participant.

2. **Event handlers registered BEFORE room.connect()** — eliminates the race condition.

3. **Event loop obtained via `asyncio.get_running_loop()`** inside async methods.

4. **SDP only offers PCMU (payload type 0)** — simplifies codec handling. No ambiguity
   about which codec Exotel will use.

5. **RTP bridge binds to `MEDIA_IP`** explicitly — ensures packets arrive correctly.

6. **Robust SIP message parser** — reads complete SIP messages, handles 100/180/200/4xx/5xx.

7. **Proper cleanup** — disconnects from room and closes sockets on call end or error.

**Files modified:** `sip_bridge.py` (full rewrite)

---

### Step 3: Verify AudioFrame API Compatibility

**Goal:** Ensure the `rtc.AudioFrame` constructor works with `livekit-agents~=1.3`.

**Action:**

- Check the livekit-rtc Python SDK source for AudioFrame constructor signature
- The constructor in recent versions expects:
  ```python
  rtc.AudioFrame(
      data: bytes,
      sample_rate: int,
      num_channels: int,
      samples_per_channel: int
  )
  ```
- If the API has changed, adapt accordingly.

---

### Step 4: Handle `audioop` Deprecation

**Goal:** Ensure G.711 encoding/decoding works on Python 3.12.

**Action:**

- `audioop` is deprecated in Python 3.11 but still **available** in Python 3.12.
  It was only **removed** in Python 3.13.
- Since you're on Python 3.12, `audioop` will work but generates deprecation warnings.
- For now: suppress the warning. For future-proofing: plan migration to a pure-Python
  G.711 codec or use the `audioop-lts` package.

**Files modified:** `sip_bridge.py` (add warning suppression)

---

### Step 5: Add Environment Variable Configuration

**Goal:** Move hardcoded IPs and ports to `.env` for flexibility.

**New `.env` variables:**

```env
# Exotel SIP Bridge Configuration
EXOTEL_SIP_HOST=pstn.in1.exotel.com
EXOTEL_SIP_PORT=5070
EXOTEL_CUSTOMER_IP=13.234.150.174
EXOTEL_CUSTOMER_SIP_PORT=5061
EXOTEL_MEDIA_IP=13.234.150.174
EXOTEL_CALLER_ID=08044319240
EXOTEL_FROM_DOMAIN=lokaviveka1m.sip.exotel.com
```

**Files modified:** `.env`, `sip_bridge.py`

---

### Step 6: Add Logging and Diagnostics

**Goal:** Add detailed logging at every stage so we can diagnose issues quickly.

**Log points:**

1. `[BRIDGE] Connecting to LiveKit room: {room_name}`
2. `[BRIDGE] Connected. Publishing SIP audio track...`
3. `[BRIDGE] Audio track published. Starting SIP call to {callee}...`
4. `[SIP] Sending INVITE to {exotel_ip}:{exotel_port}`
5. `[SIP] Received {status_code} {reason}`
6. `[SIP] Call answered. Remote RTP endpoint: {ip}:{port}`
7. `[SIP] Sending ACK`
8. `[RTP] Bridge started. Listening on {bind_ip}:{bind_port}`
9. `[RTP] First packet received from {remote_ip}:{remote_port}`
10. `[RTP] Audio flowing: {packets_received} packets received, {packets_sent} sent`
11. `[BRIDGE] Agent track subscribed: {participant.identity}`
12. `[BRIDGE] Forwarding agent audio to RTP`
13. `[BRIDGE] Call ended. Cleanup complete.`

**Files modified:** `sip_bridge.py`

---

### Step 7: Update `outboundsipexotel.md` Architecture Doc

**Goal:** Update the architecture documentation to reflect the fixes.

**Files modified:** `architecture/outboundsipexotel.md`

---

## 4. File Change Summary

| File                                | Action      | Description                                                |
| ----------------------------------- | ----------- | ---------------------------------------------------------- |
| `sip_bridge.py`                     | **Rewrite** | Clean rewrite with all 7 bugs fixed                        |
| `outbound/outbound_call.py`         | **Edit**    | Pass `room_name` to bridge, remove duplicate room creation |
| `.env`                              | **Edit**    | Add Exotel SIP configuration variables                     |
| `architecture/outboundsipexotel.md` | **Edit**    | Update architecture docs                                   |

---

## 5. Testing Plan

### Test 1: Unit — SIP INVITE Construction

- Verify the generated INVITE matches Exotel's expected format
- Compare output with the working `sip_test3.py`

### Test 2: Integration — Room + Bridge Connection

- Start the LiveKit server locally
- Start the agent (`agent_session.py`)
- Call the API: `POST /api/makeCall` with `call_from=exotel`
- Verify logs show:
  - ONE room created (not two)
  - Agent dispatched to that room
  - Bridge joins the SAME room
  - SIP INVITE sent to Exotel
  - 200 OK received
  - RTP bridge active

### Test 3: End-to-End — Audio Flow

- Make a real call via the API
- Verify:
  - Phone rings and picks up
  - Agent welcome message is heard on the phone
  - Speaking into the phone is heard by the agent
  - Agent responds (bidirectional audio confirmed)

### Test 4: Cleanup

- Hang up the phone
- Verify:
  - RTP bridge stops
  - SIP session is properly terminated (BYE)
  - LiveKit room is cleaned up
  - No zombie sockets or tasks

---

## 6. Risk Assessment

| Risk                                    | Likelihood | Impact | Mitigation                                           |
| --------------------------------------- | ---------- | ------ | ---------------------------------------------------- |
| Exotel rejects modified INVITE          | Low        | High   | Keep SDP/headers identical to working `sip_test3.py` |
| AudioFrame API mismatch                 | Medium     | High   | Verify against SDK source before coding              |
| Network/firewall blocks RTP             | Low        | High   | Same server + same IP as working test                |
| `audioop` breaks on future Python       | Low        | Low    | Python 3.12 still supports it; plan migration        |
| Agent doesn't detect bridge participant | Medium     | High   | Bridge joins as regular participant, not SIP kind    |

---

## 7. Execution Order

```
Step 1  →  outbound_call.py edits (5 min)
Step 2  →  sip_bridge.py rewrite (45 min)  ← bulk of the work
Step 3  →  AudioFrame API verification (10 min)
Step 4  →  audioop handling (5 min, part of Step 2)
Step 5  →  .env configuration (5 min)
Step 6  →  Logging (part of Step 2)
Step 7  →  Documentation update (10 min)

Total estimated time: ~80 minutes
```

---

## 8. Important Note on `agent_session.py` Behavior

The agent session (`agent_session.py`) determines the agent type from the room name:

```python
room_name = ctx.room.name
agent_type = room_name.split("-")[0].lower()
```

The room name format from `outbound_call.py` is:

```
{agent_type}-outbound-{phone_number[-4:]}-{uuid}
```

So `agent_type` extraction works correctly. ✅

The agent also checks `participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP`
to determine if the participant is a SIP caller. Since our bridge joins as a
**regular WebRTC participant** (not via LiveKit's native SIP service), the participant
kind will be `PARTICIPANT_KIND_STANDARD`, **not** `PARTICIPANT_KIND_SIP`.

This means:

- The `is_sip` check on line 130 will be `False`
- The `audio_ready.wait()` on line 157 will NOT be triggered
- The welcome message will be sent **immediately** without waiting for RTP stabilization

**Fix needed in `agent_session.py`:** For bridge-originated participants, we need a
way to detect them (e.g., via participant identity containing "sip-bridge" or via
metadata) and apply the same SIP delay logic.

This will be addressed in Step 2 of the implementation by setting the bridge
participant's identity to `sip-phone-{phone_number}` and metadata to
`{"source": "exotel_bridge", "phone": phone_number}`. Then in `agent_session.py`,
we can check metadata to apply the delay.
