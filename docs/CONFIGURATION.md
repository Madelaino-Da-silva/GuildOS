# Configuration Guide

GuildOS has two tiers of configuration:

## 1. Infrastructure settings (`.env`, `app/core/config.py`)

Things that only change per-deployment: secrets, database URL, Discord
token, OpenAI key. These require a process restart to change and should
never be exposed to the dashboard.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | yes | Signs JWTs for the dashboard. Generate with `secrets.token_urlsafe(48)`. |
| `DATABASE_URL` | yes | SQLAlchemy async URL. Defaults to local SQLite. See `docs/ARCHITECTURE.md` for Postgres migration. |
| `DISCORD_BOT_TOKEN` | yes | From the Discord Developer Portal. |
| `DISCORD_GUILD_ID` | yes | Your guild's Discord server ID; commands sync to this guild only (instant, unlike global sync). |
| `DISCORD_APPLICATION_CHANNEL_ID` | recommended | Where new-application AI reports are posted. Can also be set at runtime via `guild_config`. |
| `DISCORD_STAFF_CHANNEL_ID` | for future features | Reserved for moderator/staff alerts. |
| `DISCORD_REPORT_CHANNEL_ID` | for future features | Reserved for daily/nightly reports. |
| `DISCORD_OWNER_DM_USER_ID` | optional | If set (and `dm_reports_to_owner` is true), you get DMed every application report too. |
| `OPENAI_API_KEY` | yes | Used for every AI feature. |
| `OPENAI_MODEL` | no | Defaults to `gpt-4o-mini`. |
| `CORS_ORIGINS` | for dashboard | Comma-separated list of origins allowed to call the API. |
| `LOG_LEVEL`, `LOG_DIR` | no | Logging verbosity and where rotating log files are written. |

## 2. Guild settings (`app/core/guild_config.py`, `data/guild_config.json`)

Things guild leadership should be able to tune without touching a
server: application questions, AI personality/tone, promotion rules,
which channel gets which report. These are read/written through
`load_guild_config()` / `save_guild_config()` and will get a dashboard
Settings page UI once the Dashboard feature is built; until then, you
can hand-edit `data/guild_config.json` (it's created with sane defaults
on first read if it doesn't exist).

Current fields:

```jsonc
{
  "application_questions": [
    {"id": "ign", "question": "What is your Minecraft in-game name?"},
    // ... see app/core/guild_config.py for the full default set
  ],
  "ai_personality": "You are a fair, experienced guild recruitment officer ...",
  "minimum_age": 13,
  "report_channel_id": null,
  "staff_channel_id": null,
  "application_channel_id": null,
  "dm_reports_to_owner": true,
  "promotion_rules": {},
  "event_frequency_days": 7
}
```

To change the application questions, edit `application_questions` — each
needs a stable `id` (used as the storage key for that answer) and a
`question` (shown as the modal field label, so keep it under ~45
characters or Discord will truncate it — a longer version can go in a
follow-up message if needed).

To change the AI's tone, edit `ai_personality` — this text is injected
directly into the system prompt for every recruitment evaluation.
