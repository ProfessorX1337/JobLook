# Security

## Threat model (v1)

| Asset | Threat | Mitigation |
|---|---|---|
| User profile at rest | DB dump, insider read | pgcrypto column encryption, per-user AES keys wrapped by master key in env/KMS |
| User profile in transit | MITM | TLS everywhere, Cloudflare Full (Strict) |
| Session hijack | XSS, cookie theft | `HttpOnly` + `Secure` + `SameSite=Lax` cookies, CSP on dashboard, CSRF double-submit |
| Extension JWT theft | Compromised ATS page JS reading extension storage | Extension storage is isolated from page JS; JWTs never injected into page DOM |
| Credential stuffing | Reused passwords | Argon2id (memory-hard), email-based lockout after N failures, offer Google OAuth |
| LLM prompt injection via JD | JD text coerces Claude to leak profile or emit harmful content | System prompt pins role + refuses profile exfiltration; JD is wrapped in delimiter with "untrusted content" framing |
| Abuse / cost blowout | Paid user or leaked JWT spams `/autofill` | Per-user rate limits (Free 5/day, Pro 100/hr), cost log w/ daily alert threshold |
| Stripe webhook spoof | Forged events granting Pro | `Stripe-Signature` verification, idempotent handler |
| Supply chain (extension deps) | Malicious package → user data | Vanilla JS, zero runtime deps in extension. Backend deps pinned in `pyproject.toml`, Dependabot on. |

## Encryption

- **At rest (DB):** `pgcrypto` `pgp_sym_encrypt` on sensitive profile columns. Per-user data-encryption key (DEK), DEK wrapped by master key (env in dev, KMS in prod). DEK rotation plan: v2.
- **In transit:** TLS 1.3, HSTS on dashboard. Cloudflare Full (Strict).
- **Secrets:** Env vars only; never logged. `ANTHROPIC_API_KEY`, `STRIPE_*`, `SESSION_SECRET`, `PROFILE_ENCRYPTION_MASTER_KEY`, `GOOGLE_OAUTH_*`.

## Auth

- Passwords: Argon2id (`argon2-cffi`), default cost params.
- Sessions: `itsdangerous` signed cookies, 30-day rolling expiry.
- CSRF: double-submit token on all state-changing POSTs from dashboard.
- Extension: short-lived JWT (e.g. 7-day), stored in `chrome.storage.local`, refreshed via dashboard reconnect on 401.
- OAuth: Google only at launch. PKCE flow. Account link by verified email.

## Extension permissions

Manifest `host_permissions`:
- `https://boards.greenhouse.io/*`
- `https://*.greenhouse.io/*`
- `https://jobs.lever.co/*`
- `https://jobs.ashbyhq.com/*`
- `https://api.joblook.ai/*`

No `<all_urls>`, no broad host permission, no `tabs` permission.

## Privacy surface

- Only custom long-form questions + scraped JD leave the browser. Standard fields never do.
- JD text is sent to Anthropic for tailoring. Users are told this in the privacy policy.
- Data export (JSON) and account delete are available from day one (M1 bonus or M7 latest).
- Retention: profile kept until deletion. `llm_cost_log` kept 18 months for billing reconciliation then purged.

## Incident response (v1-lite)

- Sentry (or equivalent) errors → email.
- Daily SQL job: sum `llm_cost_log.cost_cents` grouped by user; alert if any user > $5/day.
- Manual playbook: revoke JWT (rotate signing key), disable account, force password reset.
