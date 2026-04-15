# Profile Schema

**Source of truth:** [services/joblook-backend/app/schemas.py](../services/joblook-backend/app/schemas.py) (Pydantic v2).

The extension mirrors this in [`extensions/joblook/content/shared/profile-schema.js`](../extensions/joblook/) (to be added in M2). Any change here requires updating the mirror, the DB migration, and resume-parser prompt examples.

## Top-level shape

```
Profile
├── identity           : Identity
├── work_authorization : WorkAuthorization
├── experience         : list[Experience]
├── education          : list[Education]
├── skills             : list[Skill]
├── preferences        : Preferences
├── demographics       : Demographics        # EEO — optional, user may decline
├── summary            : str
└── custom_answers     : list[CustomAnswer]  # LLM/user tailored free-text
```

## Sections

### `Identity`
Name, email, phone, postal address, LinkedIn / GitHub / portfolio URLs, pronouns.

### `WorkAuthorization`
`us_work_authorized`, `requires_sponsorship_now`, `requires_sponsorship_future`, `visa_status`, `citizenships[]`. All optional — unfilled → leave blank on form.

### `Experience` (list)
`company`, `title`, `location`, `start_date`, `end_date`, `is_current`, `summary`, `bullets[]`. `bullets` powers resume-style population where ATS asks for it.

### `Education` (list)
`school`, `degree`, `field_of_study`, `start_date`, `end_date`, `gpa`, `honors`.

### `Skill` (list)
`name`, optional `years`, optional `level` (`beginner|intermediate|advanced|expert`).

### `Preferences`
`desired_titles[]`, `desired_locations[]`, `remote_preference`, `willing_to_relocate`, `min_salary_usd`, `earliest_start_date`, `notice_period_weeks`.

### `Demographics` (EEO voluntary self-ID)
`gender`, `race_ethnicity[]`, `veteran_status`, `disability_status`, `lgbtq`. **Never auto-fill unless the user has explicitly set a value.** Legal review required before any default behavior.

### `CustomAnswer` (list)
Tailored free-text answers cached by question:

| Field | Purpose |
|---|---|
| `question` | Raw question text |
| `answer` | Final answer |
| `question_hash` | Normalized hash for cache lookup |
| `source` | `user` (edited) or `llm` (unedited) |
| `job_context_hash` | Hash of JD context the answer was tailored to — invalidates cache when JD differs meaningfully |

The `question_hash + job_context_hash` tuple is the cache key for backend `/autofill`.

## Why this shape

- **LLM-friendly.** Pydantic v2 → JSON Schema → Anthropic `messages.parse()` for resume extraction in one call.
- **Adapter-friendly.** Flat enough that `field-mapper.js` heuristics aren't fighting nested structure.
- **Forward-compatible.** `custom_answers` is the overflow bucket for anything we haven't modeled as a first-class field.

## Mutation rules

- Dashboard saves are per-section (partial `PATCH`); full-profile rewrites only happen on resume reparse (with user review).
- `custom_answers` is append-plus-upsert by `question_hash`.
- Never delete history silently — if a user updates an answer, mark prior as `source: user` and overwrite.

## v2 considerations (not in scope now)

- Multiple resumes per profile (role-targeted).
- Cover-letter templates.
- Per-application snapshots (point-in-time profile state at submit).
