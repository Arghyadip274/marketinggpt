# MarketingGPT

MarketingGPT is an advanced, multi-agent AI marketing intelligence platform. It is engineered with a strict, production-ready backend architecture designed to ingest raw business data, analyze competitors and market trends, and output highly structured, actionable marketing strategies.

---

## 🏗 Architecture & Features Overview

### 1. Core Analyzers (The "Tools" Layer)
Located in `app/tools/`, these are the raw data-processing engines that interact with the outside world.
* **Website Analyzer (`website_analyzer.py`)**: Scrapes a target website URL to extract technical SEO metrics. It counts `H1`/`H2` tags, calculates image alt-text coverage, checks for internal linking, identifies Calls-To-Action (CTAs), and computes an aggregate `seo_score`.
* **Competitor Analyzer (`competitor_analyzer.py`)**: Scrapes competitor URLs to extract their core messaging (titles, H1s, H2s), specific offers/discounts, and CTAs. It uses heuristic logic to infer their dominant market strategy (e.g., "Sales-Led" vs "Product-Led").
* **Industry Analyzer (`industry_analyzer.py`)**: Uses a normalized rule-based knowledge base to map a user's industry (e.g., "SaaS", "Ecommerce") to proven marketing patterns, common channels (e.g., LinkedIn Ads), standard offers, and messaging benchmarks.
* **Keyword Detector (`keyword_detector.py`)**: Ingests lists of target keywords and their raw metrics. It applies a proprietary normalization algorithm to rank the keywords based on their overall "Opportunity Score."
* **Trend Analyzer (`trend_analyzer.py`)**: Designed to interface with Google Trends to analyze the search velocity of given keywords over time, identifying which keywords are actively "rising" in popularity.

### 2. Onboarding & Ingestion Pipeline
* **Questionnaire Converter (`app/utils/question_converter.py`)**: A utility that reads a raw Microsoft Word document (`data/marketing_questions.docx`) and heuristically parses it into a structured JSON configuration file (`app/config/marketing_questions.json`), dynamically inferring question categories and required input types.
* **Questionnaire Models & Service**: Strictly validates user onboarding submissions against the required questions in the JSON config. It compiles valid submissions into a structured `BusinessProfile`.

### 3. The Service Layer (Clean Architecture)
Located in `app/services/`, this layer wraps every core analyzer in a robust, exception-safe class. It enforces Dependency Injection and ensures that backend crashes (like a scraped website timing out) do not crash the application.
* Services include: `KeywordService`, `TrendService`, `WebsiteService`, `CompetitorService`, `IndustryService`, and `QuestionnaireService`.

### 4. Master Strategy Orchestration
Located in `app/services/strategy_service.py`, this is the centralized heuristic brain of the pre-LLM application.
* **`StrategyService`**: Dynamically instantiates all 5 core analyzer services. When given a business profile and a target website/competitors/keywords, it triggers all analyzers, aggregates the massive multidimensional data payload, and uses rule-based correlation to generate actionable SEO strategies, channel recommendations, and messaging tactics.

### 5. API Layer (FastAPI)
Located in `app/api/` and registered in `main.py`.
* Exposes all individual services via isolated, RESTful POST endpoints (e.g., `/api/website-analysis`).
* Exposes the master orchestration engine via `POST /api/marketing-strategy`.
* Enforces strict API contracts using `Pydantic v2` data models (`app/models/`).
* Implements FastAPI `Depends()` for clean dependency injection, mapping backend `ServiceErrors` directly to HTTP responses.

### 6. Retrieval-Augmented Generation (RAG) Scaffold
Located in `app/rag/`, this module prepares the system for semantic document search.
* **`documents/` & `vector_store/`**: Directories initialized to hold raw PDFs and the local ChromaDB vector space.
* **`ingest.py`**: A `DocumentIngester` class scaffolded to process raw text using LangChain `TextSplitters` and `OpenAIEmbeddings`.
* **`retriever.py`**: A `KnowledgeRetriever` class scaffolded to execute `similarity_search()` queries against the ChromaDB vector store, injecting semantic context into the marketing strategy.

### 7. AI & LLM Agent Integration (LangChain & LangGraph)
The most advanced layer of the application, transforming the rigid API backend into an autonomous AI toolset.
* **LangChain Tools (`app/chains/tools.py`)**: Every single domain service is wrapped in a LangChain `@tool` decorator. The wrappers intercept LLM-friendly primitives and safely coerce them into strict Pydantic objects.
* **LangGraph State Machine (`app/workflows/marketing_workflow.py`)**: 
  - Uses `MarketingState` to retain inputs, intermediate payloads, and outputs.
  - A compiled directed graph automatically routes data sequentially across 8 isolated nodes (Questionnaire -> Website -> Competitors -> Industry -> Keywords -> Trends -> RAG -> Strategy) to completely automate the intelligence pipeline.

---

## 🚀 Getting Started

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the API Server:
   ```bash
   fastapi dev main.py
   ```
3. Run the orchestration pipeline test:
   ```bash
   python test_workflow.py
   ```
