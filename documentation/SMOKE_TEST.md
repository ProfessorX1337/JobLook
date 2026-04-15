# M2 Smoke Test — Greenhouse

**Goal:** Verify the extension correctly fills ≥90% of standard fields on 10 real Greenhouse postings without a backend LLM call.

## 0. Prereqs

- Python 3.11+ and Postgres 14+ locally (Docker works: `docker run -p 5432:5432 -e POSTGRES_PASSWORD=joblook -e POSTGRES_USER=joblook -e POSTGRES_DB=joblook postgres:16`).
- An Anthropic API key (for the resume-parse step that populates your profile).
- Google Chrome with Developer Mode available in `chrome://extensions`.

## 1. Backend setup

```bash
cd services/joblook-backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Generate the encryption master key and paste it into `.env` as `PROFILE_ENCRYPTION_MASTER_KEY`:

```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Fill in `.env`:
- `DATABASE_URL` → matches your Postgres
- `SESSION_SECRET` → any long random string
- `ANTHROPIC_API_KEY` → your key (needed for resume parsing)
- `EXTENSION_JWT_SECRET` → another long random string
- `PROFILE_ENCRYPTION_MASTER_KEY` → the base64 string from above

Apply migrations and start the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

You should see logs on http://localhost:8000. Hit `/healthz` to confirm.

## 2. Create a user + profile

1. Open http://localhost:8000 → **Sign up**.
2. Go to **Upload resume**, drop a real PDF/DOCX resume, let Claude parse it.
3. Review the JSON on the review page — fix anything obviously wrong. Save.
4. Confirm your profile JSON looks right at `/app/profile`.

## 3. Load the extension

1. Open `chrome://extensions`, enable **Developer mode** (top right).
2. Click **Load unpacked** → pick `extensions/joblook/`.
3. Note the generated **extension ID** (long alphanumeric string). Copy it.
4. Pin the JobLook icon to your toolbar for easier access.

If the extension fails to load, most likely cause: missing icon PNG files. Icons are referenced but not supplied in the repo — Chrome will warn but still load. You can ignore the icon warnings for the smoke test.

## 4. Connect the extension

1. Go to http://localhost:8000/app/connect-extension.
2. Paste the extension ID, click **Connect**.
3. You should see "Connected." Open the popup — it should say **Signed in**.

## 5. Smoke-test 10 Greenhouse postings

Find 10 different Greenhouse postings across different companies. Good sources:
- https://boards.greenhouse.io/airbnb
- https://boards.greenhouse.io/stripe
- https://boards.greenhouse.io/discord
- https://boards.greenhouse.io/figma
- https://boards.greenhouse.io/anthropic

For each posting:
1. Click **Apply** to reach the application form.
2. Click the JobLook popup → should say **Detected greenhouse application form.**
3. Click **Fill standard fields**.
4. Record results below.

## 6. Track results

Copy this table into a scratch file and fill it in:

| # | Company | Posting URL | Total fields | Filled correctly | Filled wrongly | Skipped | Notes |
|---|---------|-------------|:---:|:---:|:---:|:---:|-------|
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| ... |  |  |  |  |  |  |  |

Compute: **fill rate = correct / total**. Target: **≥ 90%** on standard fields (name, email, phone, address, LinkedIn/GitHub, work authorization).

Custom long-form questions (cover-letter style) and file uploads (resume) are **out of scope** for this test — those land in M3/M4.

## 7. Expected gotchas

- **Service worker sleeps.** MV3 workers die after ~30s idle. If the popup button hangs, close and reopen — it will respawn the worker.
- **React/Vue dropdowns.** Native `<select>` works; custom dropdown components (div-based) will fail to fill. Log those as "wrongly/skipped" and note which company — it's signal for hard-selector overrides later.
- **Inputs inside iframes.** Some Greenhouse embeds put the form in an iframe. Content script matches only the top frame in v1; iframe support is v2.
- **401 from `/api/extension/profile`.** JWT expired or not set. Reconnect from `/app/connect-extension`.
- **CORS errors in DevTools.** Backend needs to be running. Check `uvicorn` logs for the `/api/extension/profile` request.

## 8. Report back

For each field that failed, capture:
- The label text shown on the form
- The field's `name` / `id` / `placeholder` (from DevTools)
- The profile path it *should* have mapped to

Those become new entries in `FIELD_ALIASES` in [extensions/joblook/content/shared/profile-schema.js](../extensions/joblook/content/shared/profile-schema.js).

Once you hit 90% fill rate, M2 is officially done and we move to **M3**.
