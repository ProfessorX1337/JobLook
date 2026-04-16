# Project Status

**Snapshot date:** 2026-04-15  
**Current phase:** Extension install-UX polish (icons, welcome tab, popup redesign)
**Next milestone:** Wire the new landing CTA to "Add to Chrome" and mirror the popup's visual language
**Authoritative checklist:** [PRD.md §9](PRD.md) (update checkboxes there as work lands).

---

## Latest Major Update: Extension Install Experience (April 15, 2026)

### ✅ Extension install-to-first-fill flow revamped
Goal: make the post-install experience good enough that a new user actually sees the product work.

- **Icons** — [icons/icon{16,48,128}.png](../extensions/joblook/icons/) generated via Pillow. Ink rounded-square, cream "J", brand-blue accent square. Resolves the long-standing icon-missing warning.
- **Welcome tab** — new [welcome/welcome.html](../extensions/joblook/welcome/welcome.html) auto-opens on first install via `chrome.runtime.onInstalled` in [background/service-worker.js](../extensions/joblook/background/service-worker.js). Three-step onboarding (sign in → connect extension → try on a Greenhouse posting) plus a pin-the-extension nudge.
- **Popup redesign** — [popup/popup.html](../extensions/joblook/popup/popup.html) + [popup.js](../extensions/joblook/popup/popup.js) rewritten as a six-view state machine: signed-out / unsupported page / Lever-Ashby "coming soon" / form-detected with field count / filled with success counts / error. Signed-in profile card (avatar + name + email) anchors every signed-in state. Header status dot shows Connected vs. Signed out.
- **Detect payload** — [content/main.js](../extensions/joblook/content/main.js) now returns `fieldCount` so the popup can preview "N fields ready to fill" before the user clicks.
- **Aesthetic** — ink (#0b1220) / cream (#fafaf7) / brand-blue (#2563eb) with mono-font accents, aligned with the redesigned landing page.

### 🟡 Previous update: Marketing landing redesign (earlier in the day)
- Hero rewritten around the concrete USP — "The autofill that actually reads the job." — with a live-animating Greenhouse form that auto-fills three standard fields, then types a tailored "Why this role?" answer character-by-character. Loops. Respects `prefers-reduced-motion`.
- Dropped the "AI-Powered Career Advantage" rebrand. Trimmed landing to three sections: hero → how-it-works → single CTA.
- Premium teaser, stats, testimonials sections removed from landing (still available on /pricing).

### Next up
M2 smoke test (manual, blocking PRD §M2 checkbox) → M3 backend `/api/extension/autofill` heuristic → M4 LLM tailoring with prompt caching + `custom_answers` cache → M5 Lever + Ashby adapters → M6 Stripe + tier gating → M7 closed beta.

---

## Landing page rewrite — Ogilvy-style long-form copy (April 15, 2026, later)

### ✅ Landing expanded from 3 sections to 8
The hero demo stayed; copy got richer and the page now earns the scroll. Sections in order:

1. **Hero** — live-animating form demo + *"The autofill that actually reads the job."* + dual CTA (Add to Chrome primary, Sign up secondary).
2. **Problem** — "Another Saturday, gone." Three-paragraph Ogilvy-style indictment of the manual grind, with three hard-number stats (11 hrs/week, ~70% field repetition, 1 in 5 abandonment).
3. **What the free extension does** — three benefit-framed cards (standard fields, tailored answers, stays-in-control) with mono-accent hints.
4. **Interactive time calculator** — dark ink section with two range sliders (apps/week, mins/app). Live-updates "hours back per week" + annualized figure + before/after comparison. Fun + sticky, reinforces USP with the visitor's own numbers.
5. **How it works** — unchanged 3-step (install → sign in + upload → fill).
6. **Free vs Premium** — side-by-side tier grid. Free column explains what's free *forever*; Premium column frames features as emotional outcomes ("practice the hard conversations before they cost you $20K") not feature bullets.
7. **FAQ** — six honest objections answered (autosubmit, data handling, supported sites, how AI drafting works, Premium cancellation, "will it get me a job?" — the last answered with deliberate honesty: "No tool gets you a job.").
8. **Final CTA** — unchanged, "Add to Chrome — free" primary.

### ✅ Nav bar slimmed for install-first conversion
[base.html](../services/joblook-backend/app/templates/base.html) nav is now: `Pricing · Log in · Sign up · Add to Chrome (primary button with Chrome logo)`. Dropped Product/Blog/About/Contact from the top nav to reduce friction — they remain reachable via direct URL.

### Design language
Ink/cream/mono palette carried through. One new accent: the calculator section reverses to dark ink with an emerald "hours saved" color pop, creating a visual break between the light sections. Highlighter underline on the hero H1 emphasis phrase is reused on premium tier styling.

---

## Previously: Website Transformation (earlier April 15, 2026)

### ✅ Marketing Website Redesign Complete
- **New Positioning:** "Your AI-Powered Career Advantage"
- **Homepage:** Complete redesign with premium teaser and core capabilities
- **Pricing Page:** Full premium feature breakdown with $19/month pricing
- **Premium Strategy:** Freemium model with clear upgrade path
- **Demo Server:** `demo_main.py` for easy local testing

### ✅ Premium Tier Definition
**Five Feature Categories Defined:**
1. AI-Powered Career Acceleration (Interview Coach, Salary Negotiation)
2. Advanced Insights & Analytics (Performance Prediction, A/B Testing)
3. Enhanced Automation & Efficiency (Smart Autofill, Pipeline Analytics)
4. Networking & Personal Branding (LinkedIn Optimizer, Branding Toolkit)
5. Exclusive Perks & Support (Priority Support, Ad-free Experience)

**Pricing Structure:**
- **Monthly:** $19/month
- **Annual:** $149/year (25% savings)
- **Target:** Serious job seekers willing to invest in career advantage

---

## Where we are

### M1 — Profile pipeline ✅ complete
Backend scaffolding, canonical profile schema, SQLAlchemy models, Alembic baseline, column encryption, auth (email + Google OAuth), resume parser, Jinja2 dashboard, FastAPI app wiring. One punt: the profile editor uses a raw JSON textarea for v1; structured per-section forms are v1.1.

### M2 — Extension skeleton + Greenhouse ✅ code complete (+ install-UX polish shipped)
- [extensions/joblook/](../extensions/joblook/) — MV3 manifest, service worker (JWT storage + authenticated fetch + `externally_connectable` handler + **onInstalled welcome tab**), shared modules ([profile-schema.js](../extensions/joblook/content/shared/profile-schema.js), [field-mapper.js](../extensions/joblook/content/shared/field-mapper.js), [dom-events.js](../extensions/joblook/content/shared/dom-events.js), [api-client.js](../extensions/joblook/content/shared/api-client.js)), content loader, main logic (now returns `fieldCount`), [greenhouse.js](../extensions/joblook/content/adapters/greenhouse.js) adapter.
- **Popup** rewritten as a stateful UI with signed-in profile card, supported-host detection, field-count preview, and filled/skipped/unknown counts.
- **Welcome tab** ([welcome/welcome.html](../extensions/joblook/welcome/welcome.html)) auto-opens on first install.
- **Icons** ([icons/](../extensions/joblook/icons/)) generated — resolves the Web Store submission blocker.
- Backend: `GET /api/extension/profile` (JWT-auth, scrubbed) + CORS for `chrome-extension://*`.
- Dashboard `/app/connect-extension` issues a scoped JWT and sends it to the extension via `chrome.runtime.sendMessage(extensionId, ...)`.

**Remaining:** live smoke test on ≥10 Greenhouse postings to validate the ≥90% fill rate exit criterion (runbook: [SMOKE_TEST.md](SMOKE_TEST.md)).

### M3–M7 — not started
Backend `/autofill` heuristic → LLM tailoring → Lever + Ashby → Stripe + tiers → closed beta.

---

## Local environment (as of snapshot)

| Component | State |
|---|---|
| **Marketing Site** | **✅ Complete redesign with new positioning and premium features** |
| **Demo Server** | **`python3 -m uvicorn demo_main:app --reload --host 0.0.0.0 --port 8000` — serves all marketing pages** |
| Postgres | `postgresql@16` via Homebrew, running as a service (`brew services`). Role `joblook` / db `joblook` / all 8 tables present. |
| Python | 3.12+ dependencies installed globally. FastAPI, uvicorn, jinja2, markdown installed. |
| `.env` | Generated with fresh `SESSION_SECRET`, `EXTENSION_JWT_SECRET`, `PROFILE_ENCRYPTION_MASTER_KEY`. **`ANTHROPIC_API_KEY` still blank** — must be filled before resume parsing works. |
| Migrations | `alembic upgrade head` applied. |
| Backend | `uvicorn app.main:app --host 127.0.0.1 --port 8000` — served `/`, `/signup`, `/login`, `/healthz` at 200 OK on the last check. |
| Extension | Not yet loaded in Chrome. |

Run commands:
```bash
# For marketing website demo
cd services/joblook-backend
python3 -m uvicorn demo_main:app --reload --host 0.0.0.0 --port 8000

# For full backend (when ready)
cd services/joblook-backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

---

## Known issues / risks to track

| # | Issue | Where | Action |
|---|---|---|---|
| 1 | Resume parser uses `messages.create(..., output_config=...)`, a newer Anthropic SDK parameter. Will 500 on older SDKs. | [app/resume_parser.py:67](../services/joblook-backend/app/resume_parser.py) | Verify on first real upload; swap to `messages.parse()` if broken. |
| 2 | ~~Extension has no icon PNGs.~~ | [extensions/joblook/icons/](../extensions/joblook/icons/) | ✅ Resolved 2026-04-15 — ink/cream "J" monogram with brand accent, generated via Pillow. |
| 3 | Profile editor is a JSON textarea, not per-section forms. | [templates/dashboard/profile.html](../services/joblook-backend/app/templates/dashboard/profile.html) | 🟡 In progress — M1.1a user admin panel adds real forms + subscription/usage/billing UI |
| 4 | `authlib` is in deps but unused (Google OAuth is hand-rolled via `httpx`). | [pyproject.toml](../services/joblook-backend/pyproject.toml) | Drop on next dependency review. |
| 5 | Hand-rolled HS256 JWT. Fine for one scope; revisit if we add more token types. | [app/auth.py](../services/joblook-backend/app/auth.py) | Only revisit if token surface grows. |
| 6 | No super admin panel at `/admin`. | [app/main.py](../services/joblook-backend/app/main.py) | 🟡 In progress — M1.1b adds IP-allowlisted `/admin` with user management + system metrics |

---

## Next actions (in order)

1. **Fill `ANTHROPIC_API_KEY`** in [.env](../services/joblook-backend/.env) (blocks resume parsing).
2. **Sign up** at `http://127.0.0.1:8000`, upload a resume, review + save the parsed profile.
3. **Load extension** unpacked at `chrome://extensions` → Developer mode → pick [extensions/joblook/](../extensions/joblook/). Copy the extension ID.
4. **Connect** via `http://127.0.0.1:8000/app/connect-extension` (paste ID, click Connect).
5. **Smoke test** per [SMOKE_TEST.md](SMOKE_TEST.md) — 10 real Greenhouse postings, target ≥90% fill rate.
6. Harvest failure cases into `FIELD_ALIASES` in [profile-schema.js](../extensions/joblook/content/shared/profile-schema.js).
7. Once M2 passes, start **M3**: backend `/api/extension/autofill` heuristic (no LLM yet).
8. **M1.1a**: Build user admin panel (per-section profile forms, subscription status, usage stats, billing portal link, data export).
9. **M1.1b**: Build super admin panel at `/admin` (IP-allowlist middleware, user list + search, tier overrides, system metrics, error log viewer).
