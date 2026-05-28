"""Pydantic models for the questionnaire pipeline."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class QuestionModel(BaseModel):
    """Schema for a single question configuration."""
    category: str
    question: str
    required: bool
    input_type: str = Field(pattern="^(text|email|url)$")


class QuestionnaireResponse(BaseModel):
    """Response payload containing all configured questions."""
    questions: list[QuestionModel]


class AnswerModel(BaseModel):
    """Schema for a single submitted answer."""
    question: str
    answer: str


class QuestionnaireSubmission(BaseModel):
    """Request payload containing user answers."""
    answers: list[AnswerModel]


class BusinessProfile(BaseModel):
    """Structured business profile generated from answers."""
    profile_data: dict[str, str]
    # Optionally, we can strongly type fields if we know them, 
    # but since it's dynamic based on the questionnaire, a dict is safest.
