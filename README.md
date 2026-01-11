# LiveKit AI Website Bots

A real-time, multi-agent voice AI system built with LiveKit, OpenAI Realtime API, and React. This application enables natural voice conversations with specialized AI agents for different business domains.

## 🎯 Overview

This project provides an interactive voice interface where users can speak with AI agents specialized in different domains:

- **Web Agent** - Website information and general queries
- **Invoice Agent** - Invoice processing and billing assistance
- **Restaurant Agent** - Restaurant reservations and menu queries
- **Banking Agent** - Banking services and account management
- **Tour Agent** - Travel planning and tour information

Each agent uses OpenAI's Realtime API for natural, low-latency voice conversations with background audio and noise cancellation.

## 🏗️ Architecture

### Backend (Python/FastAPI)

- **FastAPI Server** (`server.py`) - Token generation and room management
- **LiveKit Agent** (`agent_session.py`) - Voice AI agent orchestration
- **Web Scraper** (`scrape.py`) - Website content extraction for RAG
- **Vector Database** - ChromaDB for knowledge storage
- **Specialized Agents** - Domain-specific AI assistants in `agents/` directory

### Frontend (React/TypeScript)

- **React + Vite** - Modern frontend framework
- **LiveKit Components** - Real-time audio/video components
- **TypeScript** - Type-safe development

### Infrastructure

- **LiveKit Server** - WebRTC SFU for real-time communication
- **Docker Compose** - Containerized deployment
- **Nginx** - Frontend web server (production)

## 📋 Prerequisites

- **Python 3.12+** (backend)
- **Node.js 18+** (frontend)
- **Docker & Docker Compose** (for containerized deployment)
- **LiveKit Cloud Account** or self-hosted LiveKit server
- **OpenAI API Key** (for Realtime API access)

## 🚀 Quick Start

### Option 1: Local Development Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/shubhamINT/livekit_ai_website.git
cd livekit_ai_website
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies (using pip)
pip install -r requirements.txt

# OR using uv (faster)
uv pip install -r requirements.txt
```

#### 3. Configure Backend Environment

Create a `.env` file in the `backend/` directory:

```env
# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-livekit-host.livekit.cloud

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Optional: Cartesia TTS (if not using default inference)
CARTESIA_API_KEY=your_cartesia_api_key
```

#### 4. Download Required Files (if applicable)

```bash
python agent_session.py download-files
```

#### 5. Start Backend Services

**Terminal 1** - Start FastAPI server:

```bash
python server_run.py
```

Server will run on `http://localhost:8000`

**Terminal 2** - Start LiveKit agent:

```bash
python agent_session.py start
```

#### 6. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

#### 7. Configure Frontend Environment

Create a `.env` file in the `frontend/` directory:

```env
VITE_LIVEKIT_URL=wss://your-livekit-host.livekit.cloud
VITE_BACKEND_URL=http://localhost:8000
```

#### 8. Start Frontend Development Server

```bash
npm run dev
```

Frontend will run on `http://localhost:5173`

### Option 2: Docker Deployment

#### 1. Configure Environment Variables

Set up `.env` files in both `backend/` and `frontend/` directories as shown above.

#### 2. Build and Run with Docker Compose

```bash
# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f

# Stop services
docker compose down
```

**Services:**

- Backend: `http://localhost:3011`
- Frontend: `http://localhost:3010`

#### 3. Deploy Script (Production)

For production deployments with health checks:

```bash
chmod +x depoly.sh
./depoly.sh
```

This script:

- Pulls latest code
- Builds backend with health check wait
- Builds frontend after backend is healthy
- Cleans up unused Docker resources

## 🔧 Configuration Details

### Backend Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `LIVEKIT_API_KEY` | LiveKit API key | Yes |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes |
| `LIVEKIT_URL` | LiveKit WebSocket URL | Yes |
| `OPENAI_API_KEY` | OpenAI API key for Realtime API | Yes |
| `CARTESIA_API_KEY` | Cartesia TTS API key | Optional |

### Frontend Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_LIVEKIT_URL` | LiveKit WebSocket URL (same as backend) | Yes |
| `VITE_BACKEND_URL` | Backend API URL | Yes |

### Available Agents

The system supports 5 specialized agents. Specify the agent type when connecting:

```javascript
// Frontend example
const metadata = { agent: "web" }; // web, invoice, restaurant, bank, tour
```

## 📚 Usage

### Accessing the Application

1. Open `http://localhost:5173` (development) or `http://localhost:3010` (Docker)
2. Select your desired agent type
3. Allow microphone permissions
4. Start speaking with the AI agent

### Web Scraping for Knowledge Base

To add website content to the vector database:

```bash
cd backend
python scrape.py
```

Edit `scrape.py` to add your URLs:

```python
my_urls = [
    "https://example.com/",
    "https://example.com/about/",
]
```

## 🔍 API Endpoints

### Backend API

- `GET /api/getToken` - Generate LiveKit access token
  - Query params: `name` (participant name), `agent` (agent type), `room` (optional)
  
- `GET /api/checkPassword` - Password verification
  - Query param: `password`
  
- `GET /health` - Health check endpoint

## 🛠️ Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test
```

### Building for Production

```bash
# Frontend
cd frontend
npm run build

# Output in frontend/dist
```

## ⚠️ Important Notes

1. **Agent Selection Timing**: Agent selection MUST happen after the room is connected and a participant has joined. The system uses participant metadata to determine which agent to load.

2. **LiveKit Server**: You need a LiveKit server running. Options:
   - Use LiveKit Cloud (easiest)
   - Run local LiveKit server with Docker:

   ```bash
   docker pull livekit/livekit-server
   docker run -d --name livekit-server \
     -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
     -e LIVEKIT_KEYS="devkey: secret" \
     livekit/livekit-server --dev --bind 0.0.0.0 --node-ip 127.0.0.1
   ```

3. **Python Version**: Requires Python 3.12+ due to dependencies

4. **SSL Certificates**: The project includes `pip-system-certs` for handling self-signed certificates

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Import errors or module not found

```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

**Problem**: LiveKit connection failed

- Verify `LIVEKIT_URL` is correct (should start with `wss://`)
- Check API key and secret are valid
- Ensure LiveKit server is running and accessible

**Problem**: OpenAI API errors

- Verify `OPENAI_API_KEY` is valid
- Check you have access to Realtime API (may require waitlist approval)
- Monitor OpenAI API usage limits

### Frontend Issues

**Problem**: Connection timeout

- Verify backend is running (`http://localhost:8000/health`)
- Check `VITE_BACKEND_URL` in `.env`
- Ensure CORS is properly configured

**Problem**: Microphone not working

- Grant browser microphone permissions
- Check browser console for errors
- Test microphone in browser settings

### Docker Issues

**Problem**: Backend health check failing

```bash
# Check backend logs
docker compose logs backend

# Restart services
docker compose restart backend
```

**Problem**: Port conflicts

- Ensure ports 3010, 3011 are not in use
- Modify ports in `docker-compose.yml` if needed

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Support

For issues and questions:

- Create an issue on GitHub
- Contact: [Add contact information]
