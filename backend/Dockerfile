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


# # =============================================================================
# # STAGE 1: Builder Stage - Install all build dependencies
# # =============================================================================
# FROM python:3.11-slim AS builder

# # Install build dependencies in one layer
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     python3-dev \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /build

# # Copy and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# # =============================================================================
# # STAGE 2: Runtime Stage - Minimal Debian slim image with supervisor
# # =============================================================================
# FROM python:3.11-slim AS runtime

# # Install only runtime dependencies (no compilers needed)
# # Debian slim has better package availability than Alpine for ffmpeg/audio libs
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     ffmpeg \
#     libsndfile1 \
#     supervisor \
#     && rm -rf /var/lib/apt/lists/*

# # Create non-privileged user
# ARG UID=10001
# RUN useradd -m -s /sbin/nologin -u ${UID} appuser

# WORKDIR /home/appuser

# # Copy only installed Python packages from builder
# COPY --from=builder /install /usr/local

# # Copy application code
# COPY --chown=appuser:appuser . .

# # Copy supervisord configuration
# COPY --chown=appuser:appuser supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# # Download models as appuser
# RUN echo "Downloading models..." && \
#     python agent_session.py download-files && \
#     echo "Model download completed. Listing model files:" && \
#     find /home/appuser -name "*.onnx" -type f 2>/dev/null && \
#     ls -la /home/appuser/.cache 2>/dev/null || echo "No .cache directory found"

# # Switch to non-privileged user
# USER appuser

# # Add user's local bin to PATH
# ENV PATH="/home/appuser/.local/bin:$PATH"

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000')" || exit 1

# # Expose port
# EXPOSE 8000

# # Start supervisor to manage both processes
# CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]


# Docker build command
# docker build -t shubhamint/ai_website_backend_livekit:latest .
# Docker run command
# docker run -d -p 3011:8000 shubhamint/ai_website_backend_livekit:latest

## Livekit local
# docker run -d -p 7880:7880 -p 7881:7881 -p 7882:7882/udp -e LIVEKIT_KEYS=devkey: secret livekit/livekit-server --dev