# Backend image: packages the FastAPI app with its Python runtime + deps.

# Start from a slim official Python image (small, no build cruft).
FROM python:3.14-slim

# Don't buffer stdout/stderr (so logs appear immediately) and don't write .pyc.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies FIRST and as their own layer. Docker caches layers, so as
# long as requirements.txt doesn't change, rebuilds skip re-installing deps.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code.
COPY src ./src

EXPOSE 8000

# Run the ASGI server, listening on all interfaces inside the container.
#   ${PORT:-8000} uses the platform-provided port (Railway sets PORT) and falls
#   back to 8000 locally. Shell form is used so the variable expands.
#   --proxy-headers + --forwarded-allow-ips make uvicorn trust X-Forwarded-For
#   from the reverse proxy, so rate limiting sees the real client IP.
CMD uvicorn src.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'
