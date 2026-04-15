from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class Identity(BaseModel):
    first_name: str = ""
    last_name: str = ""
    preferred_name: str = ""
    email: Optional[EmailStr] = None
    phone: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None
    pronouns: str = ""


class WorkAuthorization(BaseModel):
    us_work_authorized: Optional[bool] = None
    requires_sponsorship_now: Optional[bool] = None
    requires_sponsorship_future: Optional[bool] = None
    visa_status: str = ""
    citizenships: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: str
    title: str
    location: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    school: str
    degree: str = ""
    field_of_study: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    gpa: Optional[float] = None
    honors: str = ""


class Skill(BaseModel):
    name: str
    years: Optional[float] = None
    level: Optional[Literal["beginner", "intermediate", "advanced", "expert"]] = None


class Preferences(BaseModel):
    desired_titles: list[str] = Field(default_factory=list)
    desired_locations: list[str] = Field(default_factory=list)
    remote_preference: Optional[Literal["remote", "hybrid", "onsite", "any"]] = None
    willing_to_relocate: Optional[bool] = None
    min_salary_usd: Optional[int] = None
    earliest_start_date: Optional[date] = None
    notice_period_weeks: Optional[int] = None


class Demographics(BaseModel):
    """EEO/voluntary self-identification. All optional; user may decline."""

    gender: str = ""
    race_ethnicity: list[str] = Field(default_factory=list)
    veteran_status: str = ""
    disability_status: str = ""
    lgbtq: str = ""


class CustomAnswer(BaseModel):
    question: str
    answer: str
    question_hash: str
    source: Literal["user", "llm"] = "user"
    job_context_hash: str = ""


class Profile(BaseModel):
    identity: Identity = Field(default_factory=Identity)
    work_authorization: WorkAuthorization = Field(default_factory=WorkAuthorization)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    demographics: Demographics = Field(default_factory=Demographics)
    summary: str = ""
    custom_answers: list[CustomAnswer] = Field(default_factory=list)
