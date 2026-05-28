"""Service layer for the questionnaire onboarding pipeline."""

import json
import logging
from pathlib import Path

from app.models.questionnaire_models import (
    QuestionModel,
    QuestionnaireSubmission,
    BusinessProfile,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class QuestionnaireServiceError(Exception):
    """Base exception for questionnaire service failures."""


class QuestionnaireService:
    """Handles business logic for fetching questions and validating submissions."""

    def __init__(self, config_path: str | None = None) -> None:
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).parent.parent / "config" / "marketing_questions.json"
        
        self._questions: list[QuestionModel] = []
        self._load_questions()

    def _load_questions(self) -> None:
        """Load and parse the JSON configuration into Pydantic models."""
        try:
            if not self.config_path.exists():
                logger.error("Questionnaire config not found at %s", self.config_path)
                raise QuestionnaireServiceError(f"Configuration file missing: {self.config_path}")

            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._questions = [QuestionModel(**q) for q in data]
            logger.info("Successfully loaded %d questions.", len(self._questions))
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON configuration: %s", exc)
            raise QuestionnaireServiceError("Invalid JSON configuration") from exc
        except Exception as exc:
            logger.exception("Unexpected error loading questions")
            raise QuestionnaireServiceError("Failed to load questionnaire configuration") from exc

    def get_questions(self) -> list[QuestionModel]:
        """Return the loaded questions."""
        return self._questions

    def validate_answers(self, submission: QuestionnaireSubmission) -> None:
        """Validate that all required questions have been answered.
        
        Args:
            submission: The user's submitted answers.
            
        Raises:
            QuestionnaireServiceError: If required answers are missing.
        """
        submitted_questions = {ans.question.strip().lower() for ans in submission.answers}
        missing = []

        for q in self._questions:
            if q.required:
                if q.question.strip().lower() not in submitted_questions:
                    missing.append(q.question)

        if missing:
            logger.warning("Submission missing %d required answers.", len(missing))
            raise QuestionnaireServiceError(f"Missing required answers for: {', '.join(missing[:3])}...")

        logger.info("Successfully validated questionnaire submission.")

    def build_business_profile(self, submission: QuestionnaireSubmission) -> BusinessProfile:
        """Convert a validated submission into a structured business profile.
        
        Args:
            submission: The user's submitted answers.
            
        Returns:
            A BusinessProfile instance.
        """
        self.validate_answers(submission)
        
        profile_data = {ans.question: ans.answer for ans in submission.answers}
        logger.info("Built business profile with %d data points.", len(profile_data))
        
        return BusinessProfile(profile_data=profile_data)
