FROM python:3.12-slim

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
    curl \
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

# Add user's local bin to PATH so we can run installed scripts
ENV PATH="/home/appuser/.local/bin:$PATH"

RUN pip install --user --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Download models at build time
RUN python agent_session.py download-files

# Copy the supervisord configuration file
COPY --chown=appuser:appuser supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port your server_run.py uses
EXPOSE 8000

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Start Supervisor (which will start your two python scripts)
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]





# # Docker file with uv implementaion
# # syntax=docker/dockerfile:1
# FROM python:3.12-slim

# # Prevent Python from buffering stdout/stderr (important for logs)
# ENV PYTHONUNBUFFERED=1

# # Prevent Python from writing .pyc files
# ENV PYTHONDONTWRITEBYTECODE=1

# # # 1. Point Python's SSL module to the System Certificate Store
# # ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
# # # 2. Point Requests/Certifi based libraries to the System Certificate Store
# # ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# # Install system dependencies required for audio / webrtc / native builds
# # supervisor is used to run multiple processes
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     python3-dev \
#     build-essential \
#     supervisor \
#     ca-certificates \
#     ffmpeg \
#     libsndfile1 \
#     curl \
#     && update-ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

# # Create a non-root user
# ARG UID=10001
# RUN adduser \
#     --disabled-password \
#     --gecos "" \
#     --home "/home/appuser" \
#     --shell "/sbin/nologin" \
#     --uid "${UID}" \
#     appuser

# # Set working directory
# WORKDIR /home/appuser

# # --------------------------------------------------------------------
# # Install uv (as root)
# # --------------------------------------------------------------------
# USER root
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# # Switch back to non-root user
# USER appuser

# # Ensure uv-created virtualenv binaries are visible
# ENV PATH="/home/appuser/.venv/bin:$PATH"

# # --------------------------------------------------------------------
# # Copy dependency definition files first (for Docker cache efficiency)
# # --------------------------------------------------------------------
# COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# # # Install Python dependencies using uv
# # # --no-dev   → skip development dependencies
# # # --frozen   → enforce uv.lock, do not modify it
# # RUN uv sync --no-dev --frozen

# # 1. Export the lockfile to a standard requirements.txt
# # 2. Install into SYSTEM python (skipping venv creation)
# #    We do this as ROOT so it goes into /usr/local/lib/...
# RUN uv export --frozen --no-dev --format requirements-txt > requirements.txt && \
#     uv pip install --system --no-cache -r requirements.txt

# # --------------------------------------------------------------------
# # Copy application code
# # --------------------------------------------------------------------
# COPY --chown=appuser:appuser . .

# # Download models at build time
# RUN uv run agent_session.py download-files

# # Expose application port
# EXPOSE 8000

# # Healthcheck
# HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# # Start supervisor
# CMD ["supervisord", "-c", "/home/appuser/supervisord.conf"]



# Docker build command
# docker build -t shubhamint/ai_website_backend_livekit:latest .
# Docker run command
# docker run -d -p 3011:8000 shubhamint/ai_website_backend_livekit:latest

## Livekit local
# docker run -d -p 7880:7880 -p 7881:7881 -p 7882:7882/udp -e LIVEKIT_KEYS=devkey: secret livekit/livekit-server --dev

# docker compose -f docker-compose.yml up -d