"""Resume → canonical Profile via Anthropic structured output.

Two steps:
  1. Extract raw text from a PDF or DOCX file.
  2. One Claude call with the Profile JSON schema as `output_config.format`,
     validated through Pydantic.

Cost is logged via `record_cost` so it shows up in `llm_cost_log`.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from anthropic import Anthropic
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .config import settings
from .models import LlmCostLog, User
from .schemas import Profile

SYSTEM_PROMPT = (
    "You extract structured data from resumes. You will be given the raw text "
    "of a resume and must return a JSON object that conforms exactly to the "
    "provided Profile schema. Rules:\n"
    "- Never invent data. If a field is not present in the resume, omit it or leave it empty.\n"
    "- Dates use ISO format (YYYY-MM-DD); use the first of the month when day is unknown.\n"
    "- 'is_current' is true only when the resume explicitly says 'present', 'current', or similar.\n"
    "- Do not populate `demographics` or `custom_answers` — those are user-provided.\n"
    "- Skills should be deduped and lowercased.\n"
)

# Per-1M token prices for cost estimation (USD). Keep in sync with shared/models.md.
_PRICE_TABLE_CENTS = {
    "claude-opus-4-6":   {"input": 500,  "output": 2500},  # $5 / $25 per 1M
    "claude-sonnet-4-6": {"input": 300,  "output": 1500},  # $3 / $15 per 1M
    "claude-haiku-4-5":  {"input": 100,  "output":  500},  # $1 / $5  per 1M
}


@dataclass
class ParseResult:
    profile: Profile
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_cents: int


# ---------- text extraction ----------

def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported resume format: {filename}")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document  # python-docx

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()


# ---------- LLM extraction ----------

def parse_resume(text: str) -> ParseResult:
    if not text.strip():
        raise ValueError("Resume text is empty")

    client = Anthropic(api_key=settings.anthropic_api_key)
    schema = Profile.model_json_schema()

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Resume:\n\n{text}"}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )

    raw = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    try:
        profile = Profile.model_validate_json(raw)
    except ValidationError as e:
        raise ValueError(f"LLM returned invalid Profile JSON: {e}") from e

    usage = response.usage
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost_cents = _estimate_cost_cents(response.model, input_tokens, output_tokens)

    return ParseResult(
        profile=profile,
        model=response.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cost_cents=cost_cents,
    )


def _estimate_cost_cents(model: str, input_tokens: int, output_tokens: int) -> int:
    price = _PRICE_TABLE_CENTS.get(model)
    if not price:
        return 0
    # cents per 1M tokens × tokens / 1M, scaled to integer cents
    return round((price["input"] * input_tokens + price["output"] * output_tokens) / 1_000_000)


def record_cost(db: Session, user: User, result: ParseResult, endpoint: str = "resume_parse") -> None:
    db.add(
        LlmCostLog(
            user_id=user.id,
            endpoint=endpoint,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cache_read_tokens=result.cache_read_tokens,
            cost_cents=result.cost_cents,
        )
    )
