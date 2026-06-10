# Website Builder Architecture & Content Generation Audit

This document is a comprehensive end-to-end technical audit of the Website Builder module. It covers the frontend, backend, AI orchestration, image generation, onboarding integration, database layer, API inventory, technical debt, and actionable recommendations.

## Table of Contents
1. [High-Level Architecture](#1-high-level-architecture)
2. [Frontend Audit](#2-frontend-audit)
3. [Backend Audit](#3-backend-audit)
4. [AI Cost & Token Consumption Audit](#4-ai-cost--token-consumption-audit)
5. [Image Generation Audit](#5-image-generation-audit)
6. [Onboarding Data Utilization Audit](#6-onboarding-data-utilization-audit)
7. [Database & State Management Audit](#7-database--state-management-audit)
8. [API Audit](#8-api-audit)
9. [Content Validation & Security Audit](#9-content-validation--security-audit)
10. [Export Pipeline Audit](#10-export-pipeline-audit)
11. [Technical Debt & Risk Assessment](#11-technical-debt--risk-assessment)
12. [Generation Matrix](#12-generation-matrix)
13. [Section Inventory](#13-section-inventory)
14. [Recommendations](#14-recommendations)

---

## 1. High-Level Architecture

The Website Builder operates on a client-server model orchestrating multi-step AI generation.

**Request Flow:**
1. **User** initializes a project by selecting sitemap nodes on the Frontend.
2. **Frontend** sends nodes to the **API Layer** (`/initialize`).
3. **Frontend** triggers AI generation (`/generate-content`).
4. **Business Logic** interfaces with the **AI Engine** injecting onboarding context.
5. **Database** saves structured JSON payloads and marks required images as "pending".
6. **Background Worker** generates images and uploads to S3, updating the DB.
7. **Frontend** polls and displays the final **Preview**.
8. **User** downloads the project via the **Export Pipeline**.

---

## 2. Frontend Audit

The Website Builder is located at `src/pages/website-builder/` and relies on a central orchestrator.

### Core Files
- **`page.tsx`**: The main orchestrator. Manages high-level state (`currentStep`, `pages`, `theme`, `globalContactInfo`). Handles initialization, session restoration, backend sync (`getPages`, `saveContent`), and step transitions.
- **`components/SitemapGenerator.tsx`**: (Step 1) Manages site navigation mapping.
- **`components/ContentPreview.tsx`**: (Step 2) The massive central content editor (2400+ lines). Renders previews/edit forms. Polls the backend for AI image generation completion.
- **`components/DesignTemplate.tsx`**: (Step 3) Template and theme selection. Contains `templateOverrides` for fonts and colors.
- **`components/DownloadOutput.tsx`**: (Step 4) Generates HTML locally (`generatePageHTML`) and initiates the export zip.
- **`src/mocks/websiteBuilder.ts`**: Contains TypeScript interfaces, structural limits, and default mock data.

---

## 3. Backend Audit

The Website Builder backend (`4Sight-backend-refactor`) follows a clean multi-layered architecture:

### 3.1. API Layer (`api/endpoints/website_builder`)
- **File:** `website_builder_routes.py`
- **Purpose:** Exposes REST endpoints using FastAPI. 

### 3.2. Business Logic Layer (`business_logic/website_builder`)
- `ProjectInitializationService`: Creates database entries and sitemap structures.
- `WebsiteContentOrchestratorService`: The central coordinator. It gathers user profile data, interfaces with the AI generator, dispatches image tasks, and parses frontend saves.
- `SeoGeneratorService`: Automatically constructs `sitemap.xml` and `robots.txt`.
- `DocumentExportService`: Zips final HTML and assets into a transportable format.

### 3.3. AI Engine Layer (`ai_engine/marketing4Sight/website_builder`)
- **Files:** `content_generator.py` and `color_extractor.py`
- **Purpose:** Abstracts LLM connections and constructs system prompts.

### 3.4. Database Layer (`db_layer`)
- **File:** `WebsiteBuilderRepository.py`
- **Purpose:** SQLAlchemy data access layer for `WebsiteProject` and `WebsitePage`.

---

## 4. AI Cost & Token Consumption Audit

### 4.1. LLM Models & Integration
- **Text Generation:** Google Gemini (`gemini`) accessed via internal `LLMFactory`.
- **Image Generation:** Google GenAI SDK (`genai.Client`) directly invoking `imagen-4.0-fast-generate-001`.

### 4.2. Token Cost Analysis
- **Text Cost:** Extremely low. Input prompts consume ~600-900 tokens. LLM returns full JSON layouts consuming ~1,500 tokens.
- **Image Cost:** High cost relative to text generation (Imagen pricing).
- **Optimization Strategy:** To aggressively minimize credit burn, the `WebsiteContentGeneratorTool` intentionally **disables** automatic image generation for high-volume list sections (e.g., `founder`, `team`, `gallery`, `productCard`). Images are only automatically triggered for `hero` components.

---

## 5. Image Generation Audit

1. **Prompt Extraction:** The AI text generator parses visual context strings from the initial JSON response.
2. **Pending DB State:** The section is persisted with `image: None` and `image_status: "pending"`.
3. **Async Dispatch:** FastAPI `BackgroundTasks` dispatches `execute_image_pipeline(page_id)` asynchronously.
4. **API Invocation:** `generate_image_and_upload()` contacts Google Imagen 4.0 API.
5. **Compression & Storage:** Opened using `PIL.Image`, converted to compressed `.webp`, and uploaded to AWS S3 bucket (`4sight-platform-dev`).
6. **Finalization:** The public S3 URL is injected back into the component JSON in the database.

---

## 6. Onboarding Data Utilization Audit

| Onboarding Field | Stored In | Consumed By | Website Section |
| ---------------- | --------- | ----------- | --------------- |
| Brand Name | `BusinessProfile` | AI Engine & Export | Global Theme, Meta Titles |
| Brand Differentiators | `BusinessProfile` | AI Engine | USP, Hero, Story |
| Products/Services | `BusinessProfile` | AI Engine | ProductCard, ServiceCard, Grid |
| Target Audience | `BusinessProfile` | AI Engine | Tone injection, Hero copy |
| Brand Colors | `BusinessProfile` | AI Color Extractor | Global Theme (Step 3) |
| Contact Details | `BusinessProfile` | Backend Orchestrator | `contactInfo` sections |

---

## 7. Database & State Management Audit

### 7.1. Database Tables (PostgreSQL)
- **`wb_projects`**: Tracks `template_theme`, `primary_color`, `accent_color`, fonts.
- **`wb_pages`**: Stores `page_name`, `url_slug`. Core UI content is deeply nested in a single `JSONB` column named `components`.

### 7.2. State Management & Synchronization
- **Pages**: Stored in React state `pages`. Synchronized via `api.getPages()` and `api.saveContent()`. The backend `JSONB` is the definitive source of truth.
- **Footer/Contact**: Stored in React state `globalContactInfo`. Fetched and saved alongside pages.
- **Session Restore Flow**: 
  1. `page.tsx` mounts and calls `checkWebsiteSession()`.
  2. If session exists, prompts user.
  3. `getPages()` fetches the DB state and populates `pages`. Missing sections (like legacy `contactForm`) are forcefully hydrated.

### 7.3. Privacy & Encryption
User contact information (Email/Phone) is securely encrypted using Fernet in the `BusinessProfile` table and decrypted just-in-time during API hydration to prevent leakage.

---

## 8. API Audit

| Frontend Method | HTTP Method | Endpoint Route | Purpose |
|----------------|-------------|----------------|---------|
| `getPages()` | `GET` | `/website-builder/pages` | Fetches current state of pages and contact info. |
| `saveContent()` | `POST` | `/website-builder/save-content` | Saves manual edits and syncs state. |
| `checkWebsiteSession()` | `GET` | `/website-builder/check-session` | Checks for active session to restore. |
| `initializeWebsite()` | `POST` | `/website-builder/initialize` | Sends sitemap nodes to create project structure. |
| `generateWebsiteContent()` | `POST` | `/website-builder/generate-content?page_id={id}` | Triggers AI Engine. |
| `regenerateWebsiteSection()` | `POST` | `/website-builder/regenerate-section` | Regenerates a specific section. |
| `generateWebsiteImage()` | `POST` | `/website-builder/generate-image` | Manually prompts Image Generation provider. |
| `startFreshWebsite()` | `POST` | `/website-builder/start-fresh` | Purges current DB session. |
| `extractWebsiteColors()` | `POST` | `/website-builder/extract-colors` | Extracts brand colors from Onboarding Profile. |
| `exportWebsiteZip()` | `POST` | `/website-builder/export` | Bundles HTML, assets, and theme into ZIP archive. |

---

## 9. Content Validation & Security Audit

### 9.1. JSON Recovery Resilience
The AI Engine employs excellent JSON resilience. A custom `_repair_json` method counts open/close brackets to forcefully repair incomplete LLM trailing arrays/objects before database insertion.

### 9.2. Stored XSS Risks
The backend accepts JSON payloads from the frontend in `/website-builder/save-content` and saves them natively into `JSONB` without HTML sanitization. If the React frontend utilizes `dangerouslySetInnerHTML` anywhere in the preview renderer, the builder is vulnerable to Stored XSS attacks.

---

## 10. Export Pipeline Audit

1. **HTML Generation:** Traced in `DownloadOutput.tsx`, iterates active pages calling `generatePageHTML()` (via `src/utils/htmlGenerator.ts`).
2. **Sitemap & Robots:** Generates `sitemap.xml` and `robots.txt` strings in memory.
3. **Bundling:** Packages HTML strings into an array of objects (`htmlFiles`).
4. **Backend Export:** Sends `htmlFiles` array to `api.exportWebsiteZip()`.
5. **Download:** The backend creates a ZIP blob. The frontend converts the blob using `window.URL.createObjectURL` to trigger a download.

---

## 11. Technical Debt & Risk Assessment

| ID | Issue | Severity | Area | Recommendation |
|---|---|---|---|---|
| WB-001 | Monolithic `ContentPreview.tsx` (2400+ lines) | Critical | Frontend | Break down into separate section components (`HeroRenderer.tsx`, `GridRenderer.tsx`). |
| WB-002 | Aggressive Image Polling | High | Frontend | Transition to WebSockets or SSE instead of polling `getPages()` every 5 seconds. |
| WB-003 | Stored XSS Risk via JSONB | High | Backend | Implement Bleach/HTML sanitization on all text fields before DB commit. |
| WB-004 | Duplicate Initialization API Calls | Medium | Frontend | Consolidate `initializeWebsite()` and `getPages()` during Step 1->2 transition. |
| WB-005 | Form State Management | Medium | Frontend | Refactor `editValues` into a state library like React Hook Form. |

---

## 12. Generation Matrix

| Page | Section | AI Text Gen | Editable | Image Gen | Regeneratable |
|------|---------|-------------|----------|-----------|---------------|
| Home | Hero | Yes | Yes | Yes (Auto) | Yes |
| Home | USP / Grid | Yes | Yes | No | Yes |
| Home | Gallery | No (Auto) | Yes | Yes (Manual) | No |
| About| Story | Yes | Yes | No | Yes |
| Services | ServiceCard | Yes | Yes | No | Yes |
| Contact | ContactInfo | No (Profile Data) | Yes | No | No |
| Contact | ContactForm | No (Static) | No | No | No |

---

## 13. Section Inventory

- **Hero** (`hero`): Contains `headline`, `sub`, `cta`, `image`. Edited via `HeroEditor`. 
- **Story** (`story`): Rich text. Min limit 50 chars.
- **USP / Grid** (`usp`, `grid`): Array of cards (`title`, `description`, `icon`).
- **Blog** (`blog`): Articles (`title`, `excerpt`, `content`, `date`).
- **Founder / Team** (`founder`, `team`): People profiles (`name`, `role`, `bio`, `image`).
- **Problem Solution** (`problemSolution`): Headline with `pain` and `solution` arrays.
- **Service / Product** (`serviceCard`, `productCard`): Cards (`name`, `description`, `url`).
- **Gallery** (`gallery`): Media grid edited via `GalleryEditor`.

---

## 14. Recommendations

### Immediate Fixes
1. **Sanitize Inputs:** Apply HTML escaping to all editable text fields saved to `JSONB` to patch XSS vulnerabilities.
2. **Optimize Polling:** Restrict the 5-second polling interval in `ContentPreview.tsx` to ONLY fetch the image statuses, rather than pulling the entire heavy `pages` array.

### Short-Term Improvements
1. **Extract Components:** Break down `ContentPreview.tsx` into smaller renderer components to vastly improve React render performance and reduce cognitive load.
2. **Eliminate Duplicate API Calls:** Refactor the Step 1 -> Step 2 transition to avoid firing initialization and page fetching concurrently.

### Long-Term Improvements
1. **State Management Refactor:** Move away from monolithic React state for page sections and adopt React Hook Form for section editing.
2. **Image Cost Optimization:** Shift from Google Imagen to a lower-cost or open-source image generation provider for heavy-volume sections (like Gallery), allowing for bulk visual generation without massive credit consumption.
