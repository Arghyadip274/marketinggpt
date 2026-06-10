"""LangGraph orchestration engine for the marketing pipeline."""

import logging
from typing import Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

# Import the pre-configured tools
from app.chains.tools import (
    process_questionnaire_tool,
    analyze_website_tool,
    analyze_competitors_tool,
    analyze_industry_tool,
    analyze_keywords_tool,
    analyze_trends_tool,
    generate_master_strategy_tool,
)
from app.rag.retriever import KnowledgeRetriever
from app.prompts.personality_manager import PersonalityManager
import os

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# 1. Define the Global State
class MarketingState(TypedDict, total=False):
    """The graph state representing the lifecycle of a marketing analysis."""
    
    # Core Inputs
    questionnaire_answers: list[dict[str, str]]
    website_url: str
    competitors: list[str]
    target_keywords: list[str]
    
    # Intermediary Analysis Payloads
    business_profile: dict[str, Any]
    website_data: dict[str, Any]
    competitor_data: dict[str, Any]
    industry_data: dict[str, Any]
    ranked_keywords: list[dict[str, Any]]
    trend_data: dict[str, Any]
    
    # Conversation History
    chat_history: list[Any]
    active_persona: str
    
    # RAG Context
    rag_context: list[str]
    
    # Final Output
    marketing_strategy: dict[str, Any]


# 2. Node Implementations
def node_process_questionnaire(state: MarketingState) -> MarketingState:
    logger.info("[Node] Processing questionnaire.")
    if "questionnaire_answers" in state:
        try:
            profile = process_questionnaire_tool.invoke({"answers": state["questionnaire_answers"]})
            state["business_profile"] = profile
        except Exception as e:
            logger.warning(f"Failed to process questionnaire (likely missing required fields): {e}. Falling back to default profile.")
            # Build a mock profile from the raw answers if validation fails
            mock_data = {ans.get("question", "Unknown"): ans.get("answer", "") for ans in state["questionnaire_answers"]}
            state["business_profile"] = {"profile_data": mock_data}
    return state


def node_analyze_website(state: MarketingState) -> MarketingState:
    logger.info("[Node] Analyzing website.")
    if "website_url" in state:
        data = analyze_website_tool.invoke({"url": state["website_url"]})
        state["website_data"] = data
    return state


def node_analyze_competitors(state: MarketingState) -> MarketingState:
    logger.info("[Node] Analyzing competitors.")
    if "competitors" in state:
        data = analyze_competitors_tool.invoke({"urls": state["competitors"]})
        state["competitor_data"] = data
    return state


def node_analyze_industry(state: MarketingState) -> MarketingState:
    logger.info("[Node] Analyzing industry patterns.")
    # Extract an industry hint from the generated profile if available
    industry_hint = "generic"
    if "business_profile" in state:
        profile_text = str(state["business_profile"]).lower()
        for ind in ["saas", "ecommerce", "real estate", "healthcare", "finance"]:
            if ind in profile_text:
                industry_hint = ind
                break
    
    data = analyze_industry_tool.invoke({"industry_name": industry_hint})
    state["industry_data"] = data
    return state


def node_analyze_keywords(state: MarketingState) -> MarketingState:
    logger.info("[Node] Analyzing and ranking keywords.")
    if "target_keywords" in state:
        # Construct mock keyword dicts for the backend tool
        kw_dicts = [
            {
                "keyword": kw,
                "search_volume": 1000,
                "difficulty": 50,
                "cpc": 1.0,
                "trend_growth": 10,
                "intent_score": 80
            }
            for kw in state["target_keywords"]
        ]
        data = analyze_keywords_tool.invoke({"keywords_data": kw_dicts})
        state["ranked_keywords"] = data
    return state


def node_analyze_trends(state: MarketingState) -> MarketingState:
    logger.info("[Node] Analyzing keyword trends.")
    if "target_keywords" in state:
        data = analyze_trends_tool.invoke({"keywords": state["target_keywords"]})
        state["trend_data"] = data
    return state


def node_retrieve_context(state: MarketingState) -> MarketingState:
    logger.info("[Node] Retrieving semantic RAG context.")
    retriever = KnowledgeRetriever()
    query = state.get("website_url", "Marketing strategy context")
    context = retriever.retrieve_context(query)
    state["rag_context"] = context
    return state


def node_generate_strategy(state: MarketingState) -> MarketingState:
    logger.info("[Node] Generating final master strategy.")
    
    # 1. Try Live Gemini LLM Integration
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key and all(k in state for k in ["business_profile", "website_url", "competitors", "target_keywords"]):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            logger.info("Google API Key detected. Engaging Gemini Live Generation!")
            llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=api_key)
            
            persona_name = state.get("active_persona", "COMMIT (The Friendly Expert)")
            manager = PersonalityManager(persona_name)
            prompt_template = manager.get_strategy_prompt_template()
            
            rag_context = "\n".join(state.get("rag_context", []))
            business_profile_str = str(state["business_profile"].get("profile_data", {}))
            keyword_data_str = str(state.get("ranked_keywords", state["target_keywords"]))
            competitor_data_str = str(state.get("competitor_data", state["competitors"]))
            
            chain = prompt_template | llm
            response = chain.invoke({
                "business_profile": business_profile_str,
                "keyword_data": keyword_data_str,
                "competitor_data": competitor_data_str,
                "rag_context": rag_context,
                "chat_history": state.get("chat_history", [])
            })
            
            strategy_content = response.content
            if isinstance(strategy_content, list):
                # Langchain might return a list of content blocks for newer models
                strategy_content = "".join(block.get("text", "") for block in strategy_content if isinstance(block, dict))
                
            state["marketing_strategy"] = strategy_content
            return state
            
        except Exception as e:
            logger.error("Gemini generation failed: %s", e)
            raise ValueError(f"Gemini API Error: {str(e)}. Please check your API key and try again.") from e
            
    # 2. Fallback to Mock Strategy Generator (only runs if no API key is provided)
    logger.info("No API Key detected. Falling back to structured mock data.")
    if all(k in state for k in ["business_profile", "website_url", "competitors", "target_keywords"]):
        data = generate_master_strategy_tool.invoke({
            "business_profile_data": state["business_profile"].get("profile_data", {}),
            "website_url": state["website_url"],
            "competitor_urls": state["competitors"],
            "keywords": state["target_keywords"]
        })
        
        if "rag_context" in state and state["rag_context"]:
            rag_info = " | RAG Context: " + ", ".join(state["rag_context"])
            data["business_summary"] += rag_info
            
        state["marketing_strategy"] = data
    return state


# 3. Assemble Graph
def build_marketing_graph():
    """Build and compile the LangGraph state machine."""
    logger.info("Assembling LangGraph workflow.")
    
    workflow = StateGraph(MarketingState)

    # Add Nodes
    workflow.add_node("questionnaire", node_process_questionnaire)
    workflow.add_node("website", node_analyze_website)
    workflow.add_node("competitors", node_analyze_competitors)
    workflow.add_node("industry", node_analyze_industry)
    workflow.add_node("keywords", node_analyze_keywords)
    workflow.add_node("trends", node_analyze_trends)
    workflow.add_node("rag", node_retrieve_context)
    workflow.add_node("strategy", node_generate_strategy)

    # Add Edges (Linear sequential flow for now)
    workflow.add_edge(START, "questionnaire")
    workflow.add_edge("questionnaire", "website")
    workflow.add_edge("website", "competitors")
    workflow.add_edge("competitors", "industry")
    workflow.add_edge("industry", "keywords")
    workflow.add_edge("keywords", "trends")
    workflow.add_edge("trends", "rag")
    workflow.add_edge("rag", "strategy")
    workflow.add_edge("strategy", END)

    # Compile
    return workflow.compile()
