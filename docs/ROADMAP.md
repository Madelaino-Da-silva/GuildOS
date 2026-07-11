# Roadmap

Build order for the remaining features, each delivered as a complete,
tested vertical slice following `docs/DEVELOPER_GUIDE.md`'s pattern —
not scaffolded in advance.

1. **AI Community Manager** (daily reports) — builds the activity-
   tracking infrastructure (a listener that increments `Member.message_count`
   / `last_active_at`, a scheduled job) that later features (Promotion
   Assistant, Moderator Assistant) will also depend on. Natural next step
   after Recruitment since it establishes the scheduler.

2. **Automation / Scheduler** — APScheduler-based jobs (daily report,
   weekly report, inactivity detection). Bundled with #1 since the Daily
   Report is the scheduler's first real job.

3. **AI Staff Assistant** (nightly summary) — thin layer on top of #1/#2,
   aggregating that day's applications, moderation flags, and events into
   one digest.

4. **AI Moderator Assistant** — message-listener based, flags spam/
   advertising/scams/harassment/raids to staff with evidence, never
   auto-bans. Needs the `ModerationFlag` model + service described in
   `docs/DEVELOPER_GUIDE.md`.

5. **AI Promotion Assistant** — depends on the activity data from #1
   being populated for a while first; recommends promotions against
   `guild_config.promotion_rules`.

6. **AI Event Planner** — event history model, attendance estimation,
   generated announcements ready to post.

7. **Recruitment System expansion** — `/recruit`, `/event`, `/report`,
   `/activity`, `/member`, `/settings` slash commands beyond what
   `/apply` and `/recruit review` already cover.

8. **React Dashboard** — Home, Analytics, Applications, Members, Events,
   Reports, AI Suggestions, Settings pages; JWT auth wired into the
   existing `TODO(dashboard-auth)` markers in the API routes.

9. **AI Memory** — a dedicated store of past AI recommendations/outcomes
   that later evaluations (recruitment, promotions, events) query for
   context, e.g. "this applicant's referrer has a strong recruitment
   track record."

10. **Future expansion** (post-v1) — Minecraft server integration (RCON/
    plugin bridge), guild economy, mobile app, multi-guild support, ML-
    based predictions. Not started; architecture in
    `docs/ARCHITECTURE.md` is intentionally structured (service layer,
    swappable DB, isolated AI layer) to make these additive rather than
    requiring a rewrite.
