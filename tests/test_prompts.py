"""Unit tests for the MarketingGPT personality system."""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from app.prompts.personality_manager import PersonalityManager
from langchain_core.prompts import ChatPromptTemplate


def test_personality_manager_loads_default_prompt():
    """Test that the PersonalityManager correctly loads the default system prompt."""
    manager = PersonalityManager()
    assert "Senior Marketing Consultant" in manager.get_system_prompt()
    assert "## Role & Persona" in manager.get_system_prompt()


def test_personality_manager_fallback(tmp_path):
    """Test the fallback mechanism when the active_persona is missing."""
    manager = PersonalityManager(active_persona="UnknownPersona")
    # It should fallback to the old markdown file or the fallback string
    # Assuming fallback to "You are MarketingGPT, an elite Senior Marketing Consultant." or the markdown contents
    prompt = manager.get_system_prompt()
    assert "Senior Marketing Consultant" in prompt or "You are MarketingGPT" in prompt


def test_build_strategy_prompt_string():
    """Test formatting the strategy prompt string with dynamic context."""
    manager = PersonalityManager()
    
    formatted_prompt = manager.build_strategy_prompt_string(
        business_profile='{"name": "TechCorp"}',
        keyword_data="[SEO, Growth]",
        competitor_data="FastCompany, InnovateTech",
        rag_context="Recent trends show 50% increase in inbound."
    )
    
    assert "TechCorp" in formatted_prompt
    assert "[SEO, Growth]" in formatted_prompt
    assert "FastCompany" in formatted_prompt
    assert "Recent trends show 50% increase" in formatted_prompt
    assert "Senior Marketing Consultant" in formatted_prompt


def test_get_strategy_prompt_template():
    """Test retrieving a partial ChatPromptTemplate for LCEL chains."""
    manager = PersonalityManager()
    template = manager.get_strategy_prompt_template()
    
    assert isinstance(template, ChatPromptTemplate)
    # The system_prompt should already be partially bound
    assert "system_prompt" not in template.input_variables
    assert "business_profile" in template.input_variables
    assert "keyword_data" in template.input_variables
    
    # Format the messages to verify injection
    messages = template.format_messages(
        business_profile="Test Business",
        keyword_data="Test Keywords",
        competitor_data="Test Competitors",
        rag_context="Test Context"
    )
    
    assert len(messages) == 2
    assert "Senior Marketing Consultant" in messages[0].content
    assert "Test Business" in messages[1].content


def test_get_qa_prompt_template():
    """Test retrieving the Q&A partial ChatPromptTemplate."""
    manager = PersonalityManager()
    template = manager.get_qa_prompt_template()
    
    assert isinstance(template, ChatPromptTemplate)
    assert "user_query" in template.input_variables
    assert "rag_context" in template.input_variables
    
    messages = template.format_messages(
        user_query="How to improve SEO?",
        rag_context="Backlinks are critical."
    )
    
    assert len(messages) == 2
    assert "Senior Marketing Consultant" in messages[0].content
    assert "How to improve SEO?" in messages[1].content
    assert "Backlinks are critical." in messages[1].content
