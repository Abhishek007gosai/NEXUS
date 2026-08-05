# ================================================
# NEXUS-ECCHI — File Store + Anime Index Mini App
# Supports: Heroku · Render · VPS · Local · Koyeb
# ================================================

FROM python:3.11-slim-bullseye

LABEL maintainer="botifyx-bots"
LABEL description="NEXUS-ECCHI — File Store + EcchiDex Anime Index"
LABEL version="3.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=10000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev curl git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || curl -f http://localhost:${PORT:-10000}/ || exit 1

CMD ["python", "main.py"]
