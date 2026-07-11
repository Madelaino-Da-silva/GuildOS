# Docker Guide (Proxmox deployment)

GuildOS is designed to run 24/7 via Docker Compose — a good fit for a
Proxmox VM or LXC container with Docker installed.

## 1. Prepare the host

On your Proxmox VM/container (Debian/Ubuntu example):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# log out and back in for the group change to apply
```

## 2. Get the project onto the server

```bash
git clone <your-repo-url> guildos
cd guildos
cp .env.example .env
nano .env   # fill in real values, see docs/INSTALLATION.md step 1-2
```

Set `ENVIRONMENT=production` in `.env` for the deployed server — this
disables the "auto-create tables" convenience path in `main.py` in favor
of explicit Alembic migrations, which is what you want for anything
persistent.

## 3. Run the initial migration

```bash
docker compose run --rm api alembic upgrade head
```

## 4. Start everything

```bash
docker compose up -d --build
```

This starts:

- `guildos-api` — the FastAPI backend on port `8000`
- `guildos-bot` — the Discord bot (no exposed port; it connects out to Discord)

Both share the same named volumes (`guildos-data` for the SQLite file,
`guildos-logs` for rotating log files), so both processes see the same
data.

## 5. Confirm it's healthy

```bash
docker compose ps
curl http://localhost:8000/health
docker compose logs -f bot   # watch for "GuildOS bot logged in as ..."
```

## 6. Updating

```bash
git pull
docker compose run --rm api alembic upgrade head   # if there are new migrations
docker compose up -d --build
```

## 7. Backups

The SQLite database lives inside the `guildos-data` volume at
`/app/data/guildos.db`. Back it up with:

```bash
docker run --rm -v guildos_guildos-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/guildos-data-backup.tar.gz -C /data .
```

Run this on a cron schedule if you're staying on SQLite long-term; if
you migrate to PostgreSQL (see `docs/ARCHITECTURE.md`), use
`pg_dump` instead.

## 8. Migrating to PostgreSQL later

Add a `postgres` service to `docker-compose.yml`:

```yaml
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: guildos
      POSTGRES_PASSWORD: <choose-a-real-password>
      POSTGRES_DB: guildos
    volumes:
      - guildos-postgres-data:/var/lib/postgresql/data
```

Then update `.env`:

```
DATABASE_URL=postgresql+asyncpg://guildos:<password>@postgres:5432/guildos
```

And run `docker compose run --rm api alembic upgrade head` again — no
application code changes needed.

## Reverse proxy / HTTPS (optional, for exposing the dashboard later)

Once the React dashboard is built, put a reverse proxy (Caddy, Traefik,
or nginx) in front of ports `8000` (API) and the dashboard's port,
terminating TLS there, rather than exposing them directly. This isn't
needed yet since only the Discord bot and internal API are running.
