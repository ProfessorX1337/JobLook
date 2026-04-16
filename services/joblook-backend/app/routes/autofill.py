"""M3/M4 — Heuristic + LLM autofill endpoint.

Handles:
- /api/extension/autofill  (POST, JWT-auth)
  - Accepts list of questions + job context
  - Checks custom_answers cache (question_hash + job_context_hash)
  - Routes easy questions to profile lookups via question classifier
  - Routes hard questions to LLM generation (M4)
  - Returns per-question answer + source + confidence
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_extension_user
from ..autofill.classifier import (
    AnswerSource,
    QuestionClassification,
    classify_question,
)
from ..crypto import decrypt_column, encrypt_column, unwrap_dek
from ..db import get_db
from ..models import CustomAnswer as CustomAnswerRow, LlmCostLog, User
from ..profile_store import load_profile
from ..schemas import Profile

router = APIRouter(prefix="/api/extension")


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:64]


class QuestionInput(BaseModel):
    question: str
    question_hash: str | None = None


class AutofillRequest(BaseModel):
    questions: list[QuestionInput]
    job_context_hash: str = Field(default="")
    job_context: dict = Field(default_factory=dict)  # {description: str, title: str, ...}


class AnswerOutput(BaseModel):
    question: str
    answer: str | None = None
    source: str  # "profile" | "cache" | "heuristic" | "llm"
    confidence: float
    cached: bool = False
    question_hash: str


# ── Cache ───────────────────────────────────────────────────────────────────

def _load_cached_answer(
    db: Session, user_id: str, question_hash: str, job_context_hash: str,
) -> tuple[str | None, str]:
    row = db.execute(
        select(CustomAnswerRow).where(
            CustomAnswerRow.user_id == user_id,
            CustomAnswerRow.question_hash == question_hash,
            CustomAnswerRow.job_context_hash == job_context_hash,
        )
    ).scalar_one_or_none()
    if row is None:
        return None, ""
    user = db.get(User, user_id)
    if user is None:
        return None, ""
    dek = unwrap_dek(user.dek_wrapped)
    answer: str = decrypt_column(db, row.data_encrypted, dek)
    return answer, "cache"


def _save_cached_answer(
    db: Session,
    user_id: str,
    question_hash: str,
    job_context_hash: str,
    answer: str,
    source: str = "llm",
) -> None:
    user = db.get(User, user_id)
    if user is None:
        return
    dek = unwrap_dek(user.dek_wrapped)
    ct = encrypt_column(db, answer, dek)
    row = CustomAnswerRow(
        user_id=user_id,
        question_hash=question_hash,
        job_context_hash=job_context_hash,
        answer_encrypted=ct,
        source=source,
    )
    db.add(row)


# ── Profile field lookup ────────────────────────────────────────────────────

def _profile_lookup(classification: QuestionClassification, profile: Profile) -> str | None:
    if classification.source != AnswerSource.PROFILE or not classification.field_key:
        return None

    fk = classification.field_key
    ident = profile.identity
    prefs = profile.preferences
    work_auth = profile.work_authorization

    # Direct identity fields
    val: Any = getattr(ident, fk, None)
    if val not in (None, "", [], {}):
        return ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)

    # Preferences
    val = getattr(prefs, fk, None)
    if val not in (None, "", [], {}):
        return ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)

    # Work authorization booleans → yes/no
    if fk in ("us_work_authorized", "requires_sponsorship_now",
              "requires_sponsorship_future", "willing_to_relocate"):
        val = getattr(work_auth, fk, None)
        if val is True:
            return "Yes"
        if val is False:
            return "No"

    return None


# ── Heuristic answer (no LLM) ───────────────────────────────────────────────

_HEURISTIC_EEOC: list[tuple[str, re.Pattern]] = [
    ("eeoc_disability", re.compile(r"(disability|disabled)", re.I)),
    ("eeoc_gender",     re.compile(r"(gender|sex)", re.I)),
    ("eeoc_race",       re.compile(r"(race|ethnicity)", re.I)),
    ("eeoc_veteran",    re.compile(r"(veteran|vet)", re.I)),
]
_YES_NO_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(are\s*you\s*)?willing\s+to\s+travel", re.I),
    re.compile(r"^(are\s*you\s*)?authorized\s+to\s+work", re.I),
    re.compile(r"^(do\s*you\s*)?require\s+sponsorship", re.I),
    re.compile(r"^(are\s*you\s*)?a\s+veteran", re.I),
]


def _heuristic_answer(classification: QuestionClassification, question: str) -> str | None:
    if classification.source != AnswerSource.HEURISTIC:
        return None

    # EEOC fields → decline to self-identify (voluntary)
    if classification.field_key:
        for key, pat in _HEURISTIC_EEOC:
            if key == classification.field_key and pat.search(question):
                return "Decline to self-identify"

    # Yes/no short-answer questions
    for pat in _YES_NO_PATTERNS:
        if pat.match(question.strip()):
            q = question.lower()
            if any(neg in q for neg in ["not willing", "not able", "no, ", "don't"]):
                return "No"
            return "Yes"

    return None


# ── Main endpoint ───────────────────────────────────────────────────────────

@router.post("/autofill")
def autofill(
    payload: AutofillRequest,
    user: User = Depends(current_extension_user),
    db: Session = Depends(get_db),
):
    profile = load_profile(db, user)
    uid = str(user.id)
    results: list[AnswerOutput] = []

    for item in payload.questions:
        q_hash = item.question_hash or _hash(item.question)
        job_ctx = payload.job_context_hash or ""

        # 1. Cache hit
        cached_answer, cache_source = _load_cached_answer(db, uid, q_hash, job_ctx)
        if cached_answer is not None:
            results.append(AnswerOutput(
                question=item.question,
                answer=cached_answer,
                source=cache_source,
                confidence=1.0,
                cached=True,
                question_hash=q_hash,
            ))
            continue

        # 2. Classify
        classification = classify_question(item.question)

        # 3. Profile lookup
        if classification.source == AnswerSource.PROFILE:
            answer = _profile_lookup(classification, profile)
            if answer is not None:
                _save_cached_answer(db, uid, q_hash, job_ctx, answer, source="profile")
                results.append(AnswerOutput(
                    question=item.question,
                    answer=answer,
                    source="profile",
                    confidence=classification.confidence,
                    cached=False,
                    question_hash=q_hash,
                ))
                continue

        # 4. Heuristic
        if classification.source == AnswerSource.HEURISTIC:
            answer = _heuristic_answer(classification, item.question)
            if answer is not None:
                _save_cached_answer(db, uid, q_hash, job_ctx, answer, source="heuristic")
                results.append(AnswerOutput(
                    question=item.question,
                    answer=answer,
                    source="heuristic",
                    confidence=classification.confidence,
                    cached=False,
                    question_hash=q_hash,
                ))
                continue

        # 5. LLM generation (M4)
        from ..autofill.llm import generate_answer, log_llm_cost
        try:
            job_desc = payload.job_context.get("description", "") if payload.job_context else ""
            llm_result = generate_answer(
                profile=profile,
                question=item.question,
                job_description=job_desc,
                job_context_hash=job_ctx,
            )
            _save_cached_answer(db, uid, q_hash, job_ctx, llm_result.answer, source="llm")
            log_llm_cost(db, uid, "autofill", llm_result)
            results.append(AnswerOutput(
                question=item.question,
                answer=llm_result.answer,
                source="llm",
                confidence=1.0,
                cached=False,
                question_hash=q_hash,
            ))
        except Exception as e:
            # LLM failed — return null rather than crashing the whole batch
            results.append(AnswerOutput(
                question=item.question,
                answer=None,
                source="llm_error",
                confidence=0.0,
                cached=False,
                question_hash=q_hash,
            ))

    db.commit()
    return JSONResponse({"results": [r.model_dump() for r in results]})
