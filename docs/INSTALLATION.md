# Installation Guide (local development)

## Prerequisites

- Python 3.12
- A Discord application + bot token (https://discord.com/developers/applications)
- An OpenAI API key

## 1. Discord bot setup

1. Create an application at the Discord Developer Portal, add a **Bot**.
2. Under **Bot**, enable the **Server Members Intent** and **Message
   Content Intent** (GuildOS needs both).
3. Under **OAuth2 → URL Generator**, select scopes `bot` and
   `applications.commands`, and permissions `Send Messages`,
   `Use Slash Commands`, `Manage Messages`, `Embed Links`. Use the
   generated URL to invite the bot to your server.
4. Copy the bot token into `.env` as `DISCORD_BOT_TOKEN`.
5. Right-click your server icon in Discord (with Developer Mode enabled
   in Discord settings) → **Copy Server ID** → put it in `.env` as
   `DISCORD_GUILD_ID`.
6. Create (or pick) a channel for application reports, copy its ID into
   `DISCORD_APPLICATION_CHANNEL_ID`.

## 2. Environment file

```bash
cp .env.example .env
```

Fill in at minimum: `SECRET_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`,
`DISCORD_APPLICATION_CHANNEL_ID`, `OPENAI_API_KEY`.

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 3. Python environment

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Database

In development, the API creates tables automatically on startup
(`ENVIRONMENT=development` in `.env`). For anything beyond local
experimentation, use Alembic instead:

```bash
alembic upgrade head
```

## 5. Run it

Two processes, in two terminals (both from `backend/`, with the venv
active):

```bash
# Terminal 1 — the API
uvicorn app.main:app --reload

# Terminal 2 — the Discord bot
python -m app.discord_bot.bot
```

Visit `http://localhost:8000/health` to confirm the API is up. In your
Discord server, run `/apply` to test the recruitment flow end-to-end.

## 6. Running tests

```bash
cd backend
pytest
```

Tests use an isolated in-memory SQLite database and mock all OpenAI
calls — no API key or network access is required to run them.

## Troubleshooting

- **Slash commands don't show up**: Discord can take up to an hour to
  propagate *global* command syncs, but GuildOS syncs commands to your
  specific `DISCORD_GUILD_ID` on startup, which should be near-instant.
  Restart the bot and check the console log for "Synced N slash
  command(s)".
- **`/apply` modal doesn't open**: confirm the bot has the
  `applications.commands` OAuth2 scope (re-invite it if unsure).
- **AI evaluation always fails**: check `logs/errors.log` and confirm
  `OPENAI_API_KEY` is valid and has quota.
