# Backend — joblook-backend

**Location:** [services/joblook-backend/](../services/joblook-backend/)
**Stack:** Python 3.11+, FastAPI, Jinja2, SQLAlchemy 2.0, Alembic, Postgres (pgcrypto), Anthropic SDK, Stripe SDK.

## Current modules

| File | Purpose |
|---|---|
| [app/config.py](../services/joblook-backend/app/config.py) | `pydantic-settings` — loads env (DB URL, session secret, Anthropic key/model) |
| [app/db.py](../services/joblook-backend/app/db.py) | SQLAlchemy engine, `SessionLocal`, `Base` (DeclarativeBase), `get_db` dependency |
| [app/schemas.py](../services/joblook-backend/app/schemas.py) | Canonical Pydantic profile — see [PROFILE_SCHEMA.md](PROFILE_SCHEMA.md) |
| `app/routes/` | FastAPI routers (empty — to be added per milestone) |
| `app/templates/` | Jinja2 dashboard templates (empty) |
| `app/static/` | CSS/JS for dashboard (empty) |
| `alembic/` | Migrations (initialized, no baseline yet) |

## Planned modules (per build order)

| File | Milestone | Purpose |
|---|---|---|
| `app/models.py` | M1 | SQLAlchemy `User`, `Profile`, `LlmCostLog`, `CustomAnswer`, `Subscription` |
| `app/auth.py` | M1 | Argon2id hashing, session (`itsdangerous`), Google OAuth, current-user dependency, JWT for extension |
| `app/routes/auth.py` | M1 | `/signup`, `/login`, `/logout`, `/oauth/google/*` |
| `app/routes/dashboard.py` | M1 | `/app`, `/app/profile`, `/app/resume/upload` (Jinja2) |
| `app/routes/profile.py` | M1 | Per-section save endpoints |
| `app/resume_parser.py` | M1 | `pypdf`/`python-docx` → text → Anthropic `messages.parse(Profile)` |
| `app/routes/extension.py` | M3+ | `/api/extension/autofill` (JWT) |
| `app/llm.py` | M4 | Anthropic client wrapper, prompt builder, prompt caching, cost logging |
| `app/rate_limit.py` | M6 | Per-user, per-tier rate limiter |
| `app/routes/billing.py` | M6 | Stripe Checkout + portal redirects |
| `app/routes/webhooks.py` | M6 | `/api/webhooks/stripe` (signature verify, idempotent) |
| `app/main.py` | M1 | FastAPI app, session middleware, CORS for extension, router includes, static mount |

## Configuration

Env vars (see [.env.example](../services/joblook-backend/.env.example)):

| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://...` | Postgres connection |
| `SESSION_SECRET` | `change-me-...` | `itsdangerous` signing key for cookie sessions |
| `ANTHROPIC_API_KEY` | (empty) | Claude API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Default model (resume parsing; may swap to `claude-opus-4-6` for long-form tailoring) |

Additional vars to add as milestones land: `STRIPE_*`, `GOOGLE_OAUTH_*`, `PROFILE_ENCRYPTION_MASTER_KEY`.

## LLM usage

Two distinct call sites:
1. **Resume parsing (M1):** one-shot structured extraction. Use `client.messages.parse(output_format=Profile, ...)` with the canonical Pydantic schema. Cheaper model (`claude-sonnet-4-6`) is fine.
2. **Long-form tailoring (M4):** question + JD → tailored answer. Use prompt caching on the frozen system prompt + user profile prefix (`cache_control: {type: "ephemeral"}`). Check `custom_answers` cache (by `question_hash + job_context_hash`) before calling the API. Opus 4.6 with adaptive thinking for quality; measure cost vs. Sonnet 4.6 empirically.

All calls write a row to `llm_cost_log` (`user_id`, `model`, `input_tokens`, `output_tokens`, `cost_cents`, `endpoint`, `created_at`) per [PRD.md §10](PRD.md).

## Rate limiting (M6)

Middleware on `/api/extension/autofill`:
- Free: 5 tailored answers / day (sliding window).
- Pro: unlimited with burst cap (e.g. 100/hr).
- 429 with `Retry-After` header on miss.

Storage: Postgres row counter initially (simple, durable); Redis if that becomes a bottleneck.

## Running locally

```bash
cd services/joblook-backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # then edit
alembic upgrade head
uvicorn app.main:app --reload
```

(`app.main:app` doesn't exist yet — added in M1.)
