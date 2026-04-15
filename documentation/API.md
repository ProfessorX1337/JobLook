# API Contract

All HTTP endpoints exposed by `joblook-backend`. Every path is under `https://joblook.ai`.

## Auth surfaces

| Surface | Auth | Used by |
|---|---|---|
| `/app/*` | Session cookie (signed, `itsdangerous`) + CSRF double-submit on POST | Dashboard |
| `/api/extension/*` | `Authorization: Bearer <JWT>` | Extension |
| `/api/webhooks/*` | Provider signature (Stripe-Signature header) | Stripe |

---

## Dashboard (server-rendered, cookie-auth)

| Method | Path | Purpose | Milestone |
|---|---|---|---|
| GET  | `/` | Marketing landing | pre-M1 |
| GET  | `/signup` | Signup form | M1 |
| POST | `/signup` | Create account (Argon2id) | M1 |
| GET  | `/login` | Login form | M1 |
| POST | `/login` | Establish session | M1 |
| POST | `/logout` | Clear session | M1 |
| GET  | `/oauth/google/start` | Redirect to Google | M1 |
| GET  | `/oauth/google/callback` | Exchange code, establish session | M1 |
| GET  | `/app` | Dashboard home | M1 |
| GET  | `/app/profile` | Profile editor (Jinja2) | M1 |
| POST | `/app/profile/{section}` | Save a section (`identity`, `experience`, etc.) | M1 |
| GET  | `/app/resume` | Upload form | M1 |
| POST | `/app/resume` | Multipart upload → parse → render review | M1 |
| POST | `/app/resume/confirm` | Commit parsed profile | M1 |
| GET  | `/app/billing` | Current tier + Stripe portal link | M6 |
| POST | `/app/billing/checkout` | Create Checkout Session | M6 |
| GET  | `/app/connect-extension` | Issue scoped JWT to extension via `postMessage` | M2 |

---

## Extension (JWT-auth, JSON)

### `POST /api/extension/autofill`
Resolve long-form questions against the user's profile, optionally tailored by Claude.

**Request:**
```json
{
  "ats": "greenhouse",
  "job_context": {
    "url": "https://boards.greenhouse.io/acme/jobs/123",
    "title": "Senior Engineer",
    "company": "Acme",
    "description": "<scraped JD text>",
    "location": "Remote"
  },
  "questions": [
    { "id": "q1", "label": "Why do you want to work at Acme?", "type": "textarea", "max_length": 2000 },
    { "id": "q2", "label": "How many years of Python?", "type": "text" }
  ]
}
```

**Response:**
```json
{
  "answers": [
    { "id": "q1", "value": "…", "source": "llm", "cached": false },
    { "id": "q2", "value": "6", "source": "profile", "cached": true }
  ],
  "usage": { "tailored_today": 3, "tier_limit": 5 }
}
```

- `source`: `profile` (heuristic from profile), `cache` (prior `custom_answers` hit), `llm` (fresh Claude call).
- Returns `429` with `Retry-After` on tier cap.
- Milestone: scaffold in M3 (LLM returns `null`), LLM live in M4.

### `GET /api/extension/profile`
Returns a scrubbed projection of the profile suitable for local standard-field fill.

- Omits `custom_answers` body (extension doesn't need them pre-fill).
- Milestone: M2.

### `POST /api/extension/feedback`
Optional: user marks an LLM answer as good/bad. Feeds M7 metrics.

---

## Webhooks

### `POST /api/webhooks/stripe`
- Verify `Stripe-Signature` with `STRIPE_WEBHOOK_SECRET`.
- Idempotent by Stripe event ID (persisted).
- Events handled: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.
- Milestone: M6.

---

## Error format

JSON endpoints return:
```json
{ "error": { "code": "rate_limited", "message": "Daily tailored-answer limit reached.", "retry_after": 3600 } }
```

HTML endpoints render a themed error page with the same `code` in a hidden comment for support.

## Versioning

No version prefix in v1. Breaking changes to `/api/extension/*` bump extension `manifest.json#version`; Chrome auto-updates. If we need to support old extension versions in flight, add `/api/extension/v2/*` — never mutate v1 semantics in place.
