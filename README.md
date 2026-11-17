# Gram Sahayak — Hindi & English Agricultural Multi-Agent AI

**A production-ready rural information assistant with 11 LangGraph agent nodes, Google Gemini 3.5 Flash, Ollama 3.2, Gradio 6 UI, FastAPI, document policy summarization, Agmarknet live daily mandi rates, and dual text/voice interaction.**

## Key Features & 11 Specialized Agents

1. **Safety & Triage Agent** — Emergency health & poisoning screening with 112 guidance.
2. **Supervisor & Router Agent** — High-accuracy rule + LLM intent classification.
3. **Mandi Price Agent** — Live daily APMC arrival rates from `data.gov.in` (Agmarknet) + CEDA fallback.
4. **Weather Agent** — Real-time weather and 3-day forecast via Open-Meteo.
5. **Climate Analysis Agent** — Historical climate trends (1981 to present) via NASA POWER.
6. **Government Scheme Agent** — Search and eligibility advisory for central and state farm schemes.
7. **Crop Vision Agent** — Multimodal leaf symptom inspection via Google Gemini 3.5.
8. **Policy Summarizer Agent** — Upload PDF/DOCX/TXT policy circulars for structured farmer briefings.
9. **Agriculture Knowledge Agent** — RAG over indexed farming knowledge documents (FTS5 + vectors).
10. **Response Generator Agent** — Grounded multilingual synthesis in natural Hindi & English.
11. **Verification Agent** — Numeric grounding and anti-hallucination guard with revision loop.

## UI Highlights

- **Dynamic Multilingual Switcher**: Instant full-website translation between English and हिन्दी.
- **Unified Chat & Voice Assistant**: Record via mic, auto-transcribe, and auto-play spoken replies with reset.
- **Dedicated Mandi Explorer**: Search by commodity, state, and district with APMC arrival rates.
- **Policy Document Summarizer**: Upload PDF/DOCX/TXT and get structured breakdowns of benefits, eligibility, and rules.
- **Agent Roster**: Inspect what each agent is doing and performing in real-time.

Telegram, local memory (SQLite messages and optional LangGraph checkpoints), microphone STT, TTS and reminders are **supporting services**, not extra agents.

## 1. Install Windows prerequisites

- **Python 3.11 64-bit:** https://www.python.org/downloads/ (check "Add Python to PATH")
- **Ollama for Windows:** https://ollama.com/download/windows
- **VS Code:** https://code.visualstudio.com/
- **FFmpeg:** https://ffmpeg.org/download.html (for microphone, MP3/OGG processing; verify `ffmpeg -version`)
- Internet initially for Python libraries, model downloads and live tools.
- For a laptop with **8 GB RAM**, start with `llama3.2:3b`, avoid loading the vision model and the language model simultaneously, and expect slower CPU-only speech/photo inference.

## 2. Extract ZIP and create the environment

Open **Command Prompt (cmd)** in the extracted project folder:

```bat
py -3.11 --version
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-voice.txt
copy .env.example .env
```

You can also run `setup_windows.bat` for the base environment, then install voice extras manually.

For crop-photo, large semantic models, and Telegram, additional requirements are **optional** and documented in `API_SETUP.md`.

## 3. Download local Ollama AI

```bat
ollama pull llama3.2:3b
ollama list
```

If you already have `llama3.2` installed, inspect the exact model tag with `ollama list` and update `.env` accordingly.

For crop photo analysis:

```bat
ollama pull qwen2.5vl:3b
```

Check the Ollama service at http://127.0.0.1:11434/api/tags . If Ollama is already running in the Windows tray, **do not** run another `ollama serve` instance.

## 4. Configure API credentials (only if you want those optional features)

Open `.env` with Notepad or VS Code. **See `API_SETUP.md` for every click needed** for `data.gov.in`, Gemini, and Telegram. Weather and NASA POWER require no key.

No payment details are required for the core system; do not set up a paid cloud tier.

## 5. Add trusted PDFs, then ingest

Copy permitted official PDFs into `data/documents/`. Put their URLs into `data/documents/sources.json`. Then:

```bat
python -m scripts.ingest
```

For optional multilingual dense semantic retrieval, install additional packages and rebuild:

```bat
python -m pip install -r requirements-rag.txt
python -m scripts.ingest --vectors
```

**The assistant initially knows only the curated government scheme directory and public data APIs. Agriculture/health RAG answers require your actual official documents.** No fabricated official PDFs are provided.

## 6. Start backend — Terminal 1

```bat
cd PATH\TO\Gram_Sahayak_Multi_Agent
.venv\Scripts\activate
python -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

Verify:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs (interactive FastAPI docs)
- http://127.0.0.1:8000/api/rag/status

Or double-click `start_backend.bat`.

## 7. Start Gradio — Terminal 2

```bat
cd PATH\TO\Gram_Sahayak_Multi_Agent
.venv\Scripts\activate
python frontend.py
```

Open http://127.0.0.1:7860 or double-click `start_frontend.bat`.

The Gradio UI has tabs for Chat, Voice, Crop Photo, Weather, Mandi, Climate, Schemes, Health Facilities, Profile & Privacy, and History. Select **English** or **हिन्दी**, and replace the demonstration city **Nashik** with your town.

## 8. Voice usage (English + Hindi only)

- **Standard mode:** Start recording in the Voice tab, speak, then stop. Gradio automatically sends the recording for transcription, generates a reply, saves an MP3/WAV in `data/audio/`, and attempts to play it.
- **Experimental hands-free:** In the live microphone section, click Start once, speak, and pause for roughly one second. An energy-based silence detector segments speech. Browser/room noise can affect reliability; this is not a production-grade voice turn detector.
- `faster-whisper` downloads its base speech model the first time it is used. gTTS needs internet for speech output. Set `TTS_BACKEND=mms` for the offline alternative; see `API_SETUP.md`.
- If microphone capture fails, ensure browser permissions are enabled for localhost, and install FFmpeg.

## 9. Telegram integration (optional)

Follow `API_SETUP.md` to create a free Telegram bot, set `TELEGRAM_BOT_TOKEN`, then:

```bat
python -m pip install -r requirements-telegram.txt
python -m app.telegram_bot
```

Use `/language hi`, `/language en`, `/city Nashik` and `/remind YYYY-MM-DD HH:MM text`. Reminders are delivered only when the Telegram program is running and the user explicitly creates them. No n8n is needed.

## 10. API endpoints

| Method | Endpoint | Action |
|---|---|---|
| GET | `/health` | Backend status |
| POST | `/api/chat` | Route text through all relevant agents |
| POST | `/api/voice` | Upload audio, STT, answer and save output audio |
| POST | `/api/crop/analyze` | Upload crop image and ask vision specialist |
| GET | `/api/weather?city=Nashik` | Open-Meteo forecast |
| GET | `/api/mandi?commodity=Onion&state_name=Maharashtra` | Live government market records (credentialed) |
| GET | `/api/climate?city=Nashik&year=2025` | Historical NASA POWER |
| GET | `/api/schemes?query=crop%20insurance` | Scheme directory |
| GET | `/api/facilities?city=Nashik` | User-triggered OSM lookup |
| GET | `/api/rag/status` | Number of indexed document passages |
| GET | `/api/history/{session_id}` | Local history (localhost-only; no auth) |
| DELETE | `/api/history/{session_id}` | Delete local profile and chat history |
| POST | `/api/profile` | Save opted-in profile |

To test Swagger: open `/docs`, expand **POST /api/chat**, click **Try it out**, supply:

```json
{
  "query": "What is tomorrow's weather?",
  "language": "en",
  "city": "Nashik",
  "session_id": "local-demo"
}
```

For Hindi use `"language":"hi"` and a Hindi question.

## 11. Test and troubleshoot

```bat
python -m compileall app frontend.py scripts
python -m pytest -q
```

**Troubleshooting**

- `ModuleNotFoundError`: confirm `.venv` activated and installed relevant requirements file.
- `Connection refused 11434`: start Ollama for Windows and check `ollama list`.
- `model not found`: pull the model or change `.env` model name.
- `Connection refused 8000`: run `start_backend.bat` before Gradio.
- `No sources`: ingest actual official agriculture PDFs.
- `Mandi API setup required`: create free portal key AND copy current resource ID (see `API_SETUP.md`).
- `403/429` from services: access denied or quota/rate limit; do not invent live results.
- Whisper too slow: use the `tiny` model in `app/voice.py` instead of `base`, at some accuracy cost.
- `ChromaDB` errors: semantic retrieval is optional, use FTS5 only with `python -m scripts.ingest`.
- Chrome autoplay blocked: click/play once; browsers can require interaction before sound is automatically played.
- No crop vision: run `ollama pull qwen2.5vl:3b` and close other heavy programs.

## 12. Important limitations

- **Security:** The FastAPI routes have no login or per-user access control, so **keep `127.0.0.1` bind and do not deploy them publicly** without authentication, permissions, abuse prevention, file validation and secure secrets management. A session ID alone is not proof of identity.
- **Medical:** General education/referral only; no diagnoses or prescription doses. Urgent signals bypass the AI generative-answer flow. OpenStreetMap facility data is not an emergency dispatch service.
- **Crop diagnosis:** A photo cannot verify a specific plant disease. The result is a visual observation; confirm with an agricultural specialist.
- **Government schemes:** The included directory lists relevant programs; it does **not** grant or guarantee final eligibility.
- **Weather/mandi:** Date and actual API results are shown. No fake live prices or forecasts.
- **Verifier:** The included deterministic verifier catches unsupported numeric claims and requires evidence; optional `USE_LLM_VERIFIER=true` adds local LLM review but can add latency. It is not a comprehensive fact-checker. It can miss unsupported qualitative statements. Human review and evaluation are necessary for real-world use.
- **Speech:** Free gTTS is an unofficial network-dependent service. Offline MMS requires extra memory and its model licenses limit commercial use.
- **Testing:** Gradio component construction has been checked in the build environment; full external service integration still requires installed LangGraph, the AI models and any optional API keys on the user's PC.

## Project tree

```text
Gram_Sahayak_Multi_Agent/
├── app/
│   ├── api.py             # FastAPI
│   ├── workflow.py        # 11 LangGraph agents
│   ├── tools.py           # Weather, mandi, NASA POWER, OSM, schemes
│   ├── rag.py             # PDF/TXT/MD RAG, optional hybrid semantic
│   ├── llm.py             # Local Ollama and optional Gemini fallback
│   ├── voice.py           # Hindi/English STT/TTS
│   ├── db.py              # SQLite records, cache, history
│   ├── reminders.py       # Native APScheduler
│   └── telegram_bot.py    # Telegram long-polling
├── frontend.py            # Gradio localhost dashboard
├── scripts/ingest.py      # Official PDF ingestion
├── tests/                 # Unit tests
├── data/
│   ├── documents/         # Your trusted documents and sources.json
│   ├── schemes.json       # Curated official scheme discovery
│   ├── audio/             # Generated speech files
│   └── uploads/           # Temporary media
├── .env.example           # Environment configuration template
├── requirements*.txt      # Modular package installation
├── API_SETUP.md           # Exact API setup steps
├── AGENT_WORKFLOW.md      # Multi-agent diagram and examples
├── START_HERE.txt         # Fast installation sequence
├── start_backend.bat
├── start_frontend.bat
└── start_telegram.bat
```
