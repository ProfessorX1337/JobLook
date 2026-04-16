"""Heuristic question classifier — routes to cache, profile lookup, or LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class AnswerSource(str, Enum):
    PROFILE = "profile"      # derivable from the user's stored profile
    HEURISTIC = "heuristic"  # pattern-matched without LLM
    LLM = "llm"             # requires LLM generation


@dataclass
class QuestionClassification:
    source: AnswerSource
    confidence: float  # 0.0–1.0
    field_key: str | None = None  # which profile field maps here


# ── Pattern rules ──────────────────────────────────────────────────────────

# Fields derivable directly from profile.identity
IDENTITY_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    ("first_name",   [re.compile(r"^first\s*(name|_)?$", re.I),
                       re.compile(r"^given\s*name$", re.I)]),
    ("last_name",    [re.compile(r"^last\s*(name|_)?$", re.I),
                       re.compile(r"^family\s*name$", re.I)]),
    ("email",        [re.compile(r"^(email|e-?mail\s*address)$", re.I)]),
    ("phone",        [re.compile(r"^phone$", re.I),
                       re.compile(r"^tel(ephone)?$", re.I),
                       re.compile(r"^mobile$", re.I)]),
    ("city",         [re.compile(r"^city$", re.I)]),
    ("state",        [re.compile(r"^state$", re.I),
                       re.compile(r"^province$", re.I)]),
    ("postal_code",  [re.compile(r"^zip(\s*code)?$", re.I),
                       re.compile(r"^postal(\s*code)?$", re.I)]),
    ("country",      [re.compile(r"^country$", re.I)]),
    ("linkedin_url", [re.compile(r"linkedin", re.I)]),
    ("github_url",   [re.compile(r"github", re.I)]),
]

# Work authorization booleans
WORK_AUTH_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("us_work_authorized",          re.compile(r"authorized\s*to\s*work\s*in\s*us", re.I)),
    ("requires_sponsorship_now",    re.compile(r"requir(e|ing)\s*sponsorship", re.I)),
    ("willing_to_relocate",         re.compile(r"willing\s*to\s*relocate", re.I)),
    ("citizenships",                re.compile(r"citizen", re.I)),
]

# Salary / compensation (often LLM-assisted for "desired salary" but
# pattern-matched for "current salary" if user provides it)
COMPENSATION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("notice_period_weeks",  re.compile(r"notice\s*period", re.I)),
    ("min_salary_usd",       re.compile(r"(desired|expected|target)\s*salary", re.I)),
]

# Heuristic short-answer patterns — low LLM cost, high success rate
SHORT_ANSWER_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("eeoc_disability",    re.compile(r"(disability|disabled)", re.I)),
    ("eeoc_gender",        re.compile(r"(gender|sex)", re.I)),
    ("eeoc_race",          re.compile(r"(race|ethnicity)", re.I)),
    ("eeoc_veteran",       re.compile(r"(veteran|vet)", re.I)),
]

# Questions that are trivially answerable with yes/no
YES_NO_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(are\s*you\s*)?willing\s+to\s+travel", re.I),
    re.compile(r"^(are\s*you\s*)?authorized\s+to\s+work", re.I),
    re.compile(r"^(do\s*you\s*)?require\s+sponsorship", re.I),
    re.compile(r"^(are\s*you\s*)?a\s+veteran", re.I),
]

# Questions that are almost certainly cover-letter style and need LLM
COVER_LETTER_INDICATORS: list[re.Pattern] = [
    re.compile(r"why\s+(us|this\s+company|are\s+you\s+interested)", re.I),
    re.compile(r"describe\s+a\s+time", re.I),
    re.compile(r"tell\s+us\s+about\s+(a\s+)?your", re.I),
    re.compile(r"(greatest|biggest)\s+(strength|weakness)", re.I),
    re.compile(r"how\s+do\s+you\s+(handle|approach)", re.I),
    re.compile(r"scenario\s+(based|question)", re.I),
    re.compile(r"tell\s+me\s+about\s+a\s+time\s+when", re.I),
    re.compile(r"walk\s+me\s+through", re.I),
    re.compile(r"give\s+an\s+example", re.I),
    re.compile(r"what\s+is\s+your\s+(philosophy|approach|strategy)", re.I),
]


def classify_question(question_text: str) -> QuestionClassification:
    """
    Classify a single question into a source bucket.

    Returns confidence 1.0 if a strong pattern matched, 0.0 if no match.
    """
    q = question_text.strip()

    # Strong LLM signals — short-circuit immediately
    for pat in COVER_LETTER_INDICATORS:
        if pat.search(q):
            return QuestionClassification(source=AnswerSource.LLM, confidence=1.0)

    # Strong profile-field signals
    for field_key, patterns in IDENTITY_PATTERNS:
        for pat in patterns:
            if pat.match(q):
                return QuestionClassification(
                    source=AnswerSource.PROFILE,
                    confidence=1.0,
                    field_key=field_key,
                )

    # Work authorization booleans
    for field_key, pat in WORK_AUTH_PATTERNS:
        if pat.search(q):
            return QuestionClassification(
                source=AnswerSource.PROFILE,
                confidence=0.85,
                field_key=field_key,
            )

    # Compensation
    for field_key, pat in COMPENSATION_PATTERNS:
        if pat.search(q):
            return QuestionClassification(
                source=AnswerSource.PROFILE,
                confidence=0.8,
                field_key=field_key,
            )

    # Short answer / EEOC
    for field_key, pat in SHORT_ANSWER_PATTERNS:
        if pat.search(q):
            return QuestionClassification(
                source=AnswerSource.HEURISTIC,
                confidence=0.8,
                field_key=field_key,
            )

    # Yes/no patterns
    for pat in YES_NO_PATTERNS:
        if pat.match(q):
            return QuestionClassification(
                source=AnswerSource.HEURISTIC,
                confidence=0.7,
            )

    # Default — needs LLM
    return QuestionClassification(source=AnswerSource.LLM, confidence=0.0)


def classify_questions(questions: list[str]) -> list[QuestionClassification]:
    """Classify a list of questions."""
    return [classify_question(q) for q in questions]
