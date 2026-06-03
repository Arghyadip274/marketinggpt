import json
import logging
import os
from app.workflows.marketing_workflow import build_marketing_graph
from app.utils.logger import configure_logging

# Inject the user's Gemini API Key for terminal testing
os.environ["GOOGLE_API_KEY"] = "AIzaSyCuV0U2aS8hCRckFHoQqpuAKwv5iwSEjgE"

def main():
    # Setup basic logging to suppress noisy output if needed
    configure_logging()
    
    print("=" * 60)
    print("      MarketingGPT LangGraph Orchestration Test   ")
    print("=" * 60)
    
    # 1. Compile Graph
    print("\n[1] Compiling workflow graph...")
    graph = build_marketing_graph()
    
    # 2. Define Mock Input State
    mock_input = {
        "questionnaire_answers": [
            {"question": "What is your main product?", "answer": "Inbound marketing, sales, and CRM software"},
            {"question": "Who is your target audience?", "answer": "Mid-market businesses"}
        ],
        "website_url": "https://www.hubspot.com/",
        "competitors": ["https://www.salesforce.com/", "https://www.zoho.com/"],
        "target_keywords": ["crm software", "inbound marketing strategy"]
    }
    
    print("\n[2] Initializing State with:")
    print(json.dumps(mock_input, indent=2))
    
    print("\n[3] Executing Workflow (Streaming nodes)...\n")
    print("-" * 60)
    
    # Run the graph and stream state updates
    final_state = None
    for event in graph.stream(mock_input):
        for node_name, state_update in event.items():
            print(f"[OK] Node Finished: [{node_name.upper()}]")
            # The state update contains all the data returned by the node
            print(f"   -> Keys Updated: {list(state_update.keys())}")
        final_state = state_update
        
    print("-" * 60)
    print("\n[4] Workflow Complete! Final Strategy Output:\n")
    
    # The final event usually contains the state from the last node executed
    # However, since stream yields the delta, we check if marketing_strategy was returned
    if final_state and "marketing_strategy" in final_state:
        print(json.dumps(final_state["marketing_strategy"], indent=2))
    else:
        print("No strategy generated. Please check logs.")

if __name__ == "__main__":
    main()
