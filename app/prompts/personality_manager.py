"""Personality Manager for MarketingGPT.

Loads system prompts from disk and manages context injection for LangChain templates.
"""

import logging
import json
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from app.prompts.consultant_prompt import create_strategy_prompt, create_general_qa_prompt

logger = logging.getLogger(__name__)


class PersonalityManager:
    """Manages the persona and tone of the MarketingGPT assistant."""
    
    def __init__(self, active_persona: str = "COMMIT (The Friendly Expert)"):
        self.active_persona = active_persona
        self.personalities_file = Path(__file__).parent / "personalities.json"
        self.personalities = self._load_personalities()
        logger.info(f"PersonalityManager successfully initialized with {active_persona}.")

    def _load_personalities(self) -> dict:
        if self.personalities_file.exists():
            with open(self.personalities_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_system_prompt(self) -> str:
        """Returns the system prompt for the currently active persona."""
        persona_data = self.personalities.get(self.active_persona)
        if persona_data and "system_prompt" in persona_data:
            return persona_data["system_prompt"]
        
        # Fallback to the old markdown file if JSON fails
        prompt_file = Path(__file__).parent / "system_prompt.md"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()
        return "You are MarketingGPT, an elite Senior Marketing Consultant."

    def get_greeting(self) -> str:
        """Returns the initial greeting message for the active persona."""
        persona_data = self.personalities.get(self.active_persona)
        if persona_data and "greeting" in persona_data:
            return persona_data["greeting"]
        return "Hello! Please describe your business."

    def build_strategy_prompt_string(self, **kwargs: Any) -> str:
        """Build a fully formatted strategy prompt string.
        
        This method formats the LangChain template into a single string.
        Useful for raw LLM API calls or logging.
        """
        template = create_strategy_prompt()
        kwargs["system_prompt"] = self.get_system_prompt()
        
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
        return template.partial(system_prompt=self.get_system_prompt())

    def get_qa_prompt_template(self) -> ChatPromptTemplate:
        """Return the LangChain ChatPromptTemplate for Q&A with system_prompt pre-injected."""
        template = create_general_qa_prompt()
        return template.partial(system_prompt=self.get_system_prompt())
