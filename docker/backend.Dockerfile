# GuildOS backend + bot image.
# The same image is used for both the `api` and `bot` services in
# docker-compose.yml — they just run different commands (see compose file).
FROM python:3.12-slim

WORKDIR /app

# System deps needed for building some Python packages (e.g. asyncpg, bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Directories for SQLite data and rotating logs (mounted as volumes in compose)
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
