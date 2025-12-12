# # Stage 1: Build dependencies
# FROM python:3.11-slim AS builder
# WORKDIR /app
# RUN apt-get update && apt-get install -y build-essential
# RUN apt-get update && apt-get install -y ca-certificates
# COPY requirements.txt .
# RUN pip install --user -r requirements.txt

# # Stage 2: Production
# FROM python:3.11-slim
# WORKDIR /app

# RUN apt-get update && apt-get install -y ca-certificates
# RUN update-ca-certificates

# COPY . .
# COPY --from=builder /root/.local /root/.local
# ENV PATH=/root/.local/bin:$PATH

# EXPOSE 8000
# RUN pip install --no-cache-dir --user uv

# # Copy entrypoint script
# COPY entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh

# CMD ["/entrypoint.sh"]

# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (Crucial for logs)
ENV PYTHONUNBUFFERED=1
# Prevent Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (gcc, python3-dev are often needed for audio/webrtc libs)
# We also install 'supervisor' to manage running two scripts at once.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    build-essential \
    supervisor \
    ca-certificates \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Set working directory
WORKDIR /home/appuser

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies directly as the appuser
# (No need for multi-stage complexity here unless your builds are huge. 
#  Direct install ensures all shared libs connect correctly.)
USER appuser
RUN pip install --user --no-cache-dir -r requirements.txt

# Add user's local bin to PATH so we can run installed scripts
ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Download models at build time
RUN python agent_session.py download-files

# Copy the supervisord configuration file
COPY --chown=appuser:appuser supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port your server_run.py uses
EXPOSE 8000

# Start Supervisor (which will start your two python scripts)
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]


# Docker build command
# docker build -t shubhamint/ai_website_backend_livekit:latest .
# Docker run command
# docker run -d -p 3011:8000 shubhamint/ai_website_backend_livekit:latest