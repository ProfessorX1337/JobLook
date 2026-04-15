# Extension — extensions/joblook

**Location:** [extensions/joblook/](../extensions/joblook/)
**Stack:** Chrome Manifest V3, vanilla JavaScript, no bundler, no framework.

## Design principles

- **Assistive, not automated.** The user always clicks Submit. No event synthesis of the submit button.
- **Scoped permissions.** `host_permissions` lists only Greenhouse, Lever, Ashby, and `api.joblook.ai`. Never `<all_urls>`.
- **Local-first.** Standard fields (name, contact, work auth, EEO) are filled from `chrome.storage.local` with zero API calls. Only custom long-form questions + scraped JD leave the browser.
- **No bundler.** MV3 CSP is strict; ES modules load natively. Fewer moving parts = faster debug loop.
- **Adapters are the abstraction.** ATS quirks are irreducible; each adapter owns its quirks.

## Planned module layout

```
extensions/joblook/
├── manifest.json
├── background/
│   └── service-worker.js        # message routing, JWT storage, API calls
├── content/
│   ├── loader.js                # entry point, picks adapter by URL
│   ├── shared/
│   │   ├── profile-schema.js    # mirrors backend Pydantic — CANONICAL
│   │   ├── field-mapper.js      # label/name/placeholder heuristics
│   │   ├── dom-events.js        # React/Vue-aware native setter dispatch
│   │   └── api-client.js        # fetch wrapper w/ JWT
│   └── adapters/
│       ├── greenhouse.js
│       ├── lever.js
│       └── ashby.js
└── popup/
    ├── popup.html
    └── popup.js                 # status, manual fill, login link
```

## Adapter interface

Every adapter exports:

```js
export const adapter = {
  name: "greenhouse",
  matches(url) { /* boolean */ },
  detectForm() { /* returns form root element or null */ },
  extractJobContext(formRoot) { /* { title, company, description, location, ... } */ },
  listFields(formRoot) { /* [{ id, name, label, type, selector, required }] */ },
  async fillField(field, value) { /* uses dom-events.js */ },
};
```

This keeps `loader.js` dumb: pick adapter, iterate fields, hand off.

## DOM event dispatch

React and Vue track input values via their own internal setters and ignore naive `el.value = x`. `dom-events.js` uses the native property descriptor:

```js
const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
nativeSetter.call(el, value);
el.dispatchEvent(new Event("input", { bubbles: true }));
el.dispatchEvent(new Event("change", { bubbles: true }));
el.dispatchEvent(new Event("blur", { bubbles: true }));
```

Same pattern for `HTMLTextAreaElement` and `HTMLSelectElement`. Checkboxes/radios dispatch `click()` when target state differs from current.

## Field mapping heuristic

`field-mapper.js` scores candidates by:
1. Exact `name` or `id` match against known aliases (`fname`, `first_name`, `givenName` → `identity.first_name`).
2. Label text fuzzy match (normalize whitespace, lowercase, strip "*").
3. `placeholder` / `aria-label` fallback.

Adapters may override with hard selectors where heuristics break.

## Auth flow

1. User logs in on dashboard (`joblook.ai/app`).
2. Dashboard issues a short-lived JWT intended for the extension (scope: `extension`).
3. User opens extension popup, clicks "Connect" → popup opens `joblook.ai/app/connect-extension`.
4. Page posts JWT to extension via `chrome.runtime.sendMessage` (extension ID known).
5. Service worker stores JWT in `chrome.storage.local`.
6. Refresh flow: on 401, popup prompts re-auth.

## Milestones (from [PRD.md §9](PRD.md))

- **M2** — Skeleton + Greenhouse heuristic-only.
- **M3** — Backend `/autofill` wired in (unknowns go to backend, answers not yet LLM-generated).
- **M4** — LLM tailoring live; UI shows answer + Edit/Regenerate per question.
- **M5** — Lever + Ashby adapters.

## Testing approach

- Per-adapter HTML fixtures (saved real postings, scrubbed of PII).
- Jest-style tests running in jsdom for pure field-mapping logic.
- Manual smoke tests on a checklist of 10 live postings per ATS before each release.
- Weekly cron (M7+) that diffs fixture HTML against live postings and alerts on drift.
