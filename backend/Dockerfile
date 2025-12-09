# Stage 1: Build dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential
RUN apt-get update && apt-get install -y ca-certificates
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates
RUN update-ca-certificates

COPY . .
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000
RUN pip install --no-cache-dir --user uv

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]


# Docker build command
# docker build -t shubhamint/ai_website_backend:latest .
# Docker run command
# docker run -d -p 8000:8000 --name ai_website_backend shubhamint/ai_website_backend:latest