# Data Model

Postgres, SQLAlchemy 2.0, Alembic migrations. All tables created via Alembic — no auto-create from `Base.metadata.create_all` in prod.

## Tables (v1)

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `email` | citext unique | Lowercased, case-insensitive |
| `password_hash` | text nullable | Argon2id; null if OAuth-only |
| `google_sub` | text nullable unique | OAuth subject ID |
| `tier` | text | `free` \| `pro` |
| `stripe_customer_id` | text nullable | |
| `dek_wrapped` | bytea | Per-user data-encryption key, wrapped by master key |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### `profiles`
| Column | Type | Notes |
|---|---|---|
| `user_id` | uuid PK FK → users | 1:1 with user |
| `data_encrypted` | bytea | `pgp_sym_encrypt(json, dek)` — full canonical Profile JSON |
| `updated_at` | timestamptz | |

Alternative considered: one column per section. Rejected for v1 — profile is read/written whole by dashboard and extension; section-grained encryption adds complexity without a current win.

### `custom_answers`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid FK → users | |
| `question_hash` | text | Normalized SHA-256 of question |
| `job_context_hash` | text | Hash of JD context (company + title + description digest) |
| `answer_encrypted` | bytea | |
| `source` | text | `user` \| `llm` |
| `created_at` | timestamptz | |

Unique index on `(user_id, question_hash, job_context_hash)` — cache key.

### `llm_cost_log`
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `user_id` | uuid FK → users | |
| `endpoint` | text | `resume_parse` \| `autofill_tailor` |
| `model` | text | `claude-opus-4-6` etc. |
| `input_tokens` | int | |
| `output_tokens` | int | |
| `cache_read_tokens` | int | From `usage.cache_read_input_tokens` |
| `cost_cents` | int | Computed from token counts + model price table |
| `created_at` | timestamptz | Indexed |

### `subscriptions`
| Column | Type | Notes |
|---|---|---|
| `user_id` | uuid PK FK → users | |
| `stripe_subscription_id` | text unique | |
| `status` | text | `active`, `past_due`, `canceled`, etc. |
| `current_period_end` | timestamptz | |
| `updated_at` | timestamptz | |

### `rate_limit_counters` (v1 simple)
| Column | Type | Notes |
|---|---|---|
| `user_id` | uuid | |
| `window_start` | timestamptz | Hour bucket |
| `count` | int | |

Primary key `(user_id, window_start)`. Swap to Redis later if this hot-spots.

### `webhook_events`
| Column | Type | Notes |
|---|---|---|
| `provider` | text | `stripe` |
| `event_id` | text | Provider's ID |
| `received_at` | timestamptz | |

Primary key `(provider, event_id)` for idempotency.

## Encryption pattern

```
master_key (env/KMS)
     │
     ├── unwrap(users.dek_wrapped) → dek
     │
     └── pgp_sym_encrypt(profile_json, dek) → profiles.data_encrypted
         pgp_sym_encrypt(answer_text, dek)  → custom_answers.answer_encrypted
```

- `dek` is generated on signup and wrapped with master key before storage.
- Decryption happens server-side only, via a helper in `app/crypto.py` (M1).
- Never log decrypted values.

## Migrations

- `alembic revision --autogenerate -m "..."` for additive changes.
- Destructive changes (drop column, rename) split into multi-step: add → backfill → switch reads → drop.
- Baseline migration lands in M1 alongside first models.

## Indexes

- `users.email` (unique, from `citext`)
- `users.google_sub` (unique)
- `custom_answers (user_id, question_hash, job_context_hash)` (unique) — cache lookup
- `llm_cost_log (user_id, created_at)` — cost alerting
- `rate_limit_counters (user_id, window_start)` — PK
