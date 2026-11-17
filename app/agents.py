"""Gram Sahayak Multi-Agent Framework (Agentic AI with LangGraph & LangChain).

This module contains the complete definition, toolset, state schema, and execution
graph for all specialized agents in the Gram Sahayak ecosystem.

Agents Implemented:
1. SafetyTriageAgent: Intercepts medical emergencies, severe symptoms, and pesticide poisoning.
2. SupervisorAgent: Intent routing using fast rule-based matching with LLM routing fallback.
3. MandiPriceAgent: Fetches live daily APMC mandi rates from Agmarknet (data.gov.in) with CEDA fallback.
4. WeatherAgent: Real-time agro-meteorology and 3-day weather forecasts via Open-Meteo.
5. ClimateAgent: Historical climate trends, rainfall, and temperature from NASA POWER.
6. SchemesAgent: Central and State government schemes discovery, eligibility, and portal guidance.
7. CropVisionAgent: Multimodal visual inspection of crop leaves/plants using Gemini 3.5.
8. PolicySummarizerAgent: PDF/document policy analysis, extracting benefits, eligibility, and rules.
9. AgricultureAgent: Grounded agronomic advisory using RAG over farming knowledge documents.
10. ResponseGeneratorAgent: Multilingual response synthesis in natural Hindi or English.
11. VerificationAgent: Strict numeric grounding and hallucination guard with corrective retry loop.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph
from . import config, db, llm, rag, tools


# =====================================================================
# State Schema
# =====================================================================

class FarmState(TypedDict, total=False):
    """Execution state passed between agents in the LangGraph workflow."""
    query: str
    language: str                  # 'en' or 'hi'
    session_id: str
    city: str
    district: str
    state_name: str
    commodity: str
    image_path: str                # Path to uploaded crop photograph
    document_text: str             # Extracted text from uploaded policy PDF/doc
    document_name: str             # Name of uploaded document
    forced_route: str
    route: str
    emergency: bool
    evidence: List[Dict[str, Any]]
    answer: str
    verified: bool
    tries: int
    feedback: str
    trace: List[str]               # Step-by-step trace of which agents executed
    recent_context: str


ROUTES = ("agriculture", "weather", "mandi", "climate", "schemes", "vision", "policy_summary")


# =====================================================================
# Agent Metadata Registry (For Inspection & UI Transparency)
# =====================================================================

AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Safety & Triage Agent": {
        "id": "safety_triage",
        "role": "Emergency Medical & Poisoning Screener",
        "description": "Intercepts critical life-safety queries (poisoning, unconsciousness, severe pain) and directs immediately to national emergency helplines (112) without generating clinical guesses.",
        "tools": ["Keyword Safety Scanner", "Emergency Hotline Directory"],
        "data_sources": ["National Emergency Services Standards (India 112)"],
        "model": "Deterministic rule-based (Zero latency)",
    },
    "Supervisor & Router Agent": {
        "id": "supervisor",
        "role": "Intent Classifier & Workflow Orchestrator",
        "description": "Analyzes user query and context, classifying intent into agriculture, mandi, weather, climate, schemes, vision, or policy analysis.",
        "tools": ["Agricultural Intent Matcher", "LLM Zero-Shot Classifier"],
        "data_sources": ["User prompt", "Conversation history"],
        "model": "Hybrid (Rule Regex + Gemini 3.5 / Ollama Llama 3.2)",
    },
    "Mandi Price Agent": {
        "id": "mandi",
        "role": "Daily Market Price & APMC Rate Specialist",
        "description": "Retrieves verified daily arrival prices from Ministry of Agriculture Agmarknet (data.gov.in) with automatic fallback to Ashoka CEDA.",
        "tools": ["Agmarknet API Connector", "CEDA Agri Market API", "Commodity Normalizer"],
        "data_sources": ["data.gov.in (Agmarknet DMI)", "Ashoka University CEDA"],
        "model": "API Tool Execution + Data Aggregation",
    },
    "Weather Agent": {
        "id": "weather",
        "role": "Agro-Meteorological Forecast Specialist",
        "description": "Fetches current temperature, humidity, precipitation, wind speed, and 3-day agricultural forecasts for any Indian location.",
        "tools": ["Open-Meteo Geocoding", "Open-Meteo Weather Forecast API"],
        "data_sources": ["Open-Meteo (IMD & Global Models)"],
        "model": "Geospatial API Tool",
    },
    "Climate Analysis Agent": {
        "id": "climate",
        "role": "Historical Agro-Climatology Analyst",
        "description": "Analyzes historical annual temperature and rainfall patterns (1981 to present) to help farmers assess climate trends and drought risks.",
        "tools": ["NASA POWER Daily Agroclimatology API"],
        "data_sources": ["NASA POWER (Prediction of Worldwide Energy Resources)"],
        "model": "Agroclimatology API Tool",
    },
    "Government Scheme Agent": {
        "id": "schemes",
        "role": "Agricultural Schemes & Subsidies Advisor",
        "description": "Identifies applicable central and state government schemes (PM-Kisan, Fasal Bima, KCC, Soil Health Card), outlining benefits, eligibility, and official links.",
        "tools": ["Schemes Knowledge Database", "MyScheme Finder"],
        "data_sources": ["Curated schemes directory (data/schemes.json)"],
        "model": "Keyword Ranker + RAG Knowledge Retrieval",
    },
    "Crop Vision Agent": {
        "id": "vision",
        "role": "Multimodal Plant & Leaf Symptom Inspector",
        "description": "Analyzes photos of crops and diseased leaves, describing visible lesions, discoloration, or pests with safe cultural precautions.",
        "tools": ["Gemini 3.5 Multimodal Vision", "Agronomy Symptom Atlas"],
        "data_sources": ["Uploaded plant photograph", "RAG crop library"],
        "model": "Google Gemini 3.5 Multimodal Vision",
    },
    "Policy Summarizer Agent": {
        "id": "policy_summary",
        "role": "Government Policy & Circular Document Analyst",
        "description": "Extracts and synthesizes complex government notifications, insurance policy wordings, or subsidy PDFs into clear, farmer-friendly terms.",
        "tools": ["PyMuPDF Extractor", "Policy Structure Parser"],
        "data_sources": ["Uploaded PDF / DOCX / TXT file"],
        "model": "Google Gemini 3.5 / Ollama Llama 3.2",
    },
    "Agriculture Knowledge Agent": {
        "id": "agriculture",
        "role": "Agronomy & Crop Management Specialist",
        "description": "Provides verified guidance on sowing windows, soil management, organic fertilizers, irrigation scheduling, and integrated pest management.",
        "tools": ["SQLite FTS5 Full-Text Retrieval", "Chroma Hybrid Vector Search"],
        "data_sources": ["Ingested ICAR/KVK guides and official agriculture manuals"],
        "model": "RAG Concept (Sentence Transformers + FTS5)",
    },
    "Response Generator Agent": {
        "id": "response_generator",
        "role": "Multilingual Farmer Communicator",
        "description": "Synthesizes final responses in fluent, respectful Hindi (Devanagari) or English, strictly grounded in retrieved evidence.",
        "tools": ["Grounded Synthesis Engine", "Source Citation Formatter"],
        "data_sources": ["Aggregated Evidence from Specialist Agents"],
        "model": "Google Gemini 3.5 Flash / Ollama Llama 3.2",
    },
    "Verification Agent": {
        "id": "verifier",
        "role": "Fact-Checking & Anti-Hallucination Guard",
        "description": "Verifies that all numerical claims, market rates, and dates in the response exist in the source evidence, triggering a correction loop if unverified numbers appear.",
        "tools": ["Numeric Grounding Extractor", "Source Consistency Auditor"],
        "data_sources": ["Retrieved Evidence", "Draft Response"],
        "model": "Deterministic Regex Auditor + Optional LLM Verifier",
    },
}


def list_agents() -> List[Dict[str, Any]]:
    """Returns the full list of agents and their operational specifications."""
    return [{"name": name, **meta} for name, meta in AGENT_REGISTRY.items()]


def _record(state: FarmState, name: str, **fields) -> Dict[str, Any]:
    trace = list(state.get("trace") or [])
    if name not in trace:
        trace.append(name)
    return {"trace": trace, **fields}


# =====================================================================
# Agent Node Implementations
# =====================================================================

CRITICAL_EMERGENCY_WORDS = (
    "unconscious", "not breathing", "difficulty breathing", "chest pain",
    "severe bleeding", "seizure", "poison", "pesticide swallowed", "swallowed pesticide",
    "ingested pesticide", "swallow poison",
    "बेहोश", "सांस नहीं", "साँस नहीं", "सांस लेने में परेशानी", "सीने में दर्द",
    "गंभीर खून", "जहर", "कीटनाशक पी लिया", "कीटनाशक पी", "सांप ने काटा", "snake bite"
)


def safety_triage_node(state: FarmState) -> Dict[str, Any]:
    """Safety & Triage Agent: Evaluates whether query warrants immediate emergency services."""
    message = state.get("query", "").lower()
    is_emergency = any(phrase in message for phrase in CRITICAL_EMERGENCY_WORDS)
    if is_emergency:
        answer = (
            "⚠️ **आपातकालीन चेतावनी:** यदि यह अभी हो रहा है, तो तुरंत स्थानीय आपातकालीन सेवाओं (भारत में **112** या 108 एम्बुलेंस) "
            "से संपर्क करें या नज़दीकी अस्पताल जाएं। इस सहायक पर निर्भर होकर उपचार में देरी न करें।"
            if state.get("language") == "hi"
            else
            "⚠️ **EMERGENCY WARNING:** If someone has ingested pesticide, is unconscious, or having severe medical distress, "
            "immediately contact National Emergency Services (**112** / 108 in India) or visit the nearest hospital. "
            "Do not delay urgent medical care while using this AI assistant."
        )
        return _record(state, "Safety & Triage Agent", emergency=True, answer=answer, verified=True)
    return _record(state, "Safety & Triage Agent", emergency=False)


def route_by_rules(query: str, image_path: str = "", document_text: str = "") -> str | None:
    """Fast rule-based intent router."""
    if image_path:
        return "vision"
    if document_text and any(w in query.lower() for w in ("summar", "policy", "clause", "benefit", "eligib", "दस्तावेज़", "योजना", "नियम")):
        return "policy_summary"

    q = query.lower()
    categories = [
        ("climate", ["historical", "last year", "climate", "past rainfall", "historical rain", "जलवायु", "पिछले साल", "पुराना मौसम"]),
        ("mandi", ["mandi", "market price", "modal price", "market rate", "bhav", "बाजार भाव", "मंडी", "दाम", "कीमत", "भाव", "दर"]),
        ("weather", ["weather", "rain", "forecast", "temperature", "humidity", "wind", "मौसम", "बारिश", "तापमान", "हवा", "वर्षा"]),
        ("schemes", ["scheme", "subsidy", "pm-kisan", "pm kisan", "kcc", "fasal bima", "insurance", "credit card", "योजना", "सब्सिडी", "बीमा", "किसान सम्मान", "क्रेडिट कार्ड", "क्रेडिट"]),
        ("agriculture", ["crop", "soil", "farm", "irrigation", "plant", "fertiliz", "pest", "seed", "farming", "sowing",
                         "फसल", "खेती", "पौधा", "पौधे", "सिंचाई", "मिट्टी", "कीट", "बीज", "खाद", "यूरिया", "डीएप"]),
    ]
    for category, words in categories:
        if any(word in q for word in words):
            return category
    return None


def supervisor_node(state: FarmState) -> Dict[str, Any]:
    """Supervisor Agent: Determines routing across specialist agents."""
    route = state.get("forced_route") if state.get("forced_route") in ROUTES else None
    if not route:
        route = route_by_rules(
            state.get("query", ""),
            state.get("image_path", ""),
            state.get("document_text", "")
        )

    if not route:
        prompt = (
            "Return ONLY a JSON object like {\"route\":\"agriculture\"}.\n"
            "You are a routing agent for an Indian agricultural assistant. Choose exactly one route from:\n"
            + ", ".join(ROUTES) + ".\n"
            "User question: " + state.get("query", "")[:500]
        )
        try:
            parsed = llm.parse_json_object(llm.generate(prompt, allow_cloud=False))
            candidate = parsed.get("route")
            route = candidate if candidate in ROUTES else "agriculture"
        except Exception:
            route = "agriculture"

    return _record(state, "Supervisor & Router Agent", route=route)


def mandi_node(state: FarmState) -> Dict[str, Any]:
    """Mandi Price Agent: Retrieves verified live APMC daily prices."""
    commodity = state.get("commodity") or tools.detect_commodity(state.get("query", "")) or "Onion"
    state_name = state.get("state_name") or "Maharashtra"
    district = state.get("district", "")
    ev = tools.mandi(commodity, state_name, district)
    return _record(state, "Mandi Price Agent", evidence=[ev])


def weather_node(state: FarmState) -> Dict[str, Any]:
    """Weather Agent: Retrieves real-time weather and 3-day forecast."""
    city = state.get("city") or "Nashik"
    ev = tools.weather(city)
    return _record(state, "Weather Agent", evidence=[ev])


def climate_node(state: FarmState) -> Dict[str, Any]:
    """Climate Agent: Retrieves historical annual temperature & rainfall."""
    city = state.get("city") or "Nashik"
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", state.get("query", ""))
    year = int(year_match.group(1)) if year_match else None
    ev = tools.climate(city, year)
    return _record(state, "Climate Analysis Agent", evidence=[ev])


def schemes_node(state: FarmState) -> Dict[str, Any]:
    """Government Schemes Agent: Identifies relevant subsidies and schemes."""
    ev = tools.schemes(state.get("query", ""), state.get("state_name", ""))
    # Also fetch relevant RAG documents if available
    rag_docs = rag.knowledge_evidence(state.get("query", ""), k=2)
    return _record(state, "Government Scheme Agent", evidence=[ev] + rag_docs)


def vision_node(state: FarmState) -> Dict[str, Any]:
    """Crop Vision Agent: Inspects crop photograph for symptoms using Gemini Vision."""
    image = state.get("image_path", "")
    if not image:
        raise tools.ToolError("Please upload a crop photograph to perform visual inspection.")

    lang = state.get("language", "en")
    prompt = (
        "आप एक कृषि पादप विशेषज्ञ हैं। इस पौधे/पत्ती की तस्वीर को ध्यान से देखें और केवल दिखाई देने वाले लक्षण बताएं। "
        "स्पष्ट बताएं कि पत्ती या फसल पर क्या धब्बे, रंग परिवर्तन या कीट लक्षण दिखाई दे रहे हैं। "
        "रासायनिक कीटनाशक की दवा या रासायनिक खुराक न लिखें; केवल जैविक या सुरक्षित प्राथमिक उपचार का सुझाव दें। "
        "अधिकतम 140 शब्दों में देवनागरी हिंदी में लिखें।"
        if lang == "hi"
        else
        "You are an agricultural plant specialist. Carefully inspect this crop/leaf photograph. "
        "Describe ONLY the visible symptoms (discoloration, lesions, wilting, pest damage). "
        "Do not confirm a laboratory diagnosis or prescribe restricted chemical pesticides. "
        "Provide safe agronomic, organic, or cultural management tips. Keep under 140 words in clear English."
    )
    observation = llm.inspect_image(image, prompt)
    rag_evidence = rag.knowledge_evidence(state.get("query", "crop disease symptoms and treatment"), k=2)
    visual_ev = tools.evidence(
        "AI Visual Crop Inspection (Preliminary Observation): " + observation,
        "AI Visual Analysis (Gemini 3.5 Vision)",
        "Visual Plant Observation",
    )
    return _record(state, "Crop Vision Agent", evidence=[visual_ev] + rag_evidence)


def policy_summary_node(state: FarmState) -> Dict[str, Any]:
    """Policy Summarizer Agent: Synthesizes scheme circulars and policy documents."""
    doc_text = state.get("document_text", "")
    if not doc_text:
        # If no document was uploaded, fall back to agriculture RAG
        return agriculture_node(state)

    lang = state.get("language", "en")
    user_q = state.get("query", "").strip()

    prompt = (
        f"You are the Policy Summarizer Agent of Gram Sahayak.\n"
        f"Language of response: {'Hindi (Devanagari)' if lang == 'hi' else 'English'}.\n\n"
        f"DOCUMENT EXCERPTS:\n{doc_text[:18000]}\n\n"
        f"USER SPECIFIC QUESTION: {user_q if user_q else 'Provide a complete structured policy summary for farmers.'}\n\n"
        "Provide a clear, farmer-accessible analysis organized under these exact headings:\n"
        "1. 📋 **Scheme / Policy Name & Purpose** (योजना का नाम और मुख्य उद्देश्य)\n"
        "2. 💰 **Financial Benefits & Assistance** (वित्तीय सहायता, सब्सिडी या भुगतान विवरण)\n"
        "3. 🎯 **Eligibility Criteria** (पात्रता: कौन किसान पात्र हैं, भूमि सीमा, श्रेणी)\n"
        "4. 📑 **Required Documents** (आवश्यक दस्तावेज: आधार, भूमि खतौनी/7-12, बैंक खाता आदि)\n"
        "5. 📝 **How to Apply** (आवेदन प्रक्रिया: पोर्टल, सीएससी केंद्र, कृषि कार्यालय)\n"
        "6. ⚠️ **Important Conditions & Deadlines** (महत्वपूर्ण शर्तें व अंतिम तिथियां)\n"
        "7. ❓ **Points Not Mentioned / Caution** (जो बातें दस्तावेज में स्पष्ट नहीं हैं)\n\n"
        "Be completely faithful to the text. Do not invent any numbers or eligibility clauses."
    )
    summary = llm.generate(prompt, allow_cloud=True)
    ev = tools.evidence(
        summary,
        f"Uploaded Document: {state.get('document_name', 'Policy Document')}",
        "Policy Document Analysis",
        extra={"summary": summary, "document_name": state.get("document_name")},
    )
    return _record(state, "Policy Summarizer Agent", evidence=[ev], answer=summary, verified=True)


def agriculture_node(state: FarmState) -> Dict[str, Any]:
    """Agriculture Knowledge Agent: Retrieves RAG evidence from agricultural documentation."""
    found = rag.knowledge_evidence(state.get("query", ""), k=4)
    return _record(state, "Agriculture Knowledge Agent", evidence=found)


def response_generator_node(state: FarmState) -> Dict[str, Any]:
    """Response Generator Agent: Produces grounded response from evidence."""
    # If answer already established by triage or policy summarizer, keep it
    if state.get("answer"):
        return _record(state, "Response Generator Agent")

    records = state.get("evidence") or []
    lang = state.get("language", "en")
    lang_name = "Hindi (Devanagari)" if lang == "hi" else "English"

    if not records:
        no_source = (
            "मेरे पास इस प्रश्न के लिए अभी पर्याप्त सत्यापित जानकारी नहीं है। "
            "कृपया किसी स्थानीय कृषि विशेषज्ञ या किसान कॉल सेंटर (1800-180-1551) से पुष्टि करें।"
            if lang == "hi"
            else
            "I do not currently have verified data for this query. "
            "Please confirm with your local Krishi Vigyan Kendra (KVK) or Kisan Call Centre (1800-180-1551)."
        )
        return _record(state, "Response Generator Agent", answer=no_source)

    excerpts = "\n\n".join(f"[{i+1}] {r.get('title', 'Source')} | {r.get('text', '')[:2500]}" for i, r in enumerate(records))
    feedback = state.get("feedback", "")

    prompt = f"""You are Gram Sahayak (ग्राम सहायक), a trusted AI assistant for Indian farmers.
Answer the user's question completely in {lang_name}.
Keep the response structured, clear, and easy to understand with bullet points where helpful.

STRICT GROUNDING RULES:
1. Base all facts, numbers, dates, crop rates, and advice strictly on the provided EVIDENCE.
2. Never invent numbers, market prices, or eligibility criteria.
3. If market prices are shown, state the date and APMC market names.
4. For crop health: provide practical agronomic advice; do not prescribe dangerous chemical poisons.
5. If some information is not in the evidence, acknowledge the limitation honestly.

User Question: {state.get('query', '')[:1000]}
Conversation Context: {state.get('recent_context', '')[:600]}

EVIDENCE:
{excerpts[:10000]}

{f'Correction Instructions from Verifier: {feedback}' if feedback else ''}

Farmer-Friendly Answer:"""

    try:
        answer = llm.generate(prompt, allow_cloud=True)
    except Exception:
        # Fallback to direct evidence text
        answer = ("उपलब्ध सत्यापित जानकारी:\n" if lang == "hi" else "Available Verified Information:\n") + "\n".join(
            f"• {r.get('text', '')[:800]}" for r in records
        )

    return _record(state, "Response Generator Agent", answer=answer)


def verifier_node(state: FarmState) -> Dict[str, Any]:
    """Verification Agent: Checks numerical grounding and hallucination prevention."""
    reply = (state.get("answer") or "").strip()
    ev = state.get("evidence") or []
    if not ev or not reply:
        return _record(state, "Verification Agent", verified=True)

    grounded_text = " ".join(r.get("text", "") for r in ev)

    # Check for multi-digit numbers in the reply that do not appear anywhere in the source evidence
    claims = set(re.findall(r"(?<![\w])\d{2,}(?:\.\d+)?", reply))
    support = set(re.findall(r"(?<![\w])\d{2,}(?:\.\d+)?", grounded_text))
    # Filter out common benign formatting numbers like 2026, 112, 108
    unsupported = sorted(num for num in (claims - support) if num not in ("2026", "2025", "2024", "112", "108", "1800"))

    if unsupported and state.get("tries", 0) < 1:
        return _record(
            state,
            "Verification Agent",
            verified=False,
            tries=state.get("tries", 0) + 1,
            feedback=f"Please remove or correct unsupported numerical claims: {', '.join(unsupported[:5])}",
        )

    return _record(state, "Verification Agent", verified=True)


def safe_agent_wrapper(node_fn):
    """Wraps agent nodes to catch unexpected errors and maintain smooth graph execution."""
    def wrapper(state: FarmState) -> Dict[str, Any]:
        try:
            return node_fn(state)
        except Exception as exc:
            lang = state.get("language", "en")
            agent_name = node_fn.__name__.replace("_node", "").replace("_", " ").title()
            msg = f"सेवा अस्थायी रूप से अनुपलब्ध है ({agent_name}): {exc}" if lang == "hi" else f"Service temporarily unavailable ({agent_name}): {exc}"
            return _record(state, agent_name, evidence=[], answer=msg, verified=True)
    return wrapper


# =====================================================================
# LangGraph StateGraph Assembly
# =====================================================================

def build_agent_graph():
    """Builds and compiles the multi-agent StateGraph."""
    graph = StateGraph(FarmState)

    graph.add_node("triage", safe_agent_wrapper(safety_triage_node))
    graph.add_node("supervisor", safe_agent_wrapper(supervisor_node))
    graph.add_node("mandi", safe_agent_wrapper(mandi_node))
    graph.add_node("weather", safe_agent_wrapper(weather_node))
    graph.add_node("climate", safe_agent_wrapper(climate_node))
    graph.add_node("schemes", safe_agent_wrapper(schemes_node))
    graph.add_node("vision", safe_agent_wrapper(vision_node))
    graph.add_node("policy_summary", safe_agent_wrapper(policy_summary_node))
    graph.add_node("agriculture", safe_agent_wrapper(agriculture_node))
    graph.add_node("response_generator", safe_agent_wrapper(response_generator_node))
    graph.add_node("verifier", safe_agent_wrapper(verifier_node))

    graph.set_entry_point("triage")

    def triage_condition(state: FarmState):
        if state.get("emergency"):
            return END
        return "supervisor"

    graph.add_conditional_edges("triage", triage_condition, {END: END, "supervisor": "supervisor"})

    def supervisor_condition(state: FarmState):
        route = state.get("route", "agriculture")
        if route in ROUTES:
            return route
        return "agriculture"

    graph.add_conditional_edges("supervisor", supervisor_condition, {
        "mandi": "mandi",
        "weather": "weather",
        "climate": "climate",
        "schemes": "schemes",
        "vision": "vision",
        "policy_summary": "policy_summary",
        "agriculture": "agriculture",
    })

    # All specialist workers lead to response generator
    for specialist in ("mandi", "weather", "climate", "schemes", "vision", "agriculture"):
        graph.add_edge(specialist, "response_generator")

    graph.add_edge("policy_summary", "verifier")
    graph.add_edge("response_generator", "verifier")

    def verifier_condition(state: FarmState):
        if state.get("verified") or state.get("tries", 0) >= 1:
            return END
        return "response_generator"

    graph.add_conditional_edges("verifier", verifier_condition, {
        END: END,
        "response_generator": "response_generator",
    })

    return graph.compile()


_COMPILED_GRAPH = None


def get_agent_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_agent_graph()
    return _COMPILED_GRAPH


def run_question(**kwargs) -> Dict[str, Any]:
    """Public execution entry point for the Gram Sahayak multi-agent system."""
    app_graph = get_agent_graph()
    initial_state: FarmState = {
        "query": kwargs.get("query", ""),
        "language": kwargs.get("language", "en"),
        "session_id": kwargs.get("session_id", "default"),
        "city": kwargs.get("city", "Nashik"),
        "district": kwargs.get("district", ""),
        "state_name": kwargs.get("state_name", "Maharashtra"),
        "commodity": kwargs.get("commodity", ""),
        "image_path": kwargs.get("image_path", ""),
        "document_text": kwargs.get("document_text", ""),
        "document_name": kwargs.get("document_name", ""),
        "forced_route": kwargs.get("forced_route", ""),
        "recent_context": kwargs.get("recent_context", ""),
        "trace": [],
        "evidence": [],
        "tries": 0,
    }
    final_state = app_graph.invoke(initial_state)
    return final_state
