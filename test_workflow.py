import json
import logging
from app.workflows.marketing_workflow import build_marketing_graph

logging.basicConfig(level=logging.INFO)

def main():
    print("--- Building LangGraph Workflow ---")
    workflow = build_marketing_graph()
    
    print("\n--- Executing LangGraph Workflow ---")
    
    initial_state = {
        "questionnaire_answers": [
            {"question": "What is your business model?", "answer": "We are a B2B SaaS platform."},
            {"question": "Who is your target audience?", "answer": "Enterprise marketers."}
        ],
        "website_url": "https://example.com",
        "competitors": ["https://competitor.com"],
        "target_keywords": ["marketing automation", "b2b saas"]
    }
    
    try:
        final_state = workflow.invoke(initial_state)
        
        print("\n--- Graph Execution Successful ---")
        strategy = final_state.get("marketing_strategy", {})
        print(json.dumps(strategy, indent=2))
        
    except Exception as e:
        print(f"\nGraph execution failed: {e}")

if __name__ == "__main__":
    main()
