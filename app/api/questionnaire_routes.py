"""Questionnaire API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.questionnaire_models import QuestionnaireResponse, QuestionnaireSubmission, BusinessProfile
from app.services.questionnaire_service import QuestionnaireService, QuestionnaireServiceError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["questionnaire"])


def get_questionnaire_service() -> QuestionnaireService:
    """Dependency provider for QuestionnaireService."""
    return QuestionnaireService()


@router.get(
    "/questionnaire",
    response_model=QuestionnaireResponse,
    status_code=status.HTTP_200_OK,
    summary="Get questionnaire configuration",
)
async def get_questionnaire(
    service: QuestionnaireService = Depends(get_questionnaire_service),
) -> QuestionnaireResponse:
    """Retrieve the generated structured questionnaire."""
    logger.info("Received request for questionnaire configuration.")
    try:
        questions = service.get_questions()
        return QuestionnaireResponse(questions=questions)
    except QuestionnaireServiceError as exc:
        logger.error("Failed to retrieve questionnaire: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/questionnaire/submit",
    response_model=BusinessProfile,
    status_code=status.HTTP_200_OK,
    summary="Submit answers and build profile",
)
async def submit_questionnaire(
    submission: QuestionnaireSubmission,
    service: QuestionnaireService = Depends(get_questionnaire_service),
) -> BusinessProfile:
    """Submit questionnaire answers to build a business profile."""
    logger.info("Received questionnaire submission with %d answers.", len(submission.answers))
    
    try:
        profile = service.build_business_profile(submission)
        return profile
    except QuestionnaireServiceError as exc:
        logger.warning("Validation failed for questionnaire submission: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error processing questionnaire submission.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process submission.",
        ) from exc
