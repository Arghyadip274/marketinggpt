import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)

class CompanyExtraction(BaseModel):
    is_complete: bool = Field(description="True if website_url, competitors, and target_keywords could be deduced or generated. False if the user's prompt is too vague to guess their company/brand.")
    missing_info_question: Optional[str] = Field(description="If is_complete is False, write a question to ask the user to clarify their brand name or product.")
    website_url: Optional[str] = Field(description="The deduced primary website URL (e.g., https://www.nike.com).")
    competitors: Optional[List[str]] = Field(description="List of 2-3 competitor website URLs.")
    target_keywords: Optional[List[str]] = Field(description="List of 2-3 target SEO keywords for the product.")


def extract_company_info(chat_history: list, current_input: str) -> CompanyExtraction:
    """Extracts company information from the user's prompt using an LLM."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing. Cannot extract company info.")
        
    # We use gemini-3.1-flash-lite as requested
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=api_key)
    structured_llm = llm.with_structured_output(CompanyExtraction)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an intelligent data extraction agent. The user is asking for a marketing strategy. Your goal is to deduce their company's website URL, identify 2-3 top competitors (their URLs), and suggest 2-3 SEO target keywords based on their prompt. If their prompt is incredibly vague (e.g., 'I sell shoes') and you cannot guess the brand name, set is_complete to False and ask them for the brand name. If they provide a brand name (e.g., 'Parle G' or 'Colgate'), deduce their official website URL."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    chain = prompt | structured_llm
    
    logger.info("Executing extraction agent...")
    result = chain.invoke({
        "chat_history": chat_history,
        "input": current_input
    })
    
    return result
