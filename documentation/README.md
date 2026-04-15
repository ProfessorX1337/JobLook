# JobLook Documentation

JobLook is a Chrome extension + FastAPI backend that auto-fills job applications on Greenhouse, Lever, and Ashby (v1). Standard fields fill locally; custom long-form questions are tailored by Claude on the backend.

## Index

- [STATUS.md](STATUS.md) — **current project state, what's running locally, next actions**. Start here after a break.
- [PRD.md](PRD.md) — product requirements, scope, milestones, success metrics, risks. **The project management plan.**
- [SMOKE_TEST.md](SMOKE_TEST.md) — runbook for the M2 Greenhouse live-site smoke test.
- [ARCHITECTURE.md](ARCHITECTURE.md) — system overview, data flow, trust boundaries, domain layout.
- [BACKEND.md](BACKEND.md) — FastAPI service: modules, auth, LLM integration, rate limiting, cost logging.
- [EXTENSION.md](EXTENSION.md) — Chrome MV3 extension: adapters, field mapping, DOM event dispatch.
- [PROFILE_SCHEMA.md](PROFILE_SCHEMA.md) — canonical profile shape (the contract between every component).
- [API.md](API.md) — HTTP contract between extension, dashboard, and backend.
- [SECURITY.md](SECURITY.md) — threat model, encryption, auth, CSRF, rate limits.
- [DATA_MODEL.md](DATA_MODEL.md) — Postgres schema, encryption strategy, migrations.

## Repo layout

```
JobLook/
├── documentation/           # this folder
├── extensions/joblook/      # Chrome MV3 extension (vanilla JS, no bundler)
└── services/joblook-backend/# FastAPI + Jinja2 + Postgres + Alembic + Stripe
    ├── app/
    │   ├── config.py        # pydantic-settings
    │   ├── db.py            # SQLAlchemy engine/session/Base
    │   ├── schemas.py       # canonical Pydantic profile schema
    │   ├── routes/          # FastAPI routers
    │   ├── templates/       # Jinja2 dashboard
    │   └── static/
    └── alembic/             # migrations
```

## Current status

See [STATUS.md](STATUS.md) for a live snapshot. Short version (2026-04-15): M1 shipped; M2 code complete; Postgres + backend running locally; awaiting live-site Greenhouse smoke test.
