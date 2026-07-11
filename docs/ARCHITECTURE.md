# Architecture

## Layering

GuildOS follows a strict layering so that Discord-specific code and
HTTP-specific code never contain business logic directly:

```
Discord bot (cogs)  ─┐
                      ├──►  services/  ──►  ai/  ──►  openai_client
FastAPI routes       ─┘         │
                                 ▼
                              models/  (SQLAlchemy, via core/database.py)
```

- **`discord_bot/cogs/*`** — only Discord concerns: slash commands,
  modals, buttons, formatting messages. Every cog calls into `services/`
  for actual work and never touches the database or OpenAI directly.
- **`api/routes/*`** — only HTTP concerns: request/response schemas,
  status codes, auth dependencies. Same rule: delegate to `services/`.
- **`services/*`** — the actual business logic (e.g. "submit an
  application, evaluate it, persist the result"). This is what makes it
  possible to trigger the exact same recruitment flow from Discord *or*
  the dashboard without duplicating logic.
- **`ai/*`** — isolates all LLM-specific code: prompt construction,
  response schema validation, retries. If GuildOS ever swaps providers,
  this is the only layer that needs to change.
- **`models/*`** — SQLAlchemy ORM models, the single source of truth for
  the database schema (Alembic migrations are generated from these).

## Why this split matters for a Minecraft guild bot specifically

A guild bot tends to accumulate "just do it inline in the command
handler" code very fast, which then can't be reused for the dashboard
and can't be unit tested without spinning up Discord. By keeping
`services/` framework-agnostic:

- The AI Recruitment Officer logic is tested in `tests/` with zero
  Discord or FastAPI involved (see `test_recruitment_service.py`).
- The exact same `submit_application()` / `record_staff_decision()`
  functions will back both the `/apply` Discord flow and the dashboard's
  Applications page once it's built — no logic fork.

## Database strategy: SQLite → PostgreSQL

`DATABASE_URL` fully determines the database. SQLAlchemy's async engine
and Alembic migrations work identically against
`sqlite+aiosqlite:///...` and `postgresql+asyncpg://...`. To migrate:

1. Stand up a PostgreSQL instance (e.g. another Docker Compose service).
2. Change `DATABASE_URL` in `.env`.
3. Run `alembic upgrade head` against the new database.
4. (Optional) migrate existing data with a one-off script using both
   engines — not included yet since the guild is starting fresh.

No application code changes are required either way — this is why
`Integer` primary keys and standard column types were used throughout
instead of any SQLite-only or Postgres-only features.

## The "AI never decides" boundary

This is enforced structurally, not just by convention:

- `Application.decision` defaults to `PENDING` and is a distinct field
  from `Application.ai_recommendation`.
- The only function that writes to `Application.decision` is
  `record_staff_decision()` in `services/recruitment_service.py`, which
  requires a `decided_by_discord_id` argument — there is no code path
  that sets a decision without an explicit human ID attached.
- The Discord `/recruit review` command requires the `Manage Server`
  permission.

Every future feature (moderation, promotions) will follow the same
pattern: an `ai_*` field/table for the AI's output, a separate
human-decision field, and a service function that's the sole writer of
that human-decision field.

## AI evaluation robustness

`ai/openai_client.py` wraps the OpenAI SDK with:

- Automatic retries (exponential backoff) on transient errors
  (`APIError`, `APITimeoutError`, `RateLimitError`).
- Enforced JSON-object response format from the model.
- A single `AIServiceError` exception type that all AI feature modules
  catch, so a failure degrades gracefully (e.g. "flag for manual
  review") instead of crashing the whole request — see
  `evaluate_application()`'s try/except and the corresponding test
  `test_submit_application_survives_ai_failure`.

## Adding a new feature

See `docs/DEVELOPER_GUIDE.md` for a concrete walkthrough of the pattern
to follow (using the Recruitment Officer as the reference
implementation) when the Community Manager, Event Planner, Moderator
Assistant, and Promotion Assistant features are built next.
