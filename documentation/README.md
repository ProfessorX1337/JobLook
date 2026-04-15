# JobLook Documentation

**JobLook: Your AI-Powered Career Advantage**

JobLook is an intelligent job search platform that combines AI-driven matching, automation, and organization into one seamless experience. It transforms the chaotic, time-consuming job hunt into a structured, efficient process through a Chrome extension + FastAPI backend architecture.

## Product Evolution

**Current Positioning (April 2026):** AI-Powered Career Platform  
**Previous:** Simple application auto-fill tool

**Core Value Proposition:** Turn your job search into a competitive advantage with intelligent assistance that maintains user control—helping you apply smarter and faster while keeping applications personal and authentic.

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

## Marketing Website Features

**Core Capabilities:**
- Smart Job Discovery & Personalized Matching
- AI Resume & Application Optimizer  
- Application Acceleration & Autofill
- Centralized Pipeline Dashboard
- Career Support Tools
- AI-Powered Career Acceleration (Premium)

**Business Model:** Freemium with Premium tier at $19/month or $149/year

## Current Status

See [STATUS.md](STATUS.md) for a live snapshot. 

**Latest Updates (April 2026):**
- ✅ Complete marketing website redesign with new positioning
- ✅ Premium tier definition and pricing page
- ✅ AI-powered feature roadmap defined
- ✅ Demo server for local testing
- 🔄 Backend premium feature implementation (in progress)
- 📋 User dashboard redesign (planned)
