"""Personality Manager for MarketingGPT.

Loads system prompts from disk and manages context injection for LangChain templates.
"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from app.prompts.consultant_prompt import create_strategy_prompt, create_general_qa_prompt

logger = logging.getLogger(__name__)


class PersonalityManager:
    """Manages the MarketingGPT personality system."""

    def __init__(self, system_prompt_path: str | None = None):
        """Initialize the PersonalityManager.
        
        Args:
            system_prompt_path: Optional path to the system_prompt.md file.
        """
        if system_prompt_path:
            self.system_prompt_path = Path(system_prompt_path)
        else:
            self.system_prompt_path = Path(__file__).parent / "system_prompt.md"
            
        self.system_prompt_content = self._load_system_prompt()
        logger.info("PersonalityManager successfully initialized.")

    def _load_system_prompt(self) -> str:
        """Load the markdown system prompt from disk."""
        try:
            if self.system_prompt_path.exists():
                content = self.system_prompt_path.read_text(encoding="utf-8")
                logger.debug("System prompt loaded from %s", self.system_prompt_path)
                return content
            else:
                logger.warning("System prompt file not found at %s. Using default fallback.", self.system_prompt_path)
                return "You are MarketingGPT, an elite Senior Marketing Consultant."
        except Exception as e:
            logger.error("Failed to load system prompt: %s", e)
            return "You are MarketingGPT, an elite Senior Marketing Consultant."

    def build_strategy_prompt_string(self, **kwargs: Any) -> str:
        """Build a fully formatted strategy prompt string.
        
        This method formats the LangChain template into a single string.
        Useful for raw LLM API calls or logging.
        """
        template = create_strategy_prompt()
        kwargs["system_prompt"] = self.system_prompt_content
        
        try:
            return template.format(**kwargs)
        except Exception as e:
            logger.error("Failed to format strategy prompt string: %s", e)
            raise ValueError(f"Prompt formatting error: {e}") from e

    def get_strategy_prompt_template(self) -> ChatPromptTemplate:
        """Return the LangChain ChatPromptTemplate with system_prompt pre-injected.
        
        This returns a template ready to be used in an LCEL chain.
        """
        template = create_strategy_prompt()
        return template.partial(system_prompt=self.system_prompt_content)

    def get_qa_prompt_template(self) -> ChatPromptTemplate:
        """Return the LangChain ChatPromptTemplate for Q&A with system_prompt pre-injected."""
        template = create_general_qa_prompt()
        return template.partial(system_prompt=self.system_prompt_content)
