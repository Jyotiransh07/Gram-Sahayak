"""FastAPI backend interface for Gram Sahayak."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import config, db, tools, rag
from .agents import list_agents
from .workflow import run_question
from .voice import transcribe, text_to_speech
from .services.documents import extract_text

app = FastAPI(
    title="Gram Sahayak | Indian Agricultural Multi-Agent AI",
    version="2.0.0",
    description="Agentic AI powered by LangGraph, LangChain, Google Gemini 3.5, and Ollama 3.2.",
)

# In-memory store for active uploaded policy documents in local session
UPLOADED_DOCUMENTS: dict[str, dict] = {}


class AskRequest(BaseModel):
    query: str = Field(default="", max_length=5000)
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex, max_length=100)
    language: Literal["hi", "en"] = "en"
    city: str = Field(default="Nashik", max_length=120)
    district: str = Field(default="", max_length=120)
    state_name: str = Field(default="Maharashtra", max_length=120)
    commodity: str = Field(default="", max_length=100)
    forced_route: str = ""
    document_text: str = ""
    document_name: str = ""


def handle_question(**args):
    session = args.get("session_id") or "demo"
    stored_profile = db.get_profile(session)
    if stored_profile and stored_profile.get("consent"):
        if not args.get("city"):
            args["city"] = stored_profile.get("city", "")
        if not args.get("district"):
            args["district"] = stored_profile.get("district", "")

    prior = db.get_history(session, limit=6)
    recent_context = "\n".join(f"{row['role']}: {row['content'][:220]}" for row in prior)

    result = run_question(recent_context=recent_context, **args)

    user_query = args.get("query") or (f"[Uploaded {args.get('document_name')}]" if args.get("document_name") else "[Photo submitted]")
    db.store_message(session, "user", user_query, args.get("language", "en"))
    db.store_message(session, "assistant", result.get("answer", ""), args.get("language", "en"))

    sources = [
        {"title": e.get("title"), "source": e.get("source"), "as_of": e.get("as_of")}
        for e in result.get("evidence", [])
    ]

    return {
        "answer": result.get("answer", ""),
        "language": args.get("language", "en"),
        "session_id": session,
        "route": result.get("route", "agriculture"),
        "agents_executed": result.get("trace", []),
        "verified": result.get("verified", False),
        "sources": sources,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_active": bool(config.USE_GEMINI and config.GEMINI_KEY),
        "gemini_model": config.GEMINI_MODEL,
        "ollama_model": config.OLLAMA_MODEL,
        "data_gov_configured": bool(config.DATA_GOV_KEY),
        "ceda_configured": bool(config.CEDA_KEY),
    }


@app.get("/")
def home():
    return {
        "project": "Gram Sahayak (ग्राम सहायक)",
        "docs": "/docs",
        "frontend": "http://127.0.0.1:7860",
        "version": "2.0.0",
    }


@app.get("/api/agents")
def get_agents():
    """Returns the full roster and metadata of active agents."""
    return {"agents": list_agents()}


@app.post("/api/chat")
def chat(request: AskRequest):
    return handle_question(**request.model_dump())


@app.get("/api/history/{session_id}")
def history(session_id: str):
    return db.get_history(session_id)


@app.delete("/api/history/{session_id}")
def forget(session_id: str):
    db.delete_user_data(session_id)
    return {"deleted": True}


class ProfileRequest(BaseModel):
    session_id: str
    city: str = ""
    district: str = ""
    crop: str = ""
    language: Literal["hi", "en"] = "en"
    consent: bool = False


@app.post("/api/profile")
def profile(req: ProfileRequest):
    if not req.consent:
        raise HTTPException(400, "Explicit consent is required to save profile details.")
    db.save_profile(**req.model_dump())
    return {"saved": True}


@app.get("/api/profile/{session_id}")
def read_profile(session_id: str):
    return db.get_profile(session_id) or {"saved": False}


@app.post("/api/voice")
async def voice(
    audio: UploadFile = File(...),
    language: str = "en",
    session_id: str = "demo",
    city: str = "Nashik",
    district: str = "",
    commodity: str = "",
):
    if language not in ("hi", "en"):
        raise HTTPException(400, "Only Hindi and English are supported.")

    content = await audio.read(15 * 1024 * 1024 + 1)
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "Audio file exceeds 15 MB limit.")

    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in (".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac"):
        suffix = ".wav"

    path = config.UPLOADS / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(content)

    try:
        spoken = transcribe(str(path), preferred_language=language)
        if not spoken:
            return {
                "transcript": "",
                "answer": "आवाज स्पष्ट सुनाई नहीं दी। कृपया माइक के पास बोलें।" if language == "hi" else "Could not detect clear speech. Please speak closer to the microphone.",
                "audio_path": None,
                "agents_executed": ["Voice Transcriber Agent"],
                "sources": [],
            }

        result = handle_question(
            query=spoken,
            language=language,
            session_id=session_id,
            city=city,
            district=district,
            commodity=commodity,
        )

        audio_reply = None
        try:
            audio_reply = text_to_speech(result["answer"], language=language)
        except Exception:
            pass

        result["audio_path"] = audio_reply
        result["transcript"] = spoken
        return result
    finally:
        path.unlink(missing_ok=True)


@app.post("/api/crop/analyze")
async def analyze_crop(
    image: UploadFile = File(...),
    language: str = "en",
    session_id: str = "demo",
):
    if language not in ("hi", "en"):
        raise HTTPException(400, "Only Hindi and English are supported.")

    content = await image.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image exceeds 10 MB limit.")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        suffix = ".jpg"

    path = config.UPLOADS / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(content)

    try:
        query_text = (
            "पौधे की पत्ती/फसल के दृश्य लक्षणों की जांच करें।"
            if language == "hi"
            else "Inspect visual symptoms of this crop/leaf photograph."
        )
        return handle_question(
            query=query_text,
            language=language,
            session_id=session_id,
            image_path=str(path),
            forced_route="vision",
        )
    finally:
        path.unlink(missing_ok=True)


@app.post("/api/document/upload")
async def upload_policy(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".docx", ".txt", ".md"}
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file format: {suffix}. Upload PDF, DOCX, or TXT.")

    content = await file.read(25 * 1024 * 1024 + 1)
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 25 MB limit.")

    safe_name = f"{uuid.uuid4().hex}{suffix}"
    save_path = config.UPLOADS / safe_name
    save_path.write_bytes(content)

    try:
        extracted = extract_text(save_path)
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read document: {exc}")

    if not extracted or len(extracted.strip()) < 10:
        save_path.unlink(missing_ok=True)
        raise HTTPException(400, "No readable text found in document.")

    doc_id = uuid.uuid4().hex
    UPLOADED_DOCUMENTS[doc_id] = {
        "filename": file.filename,
        "text": extracted,
        "path": str(save_path),
    }

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "characters": len(extracted),
        "preview": extracted[:400],
    }


@app.post("/api/document/summarize")
def summarize_document(
    document_id: str = Form(...),
    language: str = Form("en"),
    question: str = Form(""),
    session_id: str = Form("demo"),
):
    doc = UPLOADED_DOCUMENTS.get(document_id)
    if not doc:
        raise HTTPException(404, "Document session expired or not found. Please re-upload the document.")

    result = handle_question(
        query=question or "Summarize this government agricultural policy / scheme document.",
        language=language,
        session_id=session_id,
        document_text=doc["text"],
        document_name=doc["filename"],
        forced_route="policy_summary",
    )
    return result


@app.get("/api/weather")
def weather(city: str = "Nashik"):
    try:
        return tools.weather(city)
    except tools.ToolError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/mandi")
def mandi(
    commodity: str,
    state_name: str = "Maharashtra",
    district: str = "",
    from_date: str | None = None,
    to_date: str | None = None,
):
    try:
        return tools.mandi(commodity, state_name, district, from_date, to_date)
    except tools.ToolError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/climate")
def climate(city: str = "Nashik", year: int | None = None):
    try:
        return tools.climate(city, year)
    except tools.ToolError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/schemes")
def schemes(query: str = "crop insurance", state: str = ""):
    return tools.schemes(query, state)


@app.get("/api/rag/status")
def rag_status():
    with db.connect() as conn:
        count = conn.execute("SELECT count(*) FROM docs_fts").fetchone()[0]
    return {"ingested_chunks": count, "documents_folder": str(config.DOCUMENTS)}
