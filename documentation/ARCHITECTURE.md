# Architecture

## Components

```
┌─────────────────────┐           ┌──────────────────────────────────┐
│  Chrome Extension   │           │         joblook-backend          │
│  (MV3, vanilla JS)  │           │  (FastAPI + Jinja2 + Postgres)   │
│                     │           │                                  │
│  ┌───────────────┐  │  JWT      │  /                 marketing     │
│  │ content script│──┼──────────▶│  /app              dashboard     │
│  │ per ATS       │  │  HTTPS    │  /api/extension/*  extension API │
│  └───────────────┘  │           │  /api/webhooks/*   stripe        │
│  ┌───────────────┐  │           │                                  │
│  │ service worker│  │           │  ┌────────────┐  ┌────────────┐  │
│  └───────────────┘  │           │  │ Anthropic  │  │  Postgres  │  │
│  ┌───────────────┐  │           │  │    SDK     │  │ + pgcrypto │  │
│  │ popup (status)│  │           │  └────────────┘  └────────────┘  │
│  └───────────────┘  │           └──────────────────────────────────┘
└─────────────────────┘                        ▲
                                               │ Stripe Webhook
                                         ┌─────┴─────┐
                                         │  Stripe   │
                                         └───────────┘
```

## Trust boundaries

1. **Browser ↔ ATS page:** extension content script runs in an isolated world; never trusts page JS.
2. **Extension ↔ backend:** JWT over HTTPS. Scoped `host_permissions` to 3 ATS domains + `api.joblook.ai`.
3. **Dashboard ↔ backend:** same-origin cookie session, CSRF double-submit on state-changing requests.
4. **Backend ↔ Postgres:** column-level encryption (pgcrypto) for sensitive profile fields with per-user keys wrapped by a master key from env/KMS.
5. **Backend ↔ Anthropic:** outbound only, API key in env, never logged.

## Key data flow — autofill a Greenhouse page

1. User navigates to a Greenhouse posting. Content script loads (manifest match pattern).
2. Adapter `detectForm()` identifies the application form.
3. Adapter `listFields()` returns `{name, label, type, selector}[]`.
4. `field-mapper.js` matches each field against the local profile. Known → fill via `dom-events.js` (React/Vue-aware).
5. Unknown long-form fields + JD (from `extractJobContext()`) are batched and POSTed to `/api/extension/autofill` with JWT.
6. Backend:
   - Rate-limit check (per user, per tier).
   - For each question: hash → look up in `custom_answers`. Hit → return cached answer.
   - Miss → call Claude with cached system prompt + profile prefix + question + JD. Log cost. Store answer.
7. Extension receives answers, fills via `dom-events.js`, shows each with Edit/Regenerate controls.
8. **User clicks Submit.** Extension never auto-submits.

## Domain layout

Single apex domain `joblook.ai`:
- `joblook.ai/` — marketing pages
- `joblook.ai/app/*` — authenticated dashboard (cookie session)
- `joblook.ai/api/extension/*` — extension API (JWT auth)
- `joblook.ai/api/webhooks/stripe` — Stripe webhook
- `joblook.ai/privacy`, `/terms` — legal

Nginx terminates TLS; Cloudflare Full (Strict) TLS in front. No subdomain sprawl in v1.

## Why these choices

| Decision | Alternative | Why |
|---|---|---|
| Vanilla JS extension, no bundler | React + Vite + CRX tooling | MV3 CSP is strict; fewer moving parts; debuggable via DevTools on the actual page |
| Per-ATS adapters with uniform interface | Generic field-mapping engine | ATS quirks are irreducible (Lever JD in sidebar, Ashby's Shadow DOM islands); uniform interface makes adding adapter #4 cheap |
| Direct Anthropic SDK | LangChain | No abstraction tax; prompt caching needs precise control over `cache_control` placement |
| FastAPI + Jinja2 | Next.js / SPA | Dashboard is form-heavy CRUD, not interactive; SSR keeps auth simple |
| pgcrypto column encryption | App-layer (Python cryptography) | Keeps secrets out of ORM-level logs; DB-level pgcrypto is battle-tested |
| JWT for extension, cookies for dashboard | Same auth both places | Extension has no cookie jar for the API domain; JWT matches the bearer model cleanly |

## Out of v1

- Queueing (`/autofill` is sync; long-form is one-shot, streams if slow)
- Multi-region
- Mobile
- Admin UI (IP-allowlist `/admin` if needed)

See [PRD.md §6](PRD.md) for full deferral list.
