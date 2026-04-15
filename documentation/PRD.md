# JobLook — Product Requirements Document

**Owner:** Bradley
**Status:** Draft / in active build
**Last updated:** 2026-04-15
**Version:** v1 (pre-beta)

---

## 1. Problem

Applicants waste hours re-entering the same data into different ATS forms, and custom long-form questions ("Why us?", "Describe a time…") demand fresh tailoring per job. Existing tools either over-automate (risking ATS ToS violations, bans, and broken applications) or under-deliver (browser autofill only handles name/email).

## 2. Solution

A Chrome extension that detects ATS forms, fills known fields locally from a canonical user profile, and — for custom questions — sends the question plus scraped job description to a backend, which uses Claude to generate a tailored answer. The user reviews every answer and clicks Submit themselves. **Assistive, not automated.**

## 3. Goals & Non-Goals

### Goals (v1)
- Fill 90%+ of standard fields on Greenhouse, Lever, Ashby without user edits.
- Generate tailored long-form answers that users accept without rewriting > 50% of the time.
- Reduce median per-application time from ~15 min to < 3 min.
- Ship a sustainable unit economic: < $0.05 LLM cost per tailored application on Pro tier.

### Non-Goals (v1)
- Workday, LinkedIn Easy Apply (deferred to v2 — iframes + Shadow DOM).
- Auto-submit. The user always clicks submit.
- Mobile.
- Enterprise / team features.
- Resume generation or rewriting. We parse the user's existing resume only.

## 4. Target Users

- **Primary:** Active job seekers (tech-adjacent) applying to 10+ roles/week.
- **Secondary:** Career switchers who need to re-tailor every cover-letter-style answer.

## 5. v1 Feature Scope

| # | Feature | Surface | Notes |
|---|---|---|---|
| F1 | Signup / login (email + Google OAuth) | Dashboard | Argon2id, session cookie |
| F2 | Resume upload → parse → review → save to profile | Dashboard | PDF/DOCX; one LLM extraction call |
| F3 | Profile editor (all canonical fields) | Dashboard | Jinja2 forms, per-section save |
| F4 | Greenhouse adapter | Extension | Heuristic field mapping first |
| F5 | Lever adapter | Extension | |
| F6 | Ashby adapter | Extension | |
| F7 | Local standard-field autofill (zero API calls) | Extension | Name, contact, work auth, EEO |
| F8 | Job description scraping per ATS | Extension | Powers LLM context |
| F9 | LLM-tailored long-form answer generation | Backend | `/api/extension/autofill` |
| F10 | `custom_answers` hash cache (skip LLM on repeat) | Backend | Keyed by question_hash + job_context_hash |
| F11 | Stripe Checkout + Free/Pro tiers | Dashboard + webhook | Free 5 tailored/day, Pro unlimited w/ burst cap |
| F12 | Per-user rate limiting | Backend middleware | |
| F13 | LLM cost logging (user, model, tokens, cost_cents) | Backend | Day one |

## 6. Out of Scope (explicit deferrals)

- Workday / LinkedIn adapters → v2
- Admin UI (v1 uses IP-allowlisted `/admin` if needed)
- Analytics dashboard for users
- Multi-profile support (one profile per account in v1)
- Team / employer features
- Interview scheduling, offer tracking, pipeline management

## 7. Success Metrics

### Leading (measured from launch)
- **Activation:** % of signups who complete profile + install extension within 24h. Target: 40%.
- **Fill accuracy:** % of standard fields correct without user edit. Target: 90%.
- **Answer acceptance:** % of LLM answers accepted with < 50% rewrite. Target: 60%.

### Lagging
- **Weekly retention (W4):** % of activated users still filling an app at week 4. Target: 25%.
- **Pro conversion:** % of Free users upgrading in 30 days. Target: 8%.
- **Gross margin per Pro user:** Target: 85%+ (LLM cost < 15% of sub price).

## 8. Architecture Summary

See [ARCHITECTURE.md](ARCHITECTURE.md). Key decisions:
- Chrome MV3, vanilla JS, no bundler. Scoped `host_permissions` to 3 ATS domains + `api.joblook.ai`.
- FastAPI + Jinja2 + Postgres + Alembic. Direct Anthropic SDK, no LangChain.
- pgcrypto column encryption for sensitive profile fields, per-user keys wrapped by master key.
- Single domain `joblook.ai` (`/`, `/app`, `/api/extension/*`), nginx + Cloudflare Full TLS.
- Auth: Argon2id + Google OAuth. JWT for extension, cookie sessions for dashboard. CSRF double-submit.

## 9. Build Order & Milestones

Each milestone is a checkpoint where the product should be demo-able end-to-end at its current scope.

### M1 — Profile pipeline (dashboard only, no extension)
**Goal:** A user can sign up, upload a resume, and end up with a complete profile in Postgres.
- [x] Backend scaffold (pyproject, config, db, schemas)
- [x] SQLAlchemy models (User, Profile) + Alembic baseline migration
- [x] Auth: signup/login, Argon2id, session cookie (itsdangerous), Google OAuth
- [x] Resume parser: pypdf / python-docx + Anthropic structured output → Profile
- [x] Jinja2 dashboard: signup, login, upload → review → save, profile editor
- [x] FastAPI main app wired (CSRF middleware, static, routers, `/healthz`)
- [ ] Per-section save endpoints (deferred — full-profile JSON save lands v1; structured per-section forms = v1.1)

**Exit criteria:** I can sign up, upload my resume, fix any parse errors, and save. `SELECT profile_encrypted FROM users` returns encrypted bytes.

### M2 — Extension skeleton + Greenhouse (heuristic-only)
- [x] MV3 manifest with scoped host_permissions
- [x] Service worker + content-script loader per ATS
- [x] `profile-schema.js` (mirrors backend Pydantic)
- [x] `field-mapper.js` (label + name + placeholder heuristics)
- [x] `dom-events.js` (React/Vue-aware native setter dispatch)
- [x] Greenhouse adapter: `detectForm`, `extractJobContext`, `listFields`
- [x] Login flow: JWT from dashboard, stored in `chrome.storage.local` (via `externally_connectable`)
- [x] Popup: status + "fill standard fields" button
- [x] Backend `/api/extension/profile` endpoint + CORS for chrome-extension origins
- [ ] Live smoke test on 10 Greenhouse postings (manual validation task)

**Exit criteria:** On a real Greenhouse posting, clicking Fill populates 90% of standard fields correctly. Zero backend calls.

### M3 — Backend `/autofill` heuristic
- [ ] `/api/extension/autofill` endpoint (JWT auth)
- [ ] Accept list of unknown questions + JD; return per-question answer candidates
- [ ] For now, return `null` for anything not heuristically derivable — no LLM yet

**Exit criteria:** Extension posts questions, receives structured responses, fills known ones, leaves unknowns blank.

### M4 — LLM tailoring for long-form
- [ ] Prompt design (system prompt + cached profile + user question + JD context)
- [ ] Prompt caching via `cache_control` on the frozen system + profile prefix
- [ ] `custom_answers` hash cache lookup before LLM call (keyed by `question_hash` + `job_context_hash`)
- [ ] Cost logging row per LLM call
- [ ] Write answer back to `custom_answers` on save

**Exit criteria:** Long-form answer arrives in < 8s, costs < $0.02, second identical question hits cache with zero LLM spend.

### M5 — Lever + Ashby adapters
- [ ] Lever adapter + its JD scraper
- [ ] Ashby adapter + its JD scraper
- [ ] Cross-ATS regression: same profile, same test postings, capture fill-rate per adapter

**Exit criteria:** 90% fill rate on 10 sample postings per ATS.

### M6 — Stripe + tiers + rate limits
- [ ] Stripe Checkout (Pro monthly)
- [ ] `/api/webhooks/stripe` (signature verify, idempotent handler)
- [ ] Tier column on user; rate limiter checks tier on `/autofill`
- [ ] Free: 5 tailored answers/day. Pro: unlimited with burst cap (e.g. 100/hr).
- [ ] Billing page in dashboard (current tier, manage via Stripe portal)

**Exit criteria:** I can upgrade, cap lifts, downgrade returns cap, webhook replay is safe.

### M7 — Closed beta (20 users)
- [ ] Privacy policy + ToS live at `/privacy`, `/terms`
- [ ] Feedback capture (simple form or Typeform link)
- [ ] Basic error reporting (Sentry or equivalent)
- [ ] Cost dashboard (SQL view over `llm_cost_log`)
- [ ] Onboard 20 invited users, weekly check-ins

**Exit criteria:** 20 users, 4 weeks of data, clear signal on acceptance-rate and retention metrics from §7.

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ATS DOM changes break adapter | High | High | Per-adapter test fixtures (saved HTML); weekly smoke test; heuristic fallback before hard selectors |
| LLM cost runs hot | Medium | High | Prompt caching, answer hash cache, per-tier rate limits, cost logging + alert |
| ATS ToS pushback | Low-Med | High | Strictly assistive (no auto-submit), scoped host_permissions, transparent UX showing every fill |
| User trust re: profile data | Med | High | Column encryption at rest, clear privacy policy, data export + delete from day one |
| Parse error rate on resumes | Med | Med | Always show parsed output for user review before save |
| Chrome Web Store review delay | Med | Med | Submit early (M2 done), iterate while in review |

## 11. Open Questions

- **Pricing:** Pro at $15/mo or $20/mo? Revisit after M6 with cost data.
- **Cover letters:** In scope for v1 tailoring, or deferred? Currently scoped via `custom_answers` but not as a first-class feature.
- **Multi-resume per profile:** Deferred — is one resume + one cover-letter template enough for beta feedback?
- **EEO auto-fill:** Legal review needed before defaulting any demographic answer. v1 plan: leave unchecked unless user explicitly sets.

## 12. Tracking

- **Tasks:** GitHub issues (to be created), one per §9 milestone subtask.
- **Status:** This PRD is the source of truth. Update §9 checkboxes + "Last updated" on material changes.
- **Component specs:** Kept in sibling docs in this folder; cross-link rather than duplicate.
