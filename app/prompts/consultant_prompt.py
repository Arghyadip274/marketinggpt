"""LangChain prompt templates for the Consultant persona."""

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

STRATEGY_HUMAN_TEMPLATE = """
Please generate a comprehensive marketing strategy based on the following intelligence:

### Business Profile
{business_profile}

### Target Keywords & SEO Data
{keyword_data}

### Competitor Analysis
{competitor_data}

### Relevant Marketing Knowledge (RAG Context)
{rag_context}

Based on your expertise as a Senior Marketing Consultant, provide a detailed action plan and strategic recommendations. Remember to explain your reasoning clearly and structure your output for readability.
"""

def create_strategy_prompt() -> ChatPromptTemplate:
    """Create a LangChain ChatPromptTemplate for strategy generation.
    
    The `{system_prompt}` variable must be injected at runtime by the PersonalityManager.
    """
    system_msg = SystemMessagePromptTemplate.from_template("{system_prompt}")
    human_msg = HumanMessagePromptTemplate.from_template(STRATEGY_HUMAN_TEMPLATE)
    
    return ChatPromptTemplate.from_messages([
        system_msg,
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        human_msg
    ])

def create_general_qa_prompt() -> ChatPromptTemplate:
    """Create a general Q&A prompt template for the consultant."""
    system_msg = SystemMessagePromptTemplate.from_template("{system_prompt}")
    human_msg = HumanMessagePromptTemplate.from_template("User Query: {user_query}\n\nRAG Context: {rag_context}\n\nProvide your strategic advice:")
    
    return ChatPromptTemplate.from_messages([system_msg, human_msg])
