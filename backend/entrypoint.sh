#!/bin/bash

export PYTHONHTTPSVERIFY=0

echo "📥 Downloading required weights/files..."
python agent_session.py download-files

echo "🚀 Starting application services..."

# Start server_run in background
python server_run.py &

# Start the agent session (foreground so container stays alive)
python agent_session.py start
