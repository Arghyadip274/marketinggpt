import streamlit as st
import time
import json
import os
from app.workflows.marketing_workflow import build_marketing_graph
from app.agents.extractor import extract_company_info

# Configure page
st.set_page_config(page_title="MarketingGPT Prototype", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

st.title("🤖 MarketingGPT Prototype")
st.markdown("Welcome to the entry-level frontend for MarketingGPT. Describe your business in the chat below to generate a strategy.")

# --- INJECT PREMIUM CSS ---
css_path = os.path.join(os.path.dirname(__file__), "app", "static", "styles.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- CONFIGURATION ---
import os
from dotenv import load_dotenv
load_dotenv(override=True) # Load the API key from a .env file and override old env vars

# Forcefully bypass Windows environment caching by reading the .env file directly
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("GOOGLE_API_KEY="):
                os.environ["GOOGLE_API_KEY"] = line.split("=")[1].strip().strip('"').strip("'")
# -------------------------------

# --- SIDEBAR PERSONALITY SELECTOR ---
from app.prompts.personality_manager import PersonalityManager
st.sidebar.header("🎭 Choose Persona")

# Dynamically load personas directly from personalities.json using absolute path
json_path = os.path.join(os.path.dirname(__file__), "app", "prompts", "personalities.json")
persona_options = []
if os.path.exists(json_path):
    try:
        import json
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            persona_options = list(data.keys())
    except Exception as e:
        st.sidebar.error(f"Error loading personalities: {e}")

if not persona_options:
    persona_options = [
        "COMMIT (The Friendly Expert)",
        "MarketingGPT (The Original)",
        "Steve (The Visionary)",
        "DataDan (The Analytical Quant)",
        "SavageSales (The Aggressive Closer)"
    ]

# Track persona changes to reset chat
if "active_persona" not in st.session_state:
    st.session_state.active_persona = persona_options[0]

try:
    default_idx = persona_options.index(st.session_state.active_persona)
except ValueError:
    default_idx = 0
    st.session_state.active_persona = persona_options[0]

selected_persona = st.sidebar.selectbox("Active Persona", persona_options, index=default_idx)

if selected_persona != st.session_state.active_persona:
    st.session_state.active_persona = selected_persona
    st.session_state.workflow_completed = False
    # Clear messages on persona change
    st.session_state.messages = []

# 2. Chat Interface Initialization
if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    manager = PersonalityManager(st.session_state.active_persona)
    st.session_state.messages = [
        {"role": "assistant", "content": manager.get_greeting()}
    ]

# Keep track of whether the heavy analysis is done
if "workflow_completed" not in st.session_state:
    st.session_state.workflow_completed = False

# Display historical chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. Chat Input and Workflow Execution
if user_input := st.chat_input("E.g., My product is Parle G..."):
    # Append and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Extract chat history excluding the most recent message
    chat_history = [(msg["role"], msg["content"]) for msg in st.session_state.messages[:-1]]

    with st.chat_message("assistant"):
        
        # If the heavy analysis is already done, we should just do a normal chat response.
        # But for this prototype, if workflow_completed is true, we just route it through the workflow again 
        # (the workflow will just use the new chat history to answer the question quickly using Gemini).
        # Actually, let's keep it simple: the workflow already has memory!
        # If we re-run the workflow, it re-scrapes everything.
        # So instead, let's just use the extractor to decide if we have enough info!
        
        status_placeholder = st.empty()
        
        if not st.session_state.workflow_completed:
            with st.spinner("Analyzing your prompt to extract company info..."):
                try:
                    extraction = extract_company_info(chat_history, user_input)
                except Exception as e:
                    st.error(f"Extraction failed: {e}")
                    st.stop()
            
            if not extraction.is_complete:
                # We are missing info! Ask the user.
                question = extraction.missing_info_question or "Could you clarify your brand name or website?"
                st.markdown(question)
                st.session_state.messages.append({"role": "assistant", "content": question})
                st.stop()
            else:
                # We have the info!
                status_placeholder.markdown(f"**Extracted Info:**\n- Website: {extraction.website_url}\n- Competitors: {', '.join(extraction.competitors or [])}\n- Keywords: {', '.join(extraction.target_keywords or [])}\n\n*Running full analysis...*")
                
                # Build mock input for LangGraph
                mock_input = {
                    "questionnaire_answers": [{"question": "User Profile Description", "answer": user_input}],
                    "website_url": extraction.website_url or "https://example.com",
                    "competitors": extraction.competitors or [],
                    "target_keywords": extraction.target_keywords or [],
                    "chat_history": chat_history,
                    "active_persona": st.session_state.active_persona
                }
                
                # Run Workflow
                with st.spinner("Compiling LangGraph Workflow..."):
                    graph = build_marketing_graph()
        
                progress_bar = st.progress(0)
                logs = []
                final_state = None
                step_count = 0
                total_steps = 8
                
                try:
                    for event in graph.stream(mock_input):
                        for node_name, state_update in event.items():
                            step_count += 1
                            progress_bar.progress(min(step_count / total_steps, 1.0))
                            logs.append(f"- [OK] Node Finished: **{node_name.upper()}**")
                            status_placeholder.markdown("\n".join(logs))
                        final_state = state_update
                        
                    progress_bar.empty()
                    status_placeholder.empty()
                    
                    if final_state and "marketing_strategy" in final_state:
                        strategy = final_state["marketing_strategy"]
                        st.markdown(strategy)
                        st.session_state.messages.append({"role": "assistant", "content": strategy})
                        st.session_state.workflow_completed = True
                        
                        # Save the generated context so follow ups don't need re-crawling
                        st.session_state.final_state = final_state
                    else:
                        st.error("Workflow completed but no strategy was generated.")
                        
                except Exception as e:
                    st.error(f"An error occurred during workflow execution: {e}")
                    
        else:
            # WORKFLOW IS COMPLETED. Just chat with the LLM using the memory.
            with st.spinner("Thinking..."):
                from langchain_google_genai import ChatGoogleGenerativeAI
                from app.prompts.personality_manager import PersonalityManager
                
                api_key = os.environ.get("GOOGLE_API_KEY")
                llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=api_key)
                
                # Build a simple follow-up prompt
                manager = PersonalityManager(st.session_state.active_persona)
                prompt_template = manager.get_strategy_prompt_template()
                
                state = st.session_state.final_state
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
                    "chat_history": chat_history + [("user", user_input)]
                })
                
                reply = response.content
                if isinstance(reply, list):
                    reply = "".join(b.get("text", "") for b in reply if isinstance(b, dict))
                    
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
