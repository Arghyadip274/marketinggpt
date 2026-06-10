import os
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.workflows.marketing_workflow import build_marketing_graph
from app.agents.extractor import extract_company_info
from app.prompts.personality_manager import PersonalityManager
from langchain_google_genai import ChatGoogleGenerativeAI

router = APIRouter()

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    active_persona: str

class ChatResponse(BaseModel):
    reply: str
    workflow_completed: bool

@router.get("/api/personas")
async def get_personas():
    """Return available personas and their greetings."""
    manager = PersonalityManager()
    personalities = manager.personalities
    
    options = []
    for name, data in personalities.items():
        options.append({
            "name": name,
            "greeting": data.get("greeting", "Hello!")
        })
    return {"personas": options}

@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_messages = request.messages
    active_persona = request.active_persona
    
    if not user_messages:
        raise HTTPException(status_code=400, detail="No messages provided.")
        
    user_input = user_messages[-1].get("content", "")
    
    # Build LangChain compatible chat history
    chat_history = []
    for msg in user_messages[:-1]:
        role = "user" if msg["role"] == "user" else "assistant"
        chat_history.append((role, msg["content"]))
        
    try:
        extraction = extract_company_info(chat_history, user_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
        
    if not extraction.is_complete:
        question = extraction.missing_info_question or "Could you clarify your brand name or website?"
        return ChatResponse(reply=question, workflow_completed=False)
        
    # We have all info, compile graph and run
    graph = build_marketing_graph()
    
    mock_input = {
        "questionnaire_answers": [{"question": "User Profile Description", "answer": user_input}],
        "website_url": extraction.website_url or "https://example.com",
        "competitors": extraction.competitors or [],
        "target_keywords": extraction.target_keywords or [],
        "chat_history": chat_history,
        "active_persona": active_persona
    }
    
    try:
        # Note: LangGraph might take a while, this is synchronous for prototype parity.
        final_state = graph.invoke(mock_input)
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Google API Key missing.")
            
        llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=api_key)
        
        manager = PersonalityManager(active_persona)
        prompt_template = manager.get_strategy_prompt_template()
        
        rag_context = "\n".join(final_state.get("rag_context", []))
        business_profile_str = str(final_state.get("business_profile", {}).get("profile_data", {}))
        keyword_data_str = str(final_state.get("ranked_keywords", final_state.get("target_keywords")))
        competitor_data_str = str(final_state.get("competitor_data", final_state.get("competitors")))
        
        chain = prompt_template | llm
        response = chain.invoke({
            "business_profile": business_profile_str,
            "keyword_data": keyword_data_str,
            "competitor_data": competitor_data_str,
            "rag_context": rag_context,
            "chat_history": chat_history + [("user", user_input)]
        })
        
        reply = response.content
        if isinstance(reply, list):
            reply = "".join(b.get("text", "") for b in reply if isinstance(b, dict))
            
        return ChatResponse(reply=reply, workflow_completed=True)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")
