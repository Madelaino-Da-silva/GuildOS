# Developer Guide: Adding a New Feature

This walks through the pattern used by the AI Recruitment Officer, which
every future feature (Community Manager, Event Planner, Moderator
Assistant, Promotion Assistant) should follow for consistency.

## The pattern, step by step

Using "AI Moderator Assistant" as the running example:

### 1. Model(s) — `app/models/`

Add a model for whatever the AI produces, e.g. `ModerationFlag` with
columns like `message_id`, `channel_id`, `flag_type`, `evidence_text`,
`ai_explanation`, `ai_confidence`, and — critically — a separate
human-decision field (`staff_action`, `actioned_by_discord_id`,
`actioned_at`) that starts `NULL`/`PENDING`. Register it in
`app/models/__init__.py`.

### 2. Migration — `alembic/`

```bash
alembic revision --autogenerate -m "add moderation_flags table"
```

Review the generated migration by hand before applying it — autogenerate
is a starting point, not a guarantee (enum types in particular often
need manual fixes, as seen in `0001_initial_schema.py`).

### 3. AI module — `app/ai/`

Add `app/ai/moderation_evaluator.py` following
`recruitment_evaluator.py`'s shape:

- A Pydantic model for the validated AI response shape.
- A function that builds the system + user prompt (personality comes
  from `guild_config.ai_personality` so tone stays consistent across
  features).
- A function that calls `ask_for_json()` from `app/ai/openai_client.py`,
  validates the response, and returns `None` (not an exception) on any
  failure — callers must handle the `None` case explicitly, never assume
  success.

### 4. Service — `app/services/`

Add `app/services/moderation_service.py`. This is where DB writes,
calling the AI module, and building a Discord-ready report all get
orchestrated — kept free of Discord/FastAPI imports so it can be unit
tested directly (see `tests/test_recruitment_service.py` for the
pattern: mock the AI call, assert on DB state).

The service is also the **only** place that ever writes a human decision
field — e.g. `record_staff_moderation_action()` should require an
explicit `actioned_by_discord_id`, mirroring
`record_staff_decision()`.

### 5. API routes — `app/api/routes/`

Add `app/api/routes/moderation.py` with thin routes that just call the
service and shape the response with a Pydantic schema from
`app/schemas/`. Register the router in `app/api/routes/__init__.py`.

### 6. Discord cog — `app/discord_bot/cogs/`

Add `app/discord_bot/cogs/moderation.py`. Cogs should only: define slash
commands/listeners, call the service, and format messages/embeds. Add
the extension path to `INITIAL_EXTENSIONS` in `app/discord_bot/bot.py`.

### 7. Tests — `backend/tests/`

At minimum: one test proving the AI's output never bypasses the
human-decision boundary (mirroring
`test_staff_decision_never_set_by_ai`), and one proving a failed AI call
degrades gracefully instead of losing data (mirroring
`test_submit_application_survives_ai_failure`).

### 8. Docs

Add the feature's behavior to `README.md`'s status table, and to
`docs/CONFIGURATION.md` if it introduces new `guild_config` fields.

## Code style

- Python 3.12, full type hints everywhere (`from __future__ import
  annotations` at the top of every module).
- `ruff` for linting, `mypy` for type checking — both are in
  `requirements.txt`. Run `ruff check .` and `mypy app` before opening a
  PR.
- No business logic in Discord cogs or FastAPI routes — see
  `docs/ARCHITECTURE.md` for why.
- Every AI feature must have a documented "what happens if the AI call
  fails" behavior — silently losing data is never acceptable.
