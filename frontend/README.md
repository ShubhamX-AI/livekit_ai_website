# Frontend - LiveKit AI Website (React + Vite)

React + TypeScript frontend that connects to the LiveKit AI backend and exposes agent-specific experiences.

## Requirements

- Node.js 18+
- Backend running (see `backend/README.md`)

## Setup

```bash
npm install
```

Create a `.env` file in this directory:

```env
VITE_LIVEKIT_URL=wss://your-livekit-host.livekit.cloud
VITE_BACKEND_URL=http://localhost:8000
```

## Running locally

```bash
npm run dev
```

Dev server runs on `http://localhost:5173`.

## Routes

Core agent routes are defined in `src/App.tsx`:

- `/` - Home/agent selection
- `/web` - Web agent experience
- `/invoice` - Invoice assistant
- `/restaurant` - Restaurant agent
- `/bank` - Banking agent
- `/tour` - Tour agent
- `/realestate` - Real estate agent

## Build

```bash
npm run build
```

Static output is emitted to `dist/`.
