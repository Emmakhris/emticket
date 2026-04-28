FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: build tools for any C-extension wheels, curl for healthcheck,
# netcat for the DB readiness probe in entrypoint.sh
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cached layer unless requirements.txt changes)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project code
COPY . .

# Ensure scripts are executable and static dir exists
RUN chmod +x /app/scripts/*.sh \
    && mkdir -p /app/staticfiles /app/media

EXPOSE 8000
