# Project Status

**Snapshot date:** 2026-04-15
**Current milestone:** M2 — feature-complete in code; awaiting live-site smoke test.
**Authoritative checklist:** [PRD.md §9](PRD.md) (update checkboxes there as work lands).

---

## Where we are

### M1 — Profile pipeline ✅ complete
Backend scaffolding, canonical profile schema, SQLAlchemy models, Alembic baseline, column encryption, auth (email + Google OAuth), resume parser, Jinja2 dashboard, FastAPI app wiring. One punt: the profile editor uses a raw JSON textarea for v1; structured per-section forms are v1.1.

### M2 — Extension skeleton + Greenhouse ✅ code complete
- [extensions/joblook/](../extensions/joblook/) — MV3 manifest, service worker (JWT storage + authenticated fetch + `externally_connectable` handler), shared modules ([profile-schema.js](../extensions/joblook/content/shared/profile-schema.js), [field-mapper.js](../extensions/joblook/content/shared/field-mapper.js), [dom-events.js](../extensions/joblook/content/shared/dom-events.js), [api-client.js](../extensions/joblook/content/shared/api-client.js)), content loader, main logic, [greenhouse.js](../extensions/joblook/content/adapters/greenhouse.js) adapter, popup.
- Backend: `GET /api/extension/profile` (JWT-auth, scrubbed) + CORS for `chrome-extension://*`.
- Dashboard `/app/connect-extension` issues a scoped JWT and sends it to the extension via `chrome.runtime.sendMessage(extensionId, ...)`.

**Remaining:** one manual task — live smoke test on ≥10 Greenhouse postings to validate the ≥90% fill rate exit criterion (runbook: [SMOKE_TEST.md](SMOKE_TEST.md)).

### M3–M7 — not started
Backend `/autofill` heuristic → LLM tailoring → Lever + Ashby → Stripe + tiers → closed beta.

---

## Local environment (as of snapshot)

| Component | State |
|---|---|
| Postgres | `postgresql@16` via Homebrew, running as a service (`brew services`). Role `joblook` / db `joblook` / all 8 tables present. |
| Python | 3.12 via Homebrew. venv at `services/joblook-backend/.venv`. All deps installed, including `pydantic[email]`. |
| `.env` | Generated with fresh `SESSION_SECRET`, `EXTENSION_JWT_SECRET`, `PROFILE_ENCRYPTION_MASTER_KEY`. **`ANTHROPIC_API_KEY` still blank** — must be filled before resume parsing works. |
| Migrations | `alembic upgrade head` applied. |
| Backend | `uvicorn app.main:app --host 127.0.0.1 --port 8000` — served `/`, `/signup`, `/login`, `/healthz` at 200 OK on the last check. |
| Extension | Not yet loaded in Chrome. |

Run commands:
```bash
cd services/joblook-backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

---

## Known issues / risks to track

| # | Issue | Where | Action |
|---|---|---|---|
| 1 | Resume parser uses `messages.create(..., output_config=...)`, a newer Anthropic SDK parameter. Will 500 on older SDKs. | [app/resume_parser.py:67](../services/joblook-backend/app/resume_parser.py) | Verify on first real upload; swap to `messages.parse()` if broken. |
| 2 | Extension has no icon PNGs. Chrome loads it anyway with a warning. | [extensions/joblook/icons/](../extensions/joblook/icons/) | Cosmetic; fix before Chrome Web Store submission (M7). |
| 3 | Profile editor is a JSON textarea, not per-section forms. | [templates/dashboard/profile.html](../services/joblook-backend/app/templates/dashboard/profile.html) | Accepted for v1; build structured forms in v1.1. |
| 4 | `authlib` is in deps but unused (Google OAuth is hand-rolled via `httpx`). | [pyproject.toml](../services/joblook-backend/pyproject.toml) | Drop on next dependency review. |
| 5 | Hand-rolled HS256 JWT. Fine for one scope; revisit if we add more token types. | [app/auth.py](../services/joblook-backend/app/auth.py) | Only revisit if token surface grows. |

---

## Next actions (in order)

1. **Fill `ANTHROPIC_API_KEY`** in [.env](../services/joblook-backend/.env) (blocks resume parsing).
2. **Sign up** at `http://127.0.0.1:8000`, upload a resume, review + save the parsed profile.
3. **Load extension** unpacked at `chrome://extensions` → Developer mode → pick [extensions/joblook/](../extensions/joblook/). Copy the extension ID.
4. **Connect** via `http://127.0.0.1:8000/app/connect-extension` (paste ID, click Connect).
5. **Smoke test** per [SMOKE_TEST.md](SMOKE_TEST.md) — 10 real Greenhouse postings, target ≥90% fill rate.
6. Harvest failure cases into `FIELD_ALIASES` in [profile-schema.js](../extensions/joblook/content/shared/profile-schema.js).
7. Once M2 passes, start **M3**: backend `/api/extension/autofill` heuristic (no LLM yet).
