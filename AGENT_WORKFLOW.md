# Gram Sahayak: 11-Agent Multi-Agent AI Framework

The core architecture is an agentic LangGraph `StateGraph(FarmState)` orchestrated using LangChain, LangGraph, Google Gemini 3.5, and Ollama Llama 3.2. Both **English and हिन्दी** are supported natively across the entire platform.

```mermaid
flowchart TD
 U["Farmer Query (Text, Voice, Photo, or Document)"] --> S["1. Safety & Triage Agent"]
 S -->|Urgent medical/poisoning warning| E["Immediate 112 / Helpline Directive"]
 S -->|Standard Inquiry| R["2. Supervisor & Router Agent"]
 R -->|Live Market Price| M["3. Mandi Price Agent (Agmarknet + CEDA)"]
 R -->|Real-time Weather| W["4. Weather Agent (Open-Meteo)"]
 R -->|Historical Climate| C["5. Climate Analysis Agent (NASA POWER)"]
 R -->|Government Scheme| G["6. Government Scheme Agent (Schemes DB + RAG)"]
 R -->|Crop / Leaf Photo| V["7. Crop Vision Agent (Gemini 3.5 Multimodal)"]
 R -->|Uploaded Policy PDF/Doc| P["8. Policy Summarizer Agent (PyMuPDF)"]
 R -->|Agronomy / Sowing / Soil| A["9. Agriculture Knowledge Agent (FTS5 + RAG)"]
 M --> X["10. Response Generator Agent"]
 W --> X
 C --> X
 G --> X
 V --> X
 P --> F["11. Verification Agent"]
 A --> X
 X --> F
 F -->|Strictly Grounded| O["Verified Response + Citations + Auto TTS Audio"]
 F -->|Numeric Hallucination Detected (Try 1)| X
 F -->|Uncertainty Bound Exceeded| N["Transparent Limitation Notice"]
```

## Agent Roster & Operational Responsibilities

| # | Agent Name | Primary Role | Core Tools & Data Sources | Model / Engine |
|---|------------|--------------|---------------------------|----------------|
| 1 | **Safety & Triage Agent** | Emergency Screener | Emergency hotline directory, safety word scanner | Deterministic zero-latency rules |
| 2 | **Supervisor & Router Agent** | Intent Classifier & Orchestrator | Regex intent matcher, zero-shot LLM classifier | Hybrid (Regex + Gemini / Llama 3.2) |
| 3 | **Mandi Price Agent** | Daily Market Price Specialist | `data.gov.in` (Agmarknet daily API), Ashoka CEDA API | Live Agmarknet + CEDA Fallback |
| 4 | **Weather Agent** | Agro-Meteorology Specialist | Open-Meteo geocoding & 3-day forecast API | Geospatial API Tool |
| 5 | **Climate Analysis Agent** | Historical Climatology Analyst | NASA POWER daily solar & agroclimatology | NASA POWER API Tool |
| 6 | **Government Scheme Agent** | Subsidy & Welfare Advisor | Curated schemes directory (`schemes.json`), MyScheme | Keyword Ranker + RAG |
| 7 | **Crop Vision Agent** | Plant Symptom Inspector | Multimodal visual inspection, symptom atlas | Google Gemini 3.5 Multimodal Vision |
| 8 | **Policy Summarizer Agent** | Document Analyst | PyMuPDF text extractor, structured parser | Gemini 3.5 Flash / Ollama Llama 3.2 |
| 9 | **Agriculture Knowledge Agent** | Agronomy Advisory Specialist | SQLite FTS5 index, Chroma hybrid vector search | RAG (multilingual-e5-small) |
| 10 | **Response Generator Agent** | Multilingual Communicator | Grounded synthesis engine, citation formatter | Google Gemini 3.5 Flash / Ollama Llama 3.2 |
| 11 | **Verification Agent** | Anti-Hallucination Guard | Numeric claim auditor, regex grounding verifier | Deterministic Regex Auditor |

## Shared Agent State (`FarmState`)

All nodes operate on the shared TypedDict state:
- `query`: User's text or transcribed voice query
- `language`: Target response language (`'en'` or `'hi'`)
- `session_id`: Unique identifier for local continuity
- `city`, `district`, `state_name`, `commodity`: Geospatial and market context
- `image_path`: Path to uploaded plant/leaf photograph
- `document_text`: Extracted text from uploaded policy PDF/DOCX/TXT
- `document_name`: Filename of uploaded document
- `route`: Active route assigned by supervisor
- `evidence`: Machine-readable evidence list from specialist tools
- `answer`: Draft or final synthesized response
- `verified`: Grounding verification boolean
- `tries`: Correction loop counter (bounded to 1 retry)
- `feedback`: Re-generation guidance from verifier
- `trace`: Ordered log of agents executed
- `recent_context`: Conversation history context
