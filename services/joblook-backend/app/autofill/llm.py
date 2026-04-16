"""M4 — LLM tailoring for long-form autofill answers.

Wires the LLM call into the /api/extension/autofill pipeline.
Caches the frozen system prompt and per-user profile prefix via
Anthropic's prompt caching API. Each answer is saved to the
custom_answers table after generation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import anthropic
from sqlalchemy.orm import Session

from ..config import settings
from ..crypto import decrypt_column, unwrap_dek
from ..models import LlmCostLog, User
from ..schemas import Profile

# ── System prompt (cached for all LLM calls) ──────────────────────────────

SYSTEM_PROMPT = """You are JobLook, an AI assistant that helps job seekers write tailored answers to application questions.

Your task: Given the user's profile context and a job description, generate a high-quality, personalized answer to the specific question asked.

Rules:
- Write in the first person as the applicant.
- Be specific and concrete — cite skills, experiences, and outcomes where possible.
- Keep answers to 150–400 words unless the question asks for something shorter or longer.
- Do NOT lie, exaggerate, or invent specific numbers or company names not in the profile.
- If the job description mentions specific technologies, methodologies, or values, reference them.
- Match the tone of the question — professional for formal questions, conversational for startup roles.
- If you don't have enough context to give a good answer, say so briefly rather than hallucinating.
"""

# Profile prefix template — cacheable per-user
def profile_prefix(profile: Profile) -> str:
    parts = ["[User Profile]"]

    ident = profile.identity
    if ident.first_name or ident.last_name:
        parts.append(f"Name: {ident.first_name} {ident.last_name}".strip())
    if ident.email:
        parts.append(f"Email: {ident.email}")
    if ident.phone:
        parts.append(f"Phone: {ident.phone}")
    loc_parts = [p for p in [ident.city, ident.state, ident.country] if p]
    if loc_parts:
        parts.append(f"Location: {', '.join(loc_parts)}")
    if ident.linkedin_url:
        parts.append(f"LinkedIn: {ident.linkedin_url}")
    if ident.github_url:
        parts.append(f"GitHub: {ident.github_url}")

    if profile.experience:
        parts.append("\n[Work Experience]")
        for exp in profile.experience[:5]:  # Limit to 5 most recent
            dates = ""
            if exp.start_date:
                dates = f" ({exp.start_date.strftime('%Y-%m')}"
                if exp.is_current:
                    dates += " – Present"
                elif exp.end_date:
                    dates += f" – {exp.end_date.strftime('%Y-%m')}"
                dates += ")"
            parts.append(f"- {exp.title} at {exp.company}{dates}")
            if exp.location:
                parts.append(f"  Location: {exp.location}")
            if exp.summary:
                parts.append(f"  Summary: {exp.summary}")
            if exp.bullets:
                for b in exp.bullets[:4]:
                    parts.append(f"  • {b}")

    if profile.education:
        parts.append("\n[Education]")
        for edu in profile.education[:3]:
            dates = ""
            if edu.start_date:
                dates = f" ({edu.start_date.strftime('%Y')}"
                if edu.end_date:
                    dates += f" – {edu.end_date.strftime('%Y')}"
                dates += ")"
            parts.append(f"- {edu.degree} in {edu.field_of_study} at {edu.school}{dates}")
            if edu.honors:
                parts.append(f"  Honors: {edu.honors}")

    if profile.skills:
        skill_names = [s.name for s in profile.skills][:30]
        parts.append(f"\n[Top Skills] {', '.join(skill_names)}")

    if profile.summary:
        parts.append(f"\n[Professional Summary]\n{profile.summary}")

    return "\n".join(parts)


# ── Per-call prompt ─────────────────────────────────────────────────────────

def build_prompt(profile: Profile, job_context: str, question: str) -> str:
    return f"""{profile_prefix(profile)}

[Job Description]
{job_context[:8000]}

[Question to Answer]
{question}

Write a tailored answer:"""


# ── Cost estimation ─────────────────────────────────────────────────────────

_PRICE_CENTS_PER_1M = {
    "claude-opus-4-6":   {"input": 500,  "output": 2500},
    "claude-sonnet-4-6": {"input": 300,  "output": 1500},
    "claude-haiku-4-5":  {"input": 100,  "output":  500},
}


def _cost_cents(model: str, input_toks: int, output_toks: int) -> int:
    p = _PRICE_CENTS_PER_1M.get(model, {"input": 300, "output": 1500})
    return round((p["input"] * input_toks + p["output"] * output_toks) / 1_000_000)


# ── LLM call ───────────────────────────────────────────────────────────────

@dataclass
class LlmAnswer:
    answer: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_cents: int


def generate_answer(
    profile: Profile,
    question: str,
    job_description: str = "",
    job_context_hash: str = "",
) -> LlmAnswer:
    """
    Generate a tailored answer using Anthropic's Messages API with prompt caching.

    The system prompt and profile prefix are sent with cache_control=max, meaning
    Anthropic caches them. Subsequent identical calls hit the cache for those
    tokens at a 90% discount.
    """
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = build_prompt(profile, job_description, question)

    # Use cached (system) + uncached (question) messages structure
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            },
        ],
    )

    # Extract answer text
    answer = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            answer += getattr(block, "text", "")

    if not answer.strip():
        answer = "[The AI was unable to generate an answer for this question.]"

    usage = response.usage
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0

    return LlmAnswer(
        answer=answer.strip(),
        model=response.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cost_cents=_cost_cents(response.model, input_tokens, output_tokens),
    )


def log_llm_cost(
    db: Session,
    user_id: str,
    endpoint: str,
    result: LlmAnswer,
) -> None:
    db.add(
        LlmCostLog(
            user_id=user_id,
            endpoint=endpoint,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cache_read_tokens=result.cache_read_tokens,
            cost_cents=result.cost_cents,
        )
    )
