# GuildOS

AI-powered management system for the **Outsiders** Minecraft guild (BendersMC).

GuildOS automates the repetitive administrative work of running a guild —
reviewing applications, tracking activity, planning events, spotting
moderation issues — while leaving every real decision to human staff. The
AI never bans, accepts, declines, or promotes anyone on its own. It only
produces recommendations, scores, and reports for a person to act on.

## Project status

This is being built one complete, working feature at a time rather than
scaffolded all at once with placeholders. Current status:

| Feature | Status |
|---|---|
| Core architecture (config, DB, logging, security) | ✅ Done |
| AI Recruitment Officer (`/apply`, scoring, staff review) | ✅ Done |
| AI Community Manager (daily reports) | ⏳ Not yet built |
| AI Event Planner | ⏳ Not yet built |
| AI Staff Assistant (nightly summary) | ⏳ Not yet built |
| AI Moderator Assistant | ⏳ Not yet built |
| AI Promotion Assistant | ⏳ Not yet built |
| Scheduler / automation | ⏳ Not yet built |
| React dashboard | ⏳ Not yet built |
| JWT auth for dashboard | ⏳ Not yet built (routes have TODO markers) |
| PostgreSQL migration guide | ✅ Path documented, SQLite is default |

See `docs/ROADMAP.md` for the build order and `docs/ARCHITECTURE.md` for
how the pieces fit together.

## What's implemented right now

**AI Recruitment Officer** — the full vertical slice:

- `/apply` Discord slash command opens a multi-step modal form (Discord
  limits modals to 5 fields, so longer question sets are split across
  sequential modals with a Continue button).
- On submission, the applicant + answers are persisted, then sent to the
  AI for evaluation across 7 dimensions (activity, maturity, communication,
  teamwork, honesty, toxicity risk, long-term potential), an overall
  0-100 score, a written explanation, positives, concerns, and a
  recommendation (accept / interview / decline).
- A formatted report is posted to a configurable staff channel and
  optionally DMed to the guild owner.
- Staff review the report and make the real decision via
  `/recruit review <application_id> <accept|interview|decline>` (requires
  Manage Server permission) or via the `POST /api/v1/applications/{id}/decision`
  endpoint (dashboard will use this once built).
- If the AI call fails for any reason, the application is still saved and
  flagged for manual review — an applicant is never lost.

## Quick start (development)

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, DISCORD_BOT_TOKEN, DISCORD_GUILD_ID,
# DISCORD_APPLICATION_CHANNEL_ID, OPENAI_API_KEY at minimum

cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the API (creates SQLite tables automatically in development mode)
uvicorn app.main:app --reload

# In a second terminal, run the bot
python -m app.discord_bot.bot
```

See `docs/INSTALLATION.md` for full setup instructions and
`docs/DOCKER.md` for running everything via Docker Compose on your
Proxmox server.

## Repository layout

```
guildos/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── core/                # config, database, logging, security, guild_config
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── api/routes/            # FastAPI route modules
│   │   ├── services/              # business-logic orchestration layer
│   │   ├── ai/                    # AI feature modules (evaluators, OpenAI client)
│   │   ├── discord_bot/           # bot entrypoint + cogs (slash commands)
│   │   └── utils/
│   ├── alembic/                   # DB migrations
│   ├── tests/
│   └── requirements.txt
├── docker/
│   └── backend.Dockerfile
├── docker-compose.yml
├── .env.example
└── docs/
```

## Documentation

- `docs/ARCHITECTURE.md` — how the layers fit together and why
- `docs/INSTALLATION.md` — local dev setup
- `docs/DOCKER.md` — running in Docker on Proxmox
- `docs/CONFIGURATION.md` — every setting, what it does
- `docs/DEVELOPER_GUIDE.md` — adding a new AI feature the way this
  codebase expects
- `docs/API.md` — REST endpoint reference
- `docs/ROADMAP.md` — build order for remaining features
