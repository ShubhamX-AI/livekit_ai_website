# Backend - LiveKit AI Agents (FastAPI)

This backend provides the FastAPI server, LiveKit agent runtime, and SIP helpers for the LiveKit AI website demo.

## Requirements

- Python 3.12+
- LiveKit server or LiveKit Cloud account
- OpenAI Realtime API access

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in this directory:

```env
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-livekit-host.livekit.cloud
OPENAI_API_KEY=your_openai_api_key

# Optional
CARTESIA_API_KEY=your_cartesia_api_key
SIP_OUTBOUND_TRUNK_ID_TWILIO=your_trunk_id
LIVEKIT_EGRESS_URL=https://your-egress-server
PORT=8000
```

## Running locally

```bash
# Terminal 1: FastAPI server
python server_run.py

# Terminal 2: LiveKit agent runtime
python agent_session.py start
```

Server runs on `http://localhost:8000` by default.

## Available agents

Supported agents include `web`, `invoice`, `restaurant`, `bank`, `tour`, and `realestate`.

## API endpoints

- `GET /api/getToken` - LiveKit token generation
- `GET /api/makeCall` - SIP outbound call helper
- `GET /api/setInboundAgent` - Map inbound number to agent
- `GET /api/getInboundAgent` - Fetch inbound mapping
- `GET /health` - Health check

## Files to know

- `server.py` - FastAPI server and routes
- `agent_session.py` - Agent runtime and routing
- `outbound/outbound_call.py` - SIP outbound utility
- `inbound/config_manager.py` - Inbound number mapping
