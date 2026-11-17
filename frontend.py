"""Gram Sahayak • Professional Agricultural Multi-Agent AI Interface.

Engineered with:
- Sunrise landing hero welcome section (Full-screen image, scrolls away naturally).
- Seamless full-width container (zero side borders or pillarbox lines).
- Clean Language Switching: strictly English OR strictly Hindi (never concatenated).
- Compact properly-sized Ask Assistant chatbox.
- Elegant warm-earth palette (forest green, sunrise amber — zero neon or cold dark-blue).
- Hands-free Voice Assistant with automatic silence detection.
- Live Mandi Prices (data.gov.in Agmarknet + CEDA fallback).
- Live Weather (Open-Meteo), Climate History (NASA POWER).
- Policy & Document Summarizer (PDF / DOCX / TXT).
- Multimodal Crop Health Doctor (Gemini 3.5 Vision).
- Live 11-Agent Roster via agents.py.
"""
from __future__ import annotations

import base64
import html
import os
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr
import numpy as np
import pandas as pd
import requests

from app import config, db, tools, rag
from app.agents import list_agents, run_question
from app.services.documents import extract_text
from app.voice import text_to_speech, transcribe

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

# Load sunrise crop-field hero background image as data URI
HERO_BG_PATH = Path(__file__).parent / "static" / "hero_bg.jpg"
if HERO_BG_PATH.exists():
    with open(HERO_BG_PATH, "rb") as f:
        _b64_bg = base64.b64encode(f.read()).decode("ascii")
    HERO_BG_URI = f"data:image/jpeg;base64,{_b64_bg}"
else:
    HERO_BG_URI = ""


# =====================================================================
# Dual Backend Caller (FastAPI API with Direct In-Process Fallback)
# =====================================================================

def backend_call(path: str, method: str = "GET", params: dict = None, data: dict = None, files: dict = None) -> dict:
    try:
        if method == "DELETE":
            resp = requests.delete(f"{BACKEND}{path}", timeout=10)
        elif method == "POST":
            resp = requests.post(
                f"{BACKEND}{path}",
                json=data if files is None else None,
                data=data if files is not None else None,
                files=files,
                timeout=180,
            )
        else:
            resp = requests.get(f"{BACKEND}{path}", params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        if path == "/api/chat":
            q_args = data or {}
            res = run_question(**q_args)
            sources = [
                {"title": e.get("title"), "source": e.get("source"), "as_of": e.get("as_of")}
                for e in res.get("evidence", [])
            ]
            return {
                "answer": res.get("answer", ""),
                "language": q_args.get("language", "en"),
                "session_id": q_args.get("session_id", "demo"),
                "route": res.get("route", "agriculture"),
                "agents_executed": res.get("trace", []),
                "verified": res.get("verified", False),
                "sources": sources,
            }
        elif path == "/api/weather":
            city = (params or {}).get("city", "Nashik")
            return tools.weather(city)
        elif path == "/api/mandi":
            p = params or {}
            return tools.mandi(
                p.get("commodity", "Onion"),
                p.get("state_name", "Maharashtra"),
                p.get("district", ""),
            )
        elif path == "/api/climate":
            p = params or {}
            return tools.climate(p.get("city", "Nashik"), p.get("year"))
        elif path == "/api/schemes":
            p = params or {}
            return tools.schemes(p.get("query", "crop insurance"), p.get("state", ""))
        elif path.startswith("/api/history"):
            sess = path.split("/")[-1]
            if method == "DELETE":
                db.delete_user_data(sess)
                return {"deleted": True}
            return db.get_history(sess)
        elif path == "/api/profile":
            if method == "POST":
                db.save_profile(**data)
                return {"saved": True}
        raise


# =====================================================================
# Strict Single-Language Dictionaries
# =====================================================================

LANG_DATA = {
    "en": {
        "brand_name": "Gram Sahayak",
        "brand_sub": "Autonomous Multi-Agent AI for Indian Agriculture",
        "status_agents": "11 AI Agents Active",
        "status_services": "Live Agmarknet & Open-Meteo",
        "hero_tag": "ADVANCED AGENTIC AI FOR INDIAN FARMERS",
        "hero_title_1": "Grow more.",
        "hero_title_2": "Prosper more.",
        "hero_desc": "Soil, weather, crop health, live mandi prices, and government policies fused into an autonomous multi-agent intelligence engine — built for every Indian farmer.",
        "lang_label": "Language",
        "city_label": "City / Town",
        "district_label": "District (Optional)",
        "commodity_label": "Main Commodity",
        "privacy_tip": "🔒 Local & Private: All session memory is stored securely on your local computer.",
        "tab_chat": "💬 Assistant & Voice",
        "tab_mandi": "📈 Mandi Prices",
        "tab_weather": "🌦️ Live Weather",
        "tab_climate": "📊 Climate History",
        "tab_policy": "📄 Policy Summarizer",
        "tab_crop": "🌿 Crop Doctor",
        "tab_agents": "🤖 Agent Roster",
        "tab_profile": "👤 Profile & History",
        "chat_header": "Ask any farming question via Text or Hands-Free Voice (auto-detects silence)",
        "chat_placeholder": "Ask anything (e.g. Onion rate in Nashik? Will it rain? PM Kisan rules?)",
        "chat_label": "Conversation History",
        "btn_ask": "Ask Assistant",
        "btn_clear": "Clear Chat",
        "mic_label": "🎙️ Hands-Free Voice (Auto Silence Detection)",
        "speak_label": "🔊 Read answers aloud",
        "mandi_header": "Daily Market Prices from Agmarknet (data.gov.in) with CEDA Fallback",
        "crop_label": "Commodity / Crop",
        "state_label": "State",
        "dist_label": "District / APMC",
        "btn_mandi": "Fetch Live Mandi Prices",
        "mandi_table_label": "APMC Mandi Rates",
        "weather_header": "Real-time Weather & 3-Day Forecast via Open-Meteo",
        "btn_weather": "Fetch Live Forecast",
        "weather_table_label": "3-Day Agricultural Forecast",
        "climate_header": "Historical Agro-Climatic Trends via NASA POWER (1981–Present)",
        "year_label": "Historical Year",
        "btn_climate": "Analyze Climate History",
        "policy_header": "Upload Government Scheme Circulars, Insurance Policies, or Notifications",
        "file_label": "Upload Policy Document (PDF, DOCX, TXT)",
        "policy_q_label": "Specific Question on Document (Optional)",
        "policy_q_ph": "e.g., What are the land requirements? What documents do I need to apply?",
        "btn_policy": "Summarize Policy Document",
        "crop_header": "Multimodal Plant & Leaf Symptom Inspection via Google Gemini 3.5",
        "crop_warn": "⚠️ Advisory: AI provides preliminary symptom observations. Always verify with your local Krishi Vigyan Kendra (KVK).",
        "crop_img_label": "Upload Crop Leaf or Plant Photo",
        "btn_crop": "Analyze Crop Symptoms",
        "agents_header": "11 Specialized Autonomous Agents Orchestrated with LangGraph",
        "profile_header": "Local Preferences & Session Privacy Control",
        "home_city": "My Home Town / City",
        "home_dist": "My Home District",
        "home_crop": "My Primary Crop",
        "consent": "I consent to store my farming preferences locally on this computer",
        "btn_save": "Save Preferences",
        "btn_view_hist": "View Chat History",
        "btn_del_hist": "Delete Local Data & Reset",
    },
    "hi": {
        "brand_name": "ग्राम सहायक",
        "brand_sub": "भारतीय कृषि हेतु बहु-एजेंट स्वायत्त एआई",
        "status_agents": "11 स्वायत्त एआई एजेंट सक्रिय",
        "status_services": "ताज़ा Agmarknet एवं Open-Meteo",
        "hero_tag": "भारतीय किसानों के लिए उन्नत स्वायत्त एआई",
        "hero_title_1": "अधिक उपज।",
        "hero_title_2": "समृद्ध किसान।",
        "hero_desc": "मिट्टी, मौसम, फसल रोग, दैनिक मंडी भाव और सरकारी नीतियां — भारतीय किसानों के लिए एक एकीकृत स्वायत्त एआई इंजन।",
        "lang_label": "भाषा",
        "city_label": "शहर / कस्बा",
        "district_label": "जिला (वैकल्पिक)",
        "commodity_label": "मुख्य फसल",
        "privacy_tip": "🔒 स्थानीय व गोपनीय: आपकी बातचीत केवल आपके कंप्यूटर में सुरक्षित रहती है।",
        "tab_chat": "💬 सहायक से पूछें",
        "tab_mandi": "📈 ताज़ा मंडी भाव",
        "tab_weather": "🌦️ मौसम पूर्वानुमान",
        "tab_climate": "📊 ऐतिहासिक जलवायु",
        "tab_policy": "📄 नीति सारांश",
        "tab_crop": "🌿 फसल रोग जांच",
        "tab_agents": "🤖 11 एजेंट रोस्टर",
        "tab_profile": "👤 प्रोफ़ाइल एवं इतिहास",
        "chat_header": "लिखकर या बोलकर कृषि संबंधी कोई भी प्रश्न पूछें",
        "chat_placeholder": "यहाँ प्रश्न पूछें (उदा. नासिक में प्याज का भाव? कल बारिश होगी? पीएम किसान नियम?)",
        "chat_label": "बातचीत का इतिहास",
        "btn_ask": "पूछें",
        "btn_clear": "चैट साफ़ करें",
        "mic_label": "🎙️ हैंड्स-फ्री आवाज़ (साइलेंस स्वतः पहचान)",
        "speak_label": "🔊 उत्तर बोलकर सुनाएं",
        "mandi_header": "सरकारी Agmarknet (data.gov.in) से ताज़ा दैनिक मंडी भाव",
        "crop_label": "फसल / वस्तु का नाम",
        "state_label": "राज्य",
        "dist_label": "जिला / मंडी",
        "btn_mandi": "ताज़ा मंडी भाव देखें",
        "mandi_table_label": "मंडी दरें",
        "weather_header": "Open-Meteo द्वारा वास्तविक समय मौसम एवं 3-दिवसीय पूर्वानुमान",
        "btn_weather": "ताज़ा मौसम देखें",
        "weather_table_label": "3-दिवसीय मौसम पूर्वानुमान",
        "climate_header": "NASA POWER द्वारा 1981 से ऐतिहासिक जलवायु विश्लेषण",
        "year_label": "विश्लेषण हेतु वर्ष",
        "btn_climate": "ऐतिहासिक जलवायु देखें",
        "policy_header": "सरकारी योजना, अधिसूचना अथवा बीमा पॉलिसी दस्तावेज़ अपलोड करें",
        "file_label": "दस्तावेज़ अपलोड करें (PDF, DOCX, TXT)",
        "policy_q_label": "दस्तावेज़ पर विशेष प्रश्न (वैकल्पिक)",
        "policy_q_ph": "उदा. कौन से किसान पात्र हैं? क्या-क्या दस्तावेज लगेंगे?",
        "btn_policy": "दस्तावेज़ का सारांश निकालें",
        "crop_header": "जेमिनी 3.5 विज़न द्वारा फसल / पत्ती की फोटो की जांच",
        "crop_warn": "⚠️ सलाह: एआई केवल दृश्य लक्षणों का प्राथमिक विश्लेषण करता है। किसी भी छिड़काव से पहले कृषि विज्ञान केंद्र (KVK) से सलाह लें।",
        "crop_img_label": "फसल / पत्ती की फोटो अपलोड करें",
        "btn_crop": "फसल के लक्षणों की जांच करें",
        "agents_header": "LangGraph द्वारा संचालित 11 स्वायत्त एजेंट",
        "profile_header": "स्थानीय सेटिंग्स एवं डेटा गोपनीयता नियंत्रण",
        "home_city": "मेरा शहर / गांव",
        "home_dist": "मेरा जिला",
        "home_crop": "मेरी मुख्य फसल",
        "consent": "मैं इस कंप्यूटर में इन प्राथमिकताओं को सहेजने की सहमति देता/देती हूँ",
        "btn_save": "प्राथमिकताएं सहेजें",
        "btn_view_hist": "बातचीत का इतिहास देखें",
        "btn_del_hist": "इतिहास हटाएं (डेटा रीसेट)",
    },
}


# =====================================================================
# CSS — Elegant Warm Earth Palette, No Side Lines, Full Width
# =====================================================================

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&family=Outfit:wght@500;600;700;800;900&display=swap');

/* ── Colour Tokens ───────────────────────────────────────────── */
:root {{
  --bg:          #0d110e;
  --bg2:         #111a13;
  --card:        #162019;
  --card2:       #1c2b1f;
  --border:      rgba(255,255,255,0.08);
  --green:       #22863a;
  --green-h:     #2ea84f;
  --emerald:     #34d058;
  --amber:       #f0a500;
  --amber-lt:    #fcd34d;
  --white:       #f0f4f1;
  --muted:       #8fa899;
  --body:        #c4d4c8;
  --accent-glow: rgba(34, 134, 58, 0.18);
}}

/* ── RESET — kill every Gradio default margin/border/bg ───────── */
*,*::before,*::after {{ box-sizing: border-box; }}

html, body {{
  margin: 0 !important; padding: 0 !important;
  width: 100% !important; max-width: 100% !important;
  background: var(--bg) !important;
  overflow-x: hidden !important;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
}}

/* Remove every Gradio wrapper that could add side-lines */
.gradio-container,
.gradio-container > .main,
.gradio-container > .main > .wrap,
div#root,
.wrap.svelte-1byz9vf {{
  margin: 0 !important; padding: 0 !important;
  width: 100% !important; max-width: 100% !important;
  background: var(--bg) !important;
  border: none !important;
  box-shadow: none !important;
  min-height: unset !important;
}}

/* ── HERO — full-screen landing image, scrolls away naturally ── */
#gs-hero {{
  position: relative;
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 0 24px 60px;
  background:
    linear-gradient(to bottom,
      rgba(13,17,14,0.35) 0%,
      rgba(13,17,14,0.60) 55%,
      rgba(13,17,14,0.92) 82%,
      var(--bg) 100%
    ),
    url('{HERO_BG_URI}') center 40% / cover no-repeat;
  overflow: hidden;
}}

/* Thin amber divider line at bottom of hero */
#gs-hero::after {{
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--amber), transparent);
  opacity: 0.4;
}}

.hero-eyebrow {{
  display: inline-block;
  font-family: 'Outfit', sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--amber);
  background: rgba(240,165,0,0.12);
  border: 1px solid rgba(240,165,0,0.3);
  border-radius: 999px;
  padding: 5px 16px;
  margin-bottom: 28px;
  backdrop-filter: blur(4px);
}}

.hero-h1 {{
  font-family: 'Outfit', sans-serif;
  font-size: clamp(44px, 7vw, 88px);
  font-weight: 900;
  line-height: 1.0;
  letter-spacing: -2px;
  color: #ffffff;
  margin: 0 0 20px;
  text-shadow: 0 4px 32px rgba(0,0,0,0.6);
}}
.hero-h1 span {{ color: var(--emerald); }}

.hero-p {{
  max-width: 680px;
  font-size: 17px;
  line-height: 1.65;
  color: rgba(255,255,255,0.80);
  margin: 0 auto 36px;
}}

.hero-scroll {{
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.4);
  animation: bounce 2.4s ease-in-out infinite;
}}
.hero-scroll svg {{ width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; }}

@keyframes bounce {{
  0%,100% {{ transform: translateX(-50%) translateY(0); }}
  50%      {{ transform: translateX(-50%) translateY(8px); }}
}}

/* ── DASHBOARD — solid dark below the hero ────────────────────── */
#gs-dash {{
  background: var(--bg);
  width: 100%;
}}

.dash-inner {{
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 20px 80px;
}}

/* ── NAV BAR ──────────────────────────────────────────────────── */
.gs-nav {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  margin-bottom: 18px;
}}
.gs-brand-name {{
  font-family: 'Outfit', sans-serif;
  font-size: 20px;
  font-weight: 800;
  color: var(--white);
}}
.gs-brand-sub {{
  font-size: 12px;
  color: var(--emerald);
  margin-top: 2px;
  opacity: 0.85;
}}
.gs-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}

.badge-green {{
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 600;
  padding: 4px 12px;
  background: rgba(52,208,88,0.10);
  border: 1px solid rgba(52,208,88,0.28);
  border-radius: 999px;
  color: #6ee7a0;
}}
.badge-amber {{
  display: inline-flex; align-items: center;
  font-size: 12px; font-weight: 600;
  padding: 4px 12px;
  background: rgba(240,165,0,0.10);
  border: 1px solid rgba(240,165,0,0.28);
  border-radius: 999px;
  color: var(--amber-lt);
}}
.dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--emerald); }}

/* ── CONTEXT STRIP ────────────────────────────────────────────── */
.ctx-strip {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 16px;
}}

/* ── TABS ─────────────────────────────────────────────────────── */
.tabs {{ background: transparent !important; border: none !important; }}

.tab-nav {{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  padding: 4px !important;
  gap: 3px !important;
  margin-bottom: 14px !important;
  overflow-x: auto !important;
  flex-wrap: nowrap !important;
}}
.tab-nav button {{
  border-radius: 10px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--muted) !important;
  border: none !important;
  padding: 8px 14px !important;
  white-space: nowrap !important;
  transition: all 0.18s ease !important;
}}
.tab-nav button.selected,
.tab-nav button[aria-selected="true"] {{
  background: var(--green) !important;
  color: #fff !important;
}}
.tab-nav button:hover:not(.selected):not([aria-selected="true"]) {{
  background: rgba(255,255,255,0.05) !important;
  color: var(--white) !important;
}}

/* ── CARDS / PANELS ───────────────────────────────────────────── */
.gs-card {{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  padding: 18px !important;
  margin-bottom: 14px !important;
}}

/* ── COMPACT CHATBOT ──────────────────────────────────────────── */
.compact-chat .wrap {{
  height: 280px !important;
  min-height: 280px !important;
  max-height: 280px !important;
}}
.compact-chat {{
  border-radius: 12px !important;
  overflow: hidden !important;
}}

/* ── INPUTS ───────────────────────────────────────────────────── */
input, textarea, select {{
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  color: var(--white) !important;
  border-radius: 10px !important;
  font-size: 14px !important;
}}
input:focus, textarea:focus {{
  border-color: var(--emerald) !important;
  box-shadow: 0 0 0 2px rgba(52,208,88,0.15) !important;
  outline: none !important;
}}
label {{ color: var(--muted) !important; font-size: 13px !important; font-weight: 500 !important; }}

/* ── BUTTONS ──────────────────────────────────────────────────── */
button.primary,
.gr-button-primary {{
  background: var(--green) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 10px !important;
  color: #fff !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  padding: 9px 20px !important;
  transition: background 0.18s ease !important;
}}
button.primary:hover,
.gr-button-primary:hover {{
  background: var(--green-h) !important;
}}
button.stop,
.gr-button-stop {{
  background: rgba(220,38,38,0.15) !important;
  border-color: rgba(220,38,38,0.4) !important;
  color: #fca5a5 !important;
}}

/* ── METRIC GRID ──────────────────────────────────────────────── */
.gs-metric-block {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px;
  margin: 12px 0 16px;
}}
.gs-metric-block h3 {{
  margin: 0 0 14px;
  font-family: 'Outfit', sans-serif;
  font-size: 17px;
  font-weight: 700;
  color: var(--emerald);
}}
.gs-metric-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin-top: 10px;
}}
.gs-metric-item {{
  background: var(--card2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
}}
.gs-metric-item .lbl {{
  display: block; color: var(--muted); font-size: 12px; margin-bottom: 4px;
}}
.gs-metric-item .val {{
  display: block; color: var(--white);
  font-family: 'Outfit', sans-serif;
  font-size: 20px; font-weight: 800;
}}

/* ── AGENT CARDS ──────────────────────────────────────────────── */
.gs-agent-card {{
  background: var(--card2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  transition: border-color 0.2s;
}}
.gs-agent-card:hover {{ border-color: rgba(52,208,88,0.35); }}
.gs-agent-card h4 {{
  margin: 0 0 5px;
  font-size: 15px; font-weight: 700;
  color: var(--emerald);
}}
.gs-agent-card p {{
  margin: 3px 0; font-size: 13px;
  color: var(--body); line-height: 1.5;
}}

/* ── RADIO (Language) ─────────────────────────────────────────── */
.gs-lang-radio label {{ color: var(--white) !important; font-weight: 600 !important; font-size: 14px !important; }}
.gs-lang-radio input[type=radio] {{ accent-color: var(--emerald) !important; }}

/* Hide Gradio footer */
footer {{ display: none !important; }}

/* ── Markdown body ────────────────────────────────────────────── */
.prose, .markdown-body {{ color: var(--body) !important; }}

/* Dataframe tweaks */
.dataframe {{ background: var(--card2) !important; color: var(--white) !important; }}
.dataframe th {{ background: var(--card) !important; color: var(--emerald) !important; font-weight: 700 !important; }}
.dataframe td {{ border-color: var(--border) !important; }}
"""


# =====================================================================
# UI Helper Functions
# =====================================================================

def render_sources(result: dict) -> str:
    sources = result.get("sources", [])
    if not sources:
        return "No external sources required for this response."
    lines = []
    for i, s in enumerate(sources, 1):
        title = s.get("title") or "Source"
        url = s.get("source") or ""
        as_of = s.get("as_of") or ""
        link_md = f"[{title}]({url})" if url.startswith("http") else f"**{title}**"
        lines.append(f"{i}. {link_md} • `{as_of}`")
    return "\n\n".join(lines)


def agent_trace(result: dict) -> str:
    trace = result.get("agents_executed", [])
    if not trace:
        return "No agents executed."
    return " ➔ ".join(trace)


def metric_card(title: str, metrics: List[Tuple[str, Any]], footer: str = "") -> str:
    items = "".join(
        f"<div class='gs-metric-item'><span class='lbl'>{html.escape(str(lbl))}</span><span class='val'>{html.escape(str(val))}</span></div>"
        for lbl, val in metrics
    )
    footer_html = f"<div style='margin-top:10px;font-size:12px;color:#6ee7a0;'>{html.escape(footer)}</div>" if footer else ""
    return (
        f"<div class='gs-metric-block'>"
        f"<h3>{html.escape(title)}</h3>"
        f"<div class='gs-metric-grid'>{items}</div>"
        f"{footer_html}</div>"
    )


def hero_html_str(t: dict) -> str:
    return f"""<div id="gs-hero">
  <div class="hero-eyebrow">🌾 {t['hero_tag']}</div>
  <h1 class="hero-h1">{t['hero_title_1']}<br><span>{t['hero_title_2']}</span></h1>
  <p class="hero-p">{t['hero_desc']}</p>
  <div class="hero-scroll">
    <svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
    SCROLL
  </div>
</div>"""


def nav_html_str(t: dict) -> str:
    # Always show bilingual brand name in the nav pill (Gram Sahayak • ग्राम सहायक)
    brand_en = "Gram Sahayak"
    brand_hi = "ग्राम सहायक"
    return f"""<div class="gs-nav">
  <div>
    <div class="gs-brand-name">🌾 {brand_en} • <span style="color:var(--emerald);font-size:17px;">{brand_hi}</span></div>
    <div class="gs-brand-sub">{t['brand_sub']}</div>
  </div>
  <div class="gs-badges">
    <div class="badge-green"><span class="dot"></span>{t['status_agents']}</div>
    <div class="badge-amber">⚡ {t['status_services']}</div>
  </div>
</div>"""


def get_agent_cards_html() -> str:
    agents = list_agents()
    cards = []
    for a in agents:
        tools_str = ", ".join(a.get("tools", []))
        sources_str = ", ".join(a.get("data_sources", []))
        card = f"""<div class='gs-agent-card'>
            <h4>🤖 {html.escape(a['name'])} — <i style='font-weight:400;color:#6ee7a0;'>{html.escape(a['role'])}</i></h4>
            <p><b>Description:</b> {html.escape(a['description'])}</p>
            <p><b>Tools:</b> {html.escape(tools_str)}</p>
            <p><b>Data Sources:</b> {html.escape(sources_str)}</p>
            <p><b>Engine:</b> <span style='color:var(--emerald);font-weight:600;'>{html.escape(a.get('model','LangGraph Node'))}</span></p>
        </div>"""
        cards.append(card)
    return "".join(cards)


# =====================================================================
# Core Feature Handlers
# =====================================================================

def send_chat(question, history, language, city, district, commodity, session, speak):
    history = list(history or [])
    if not question or not question.strip():
        return history, "", "", None, "", ""
    payload = {
        "query": question.strip(),
        "language": language,
        "city": city or "Nashik",
        "district": district or "",
        "commodity": commodity or "",
        "session_id": session,
    }
    result = backend_call("/api/chat", method="POST", data=payload)
    answer = result.get("answer", "")
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    audio_file = None
    if speak and answer:
        try:
            audio_file = text_to_speech(answer, language=language)
        except Exception:
            pass
    return history, "", render_sources(result), audio_file, agent_trace(result), answer


def process_voice_chat(audio_path, history, language, city, district, commodity, session):
    history = list(history or [])
    if not audio_path:
        return history, None, "", None, "", ""
    spoken_text = transcribe(audio_path, preferred_language=language)
    if not spoken_text or not spoken_text.strip():
        msg = "आवाज स्पष्ट नहीं सुनाई दी।" if language == "hi" else "No clear speech detected. Please try again."
        return history, None, "", None, "", msg
    payload = {
        "query": spoken_text,
        "language": language,
        "city": city or "Nashik",
        "district": district or "",
        "commodity": commodity or "",
        "session_id": session,
    }
    result = backend_call("/api/chat", method="POST", data=payload)
    answer = result.get("answer", "")
    history.append({"role": "user", "content": f"🎙️ {spoken_text}"})
    history.append({"role": "assistant", "content": answer})
    audio_file = None
    try:
        audio_file = text_to_speech(answer, language=language)
    except Exception:
        pass
    return history, None, render_sources(result), audio_file, agent_trace(result), answer


def stream_auto_silence(chunk, state, history, language, city, district, commodity, session):
    state = state or {"chunks": [], "sr": 16000, "speech": False, "quiet": 0.0, "cooldown": 0.0, "length": 0.0}
    history = list(history or [])
    blanks = (gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip())
    if not chunk or chunk[1] is None:
        return (state, *blanks)
    rate, values = chunk
    if rate <= 0:
        return (state, *blanks)
    samples = np.asarray(values)
    if samples.dtype.kind in ("i", "u"):
        samples = samples.astype("float32") / 32768.0
    else:
        samples = samples.astype("float32")
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    duration = samples.size / rate
    if samples.size == 0:
        return (state, *blanks)
    if time.monotonic() < state.get("cooldown", 0.0):
        return (state, *blanks)
    rms = float(np.sqrt(np.mean(samples ** 2)))
    voiced = rms > 0.016
    if voiced:
        state["speech"] = True
        state["quiet"] = 0.0
    elif state.get("speech"):
        state["quiet"] = state.get("quiet", 0.0) + duration
    if state.get("speech"):
        state["chunks"].append(samples)
        state["sr"] = rate
        state["length"] = state.get("length", 0.0) + duration
    if state.get("speech") and state.get("quiet", 0.0) >= 1.0 and state.get("length", 0) >= 0.6:
        import soundfile as sf
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            tmp_audio = fh.name
        try:
            full_audio = np.concatenate(state["chunks"])
            sf.write(tmp_audio, full_audio, state["sr"])
            new_hist, _, citations, audio_reply, trace, answer = process_voice_chat(
                tmp_audio, history, language, city, district, commodity, session
            )
            status_msg = "✅ Silence detected — response ready!" if language == "en" else "✅ चुप्पी पहचानी गई — उत्तर तैयार!"
        except Exception as exc:
            new_hist = history
            status_msg = f"Voice error: {exc}"
            citations, audio_reply, trace, answer = "", None, "", f"Error: {exc}"
        finally:
            Path(tmp_audio).unlink(missing_ok=True)
        state = {"chunks": [], "sr": rate, "speech": False, "quiet": 0.0, "cooldown": time.monotonic() + 3.0, "length": 0.0}
        return state, new_hist, status_msg, citations, audio_reply, trace, answer
    status_str = "🟢 Speaking detected..." if state.get("speech") else "🎙️ Ready — speak into microphone..."
    return (state, gr.skip(), status_str, *blanks[3:])


def mandi_ui(commodity, state, district):
    res = backend_call("/api/mandi", params={"commodity": commodity, "state_name": state, "district": district})
    data = res.get("data", {})
    records = data.get("records", [])
    df = pd.DataFrame(records)
    latest_date = data.get("latest_reported_date", "N/A")
    record_count = data.get("record_count", len(df))
    avg_price = data.get("avg_modal_price")
    if avg_price is None and not df.empty and "modal_price" in df.columns:
        nums = pd.to_numeric(df["modal_price"], errors="coerce").dropna()
        avg_price = f"₹ {nums.mean():.0f}" if not nums.empty else "N/A"
    else:
        avg_price = f"₹ {avg_price}/quintal" if avg_price else "N/A"
    min_price = data.get("min_overall", "N/A")
    max_price = data.get("max_overall", "N/A")
    provider = data.get("provider", "Agmarknet (data.gov.in) / CEDA")
    summary = metric_card(
        f"Mandi Rates • {data.get('commodity', commodity)} ({provider})",
        [
            ("Latest Arrival Date", latest_date),
            ("Average Modal Price", avg_price),
            ("Price Range", f"₹ {min_price} – ₹ {max_price}"),
            ("APMC Mandis Reported", record_count),
        ],
        footer=f"Source: {res.get('title', 'Agmarknet / CEDA')} • Rates in INR per quintal (100 kg)",
    )
    clean_df = pd.DataFrame()
    if not df.empty:
        col_map = {
            "market": "APMC Market", "district": "District", "commodity": "Commodity",
            "variety": "Variety", "arrival_date": "Arrival Date",
            "min_price": "Min Rate (₹)", "max_price": "Max Rate (₹)", "modal_price": "Modal Rate (₹/q)",
        }
        clean_df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    note = f"**Verification:** {res.get('text', '')}"
    return summary, note, clean_df, f"Source: [{res.get('title','Mandi data')}]({res.get('source','')})"


def weather_ui(city):
    res = backend_call("/api/weather", params={"city": city})
    data = res.get("data", {})
    current = data.get("current", {})
    daily = data.get("daily", {})
    location = data.get("location", {})
    summary = metric_card(
        f"Live Weather • {location.get('name', city)}, {location.get('state', '')}".strip(", "),
        [
            ("Temperature", f"{current.get('temperature_2m', 'N/A')} °C"),
            ("Relative Humidity", f"{current.get('relative_humidity_2m', 'N/A')} %"),
            ("Precipitation", f"{current.get('precipitation', '0')} mm"),
            ("Wind Speed", f"{current.get('wind_speed_10m', 'N/A')} km/h"),
        ],
        footer=f"Observation: {current.get('time', 'Live')} Asia/Kolkata • Source: Open-Meteo",
    )
    forecast_df = pd.DataFrame({
        "Date": daily.get("time", []),
        "Max Temp (°C)": daily.get("temperature_2m_max", []),
        "Min Temp (°C)": daily.get("temperature_2m_min", []),
        "Rainfall (mm)": daily.get("precipitation_sum", []),
        "Rain Probability (%)": daily.get("precipitation_probability_max", []),
    })
    return summary, f"**Summary:** {res.get('text', '')}", forecast_df, f"Source: [{res.get('title','Weather')}]({res.get('source','')})"


def climate_ui(city, year):
    res = backend_call("/api/climate", params={"city": city, "year": int(year)})
    data = res.get("data", {})
    summary = metric_card(
        f"NASA POWER Climate History • {city} ({year})",
        [
            ("Analysis Year", data.get("year", year)),
            ("Mean Daily Temp", f"{data.get('mean_temp_c', 'N/A')} °C"),
            ("Total Annual Rain", f"{data.get('precipitation_mm', 'N/A')} mm"),
            ("Recorded Days", data.get("days", 365)),
        ],
        footer="Derived from NASA POWER satellite agroclimatology",
    )
    df = pd.DataFrame([{
        "City": city, "Year": data.get("year", year),
        "Mean Temperature (°C)": data.get("mean_temp_c", "N/A"),
        "Total Precipitation (mm)": data.get("precipitation_mm", "N/A"),
        "Recorded Days": data.get("days", "N/A"),
    }])
    return summary, f"**Summary:** {res.get('text', '')}", df, f"Source: [{res.get('title','NASA POWER')}]({res.get('source','')})"


def summarize_uploaded_policy(file_path, custom_q, language, session):
    if not file_path:
        raise gr.Error("Please upload a PDF, DOCX or TXT file first.")
    path = Path(file_path)
    extracted_text = extract_text(path)
    if not extracted_text:
        raise gr.Error("No readable text found in this document.")
    res = run_question(
        query=custom_q or "Summarize this government agricultural policy / scheme document.",
        language=language,
        session_id=session,
        document_text=extracted_text,
        document_name=path.name,
        forced_route="policy_summary",
    )
    return res.get("answer", ""), f"Document: **{path.name}** ({len(extracted_text):,} chars extracted)", agent_trace(res), render_sources(res)


def analyze_crop_photo(image_path, language, session):
    if not image_path:
        raise gr.Error("Please upload or take a photograph of the plant/leaf.")
    res = run_question(
        query="Inspect visual symptoms of this crop/leaf photograph.",
        language=language,
        session_id=session,
        image_path=str(image_path),
        forced_route="vision",
    )
    return res.get("answer", ""), render_sources(res), agent_trace(res)


def save_user_profile(session, city, district, crop, language, consent):
    if not consent:
        return "Nothing saved. Please check the consent checkbox first."
    db.save_profile(session_id=session, city=city, district=district, crop=crop, language=language, consent=True)
    return "✅ Preferences saved to local database."


def show_chat_history(session):
    records = db.get_history(session, limit=25)
    if not records:
        return "No conversation history found for this session."
    return "\n\n".join(f"**{r['role'].upper()} ({r['language']})**: {r['content']}" for r in records)


def clear_user_history(session):
    db.delete_user_data(session)
    return "✅ Session history deleted."


# =====================================================================
# Build the Gradio UI
# =====================================================================

def create_ui():
    en = LANG_DATA["en"]

    with gr.Blocks(title="Gram Sahayak • Agricultural Multi-Agent AI") as demo:
        session = gr.State(lambda: uuid.uuid4().hex)

        # ── 1. HERO (full-screen, scrolls away) ──────────────────────
        hero_el = gr.HTML(hero_html_str(en))

        # ── 2. DASHBOARD (solid dark below hero) ─────────────────────
        with gr.Column(elem_id="gs-dash"):
            with gr.Column(elem_classes=["dash-inner"]):

                # Nav bar
                nav_el = gr.HTML(nav_html_str(en))

                # Context strip — Language + Location + Crop
                with gr.Row(elem_classes=["ctx-strip"]):
                    lang = gr.Radio(
                        choices=[("English", "en"), ("हिन्दी", "hi")],
                        value="en",
                        label=en["lang_label"],
                        scale=2,
                        elem_classes=["gs-lang-radio"],
                    )
                    city = gr.Textbox(value="Nashik", label=en["city_label"], scale=3)
                    district = gr.Textbox(value="", label=en["district_label"], scale=3)
                    commodity = gr.Textbox(value="", label=en["commodity_label"], scale=3)

                # ── TABS ─────────────────────────────────────────────
                with gr.Tabs(elem_id="main-tabs") as tabs:

                    # Tab 1 — Assistant & Voice
                    with gr.Tab(en["tab_chat"], id="tab_chat") as tab_chat:
                        chat_hdr = gr.Markdown(f"### {en['chat_header']}")

                        chatbot = gr.Chatbot(
                            height=280,
                            label=en["chat_label"],
                            elem_classes=["compact-chat"],
                        )

                        with gr.Row():
                            with gr.Column(scale=8):
                                question = gr.Textbox(
                                    label=en["chat_placeholder"],
                                    placeholder=en["chat_placeholder"],
                                    lines=1,
                                )
                            with gr.Column(scale=2):
                                submit_btn = gr.Button(en["btn_ask"], variant="primary")
                                clear_btn = gr.Button(en["btn_clear"])

                        with gr.Row():
                            auto_mic = gr.Audio(
                                sources=["microphone"],
                                streaming=True,
                                type="numpy",
                                label=en["mic_label"],
                                scale=6,
                            )
                            with gr.Column(scale=4):
                                speak = gr.Checkbox(label=en["speak_label"], value=True)
                                auto_status = gr.Markdown("🎙️ Ready — speak into microphone...")

                        auto_state = gr.State({
                            "chunks": [], "sr": 16000, "speech": False,
                            "quiet": 0.0, "cooldown": 0.0, "length": 0.0,
                        })

                        answer_audio = gr.Audio(
                            label="Voice Reply",
                            type="filepath",
                            autoplay=True,
                            interactive=False,
                        )

                        with gr.Accordion("Execution Details & Sources", open=False):
                            latest_ans = gr.Textbox(label="Latest Answer", lines=3)
                            flow_trace = gr.Textbox(label="Agent Flow (Trace)")
                            citations = gr.Markdown(label="Sources & Evidence")

                        text_inputs = [question, chatbot, lang, city, district, commodity, session, speak]
                        text_outputs = [chatbot, question, citations, answer_audio, flow_trace, latest_ans]
                        submit_btn.click(send_chat, inputs=text_inputs, outputs=text_outputs)
                        question.submit(send_chat, inputs=text_inputs, outputs=text_outputs)
                        clear_btn.click(lambda: ([], "", "", None, "", ""), outputs=text_outputs)

                        stream_inputs = [auto_mic, auto_state, chatbot, lang, city, district, commodity, session]
                        stream_outputs = [auto_state, chatbot, auto_status, citations, answer_audio, flow_trace, latest_ans]
                        auto_mic.stream(
                            stream_auto_silence,
                            inputs=stream_inputs,
                            outputs=stream_outputs,
                            stream_every=0.35,
                        )

                    # Tab 2 — Mandi Prices
                    with gr.Tab(en["tab_mandi"], id="tab_mandi") as tab_mandi:
                        mandi_hdr = gr.Markdown(f"### {en['mandi_header']}")
                        with gr.Row():
                            mandi_crop = gr.Textbox(value="Onion", label=en["crop_label"])
                            mandi_state = gr.Textbox(value="Maharashtra", label=en["state_label"])
                            mandi_district = gr.Textbox(value="", label=en["dist_label"])
                        mandi_btn = gr.Button(en["btn_mandi"], variant="primary")
                        mandi_summary = gr.HTML()
                        mandi_note = gr.Markdown()
                        mandi_table = gr.Dataframe(label=en["mandi_table_label"], interactive=False, wrap=True)
                        mandi_source = gr.Markdown()
                        mandi_btn.click(
                            mandi_ui,
                            inputs=[mandi_crop, mandi_state, mandi_district],
                            outputs=[mandi_summary, mandi_note, mandi_table, mandi_source],
                        )

                    # Tab 3 — Live Weather
                    with gr.Tab(en["tab_weather"], id="tab_weather") as tab_weather:
                        weather_hdr = gr.Markdown(f"### {en['weather_header']}")
                        weather_btn = gr.Button(en["btn_weather"], variant="primary")
                        weather_summary = gr.HTML()
                        weather_notes = gr.Markdown()
                        weather_table = gr.Dataframe(label=en["weather_table_label"], interactive=False, wrap=True)
                        weather_source = gr.Markdown()
                        weather_btn.click(
                            weather_ui,
                            inputs=[city],
                            outputs=[weather_summary, weather_notes, weather_table, weather_source],
                        )

                    # Tab 4 — Climate History
                    with gr.Tab(en["tab_climate"], id="tab_climate") as tab_climate:
                        climate_hdr = gr.Markdown(f"### {en['climate_header']}")
                        climate_year = gr.Number(value=date.today().year - 1, precision=0, label=en["year_label"])
                        climate_btn = gr.Button(en["btn_climate"], variant="primary")
                        climate_summary = gr.HTML()
                        climate_notes = gr.Markdown()
                        climate_table = gr.Dataframe(interactive=False)
                        climate_source = gr.Markdown()
                        climate_btn.click(
                            climate_ui,
                            inputs=[city, climate_year],
                            outputs=[climate_summary, climate_notes, climate_table, climate_source],
                        )

                    # Tab 5 — Policy Summarizer
                    with gr.Tab(en["tab_policy"], id="tab_policy") as tab_policy:
                        policy_hdr = gr.Markdown(f"### {en['policy_header']}")
                        with gr.Row():
                            with gr.Column(scale=5):
                                policy_file = gr.File(
                                    label=en["file_label"],
                                    file_types=[".pdf", ".docx", ".txt", ".md"],
                                    type="filepath",
                                )
                            with gr.Column(scale=7):
                                policy_q = gr.Textbox(
                                    label=en["policy_q_label"],
                                    placeholder=en["policy_q_ph"],
                                    lines=2,
                                )
                                summarize_btn = gr.Button(en["btn_policy"], variant="primary")
                        doc_info_text = gr.Markdown()
                        summary_output = gr.Markdown(label="Structured Policy Briefing")
                        policy_trace = gr.Textbox(label="Agent Trace")
                        policy_sources = gr.Markdown(label="Sources")
                        summarize_btn.click(
                            summarize_uploaded_policy,
                            inputs=[policy_file, policy_q, lang, session],
                            outputs=[summary_output, doc_info_text, policy_trace, policy_sources],
                        )

                    # Tab 6 — Crop Doctor
                    with gr.Tab(en["tab_crop"], id="tab_crop") as tab_crop:
                        crop_hdr = gr.Markdown(f"### {en['crop_header']}")
                        crop_warn_box = gr.Markdown(en["crop_warn"])
                        plant_img = gr.Image(type="filepath", sources=["upload", "webcam"], label=en["crop_img_label"])
                        crop_btn = gr.Button(en["btn_crop"], variant="primary")
                        crop_result = gr.Markdown()
                        crop_sources = gr.Markdown()
                        crop_trace = gr.Textbox(label="Agent Trace")
                        crop_btn.click(
                            analyze_crop_photo,
                            inputs=[plant_img, lang, session],
                            outputs=[crop_result, crop_sources, crop_trace],
                        )

                    # Tab 7 — Agent Roster
                    with gr.Tab(en["tab_agents"], id="tab_agents") as tab_agents:
                        agents_hdr = gr.Markdown(f"### {en['agents_header']}")
                        agents_display = gr.HTML(get_agent_cards_html())

                    # Tab 8 — Profile & Privacy
                    with gr.Tab(en["tab_profile"], id="tab_profile") as tab_profile:
                        profile_hdr = gr.Markdown(f"### {en['profile_header']}")
                        saved_city = gr.Textbox(label=en["home_city"])
                        saved_district = gr.Textbox(label=en["home_dist"])
                        saved_crop = gr.Textbox(label=en["home_crop"])
                        consent_box = gr.Checkbox(label=en["consent"], value=False)
                        save_prof_btn = gr.Button(en["btn_save"], variant="primary")
                        prof_status = gr.Textbox(label="Status")
                        save_prof_btn.click(
                            save_user_profile,
                            inputs=[session, saved_city, saved_district, saved_crop, lang, consent_box],
                            outputs=[prof_status],
                        )
                        gr.Markdown("---")
                        history_display = gr.Markdown()
                        load_hist_btn = gr.Button(en["btn_view_hist"])
                        del_hist_btn = gr.Button(en["btn_del_hist"], variant="stop")
                        load_hist_btn.click(show_chat_history, inputs=[session], outputs=[history_display])
                        del_hist_btn.click(clear_user_history, inputs=[session], outputs=[history_display])

        # ── Language Switcher ─────────────────────────────────────────
        def switch_language(sel: str):
            t = LANG_DATA.get(sel, LANG_DATA["en"])
            return (
                hero_html_str(t),
                nav_html_str(t),
                gr.update(label=t["city_label"]),
                gr.update(label=t["district_label"]),
                gr.update(label=t["commodity_label"]),
                gr.update(label=t["tab_chat"]),
                gr.update(label=t["tab_mandi"]),
                gr.update(label=t["tab_weather"]),
                gr.update(label=t["tab_climate"]),
                gr.update(label=t["tab_policy"]),
                gr.update(label=t["tab_crop"]),
                gr.update(label=t["tab_agents"]),
                gr.update(label=t["tab_profile"]),
                f"### {t['chat_header']}",
                gr.update(label=t["chat_label"]),
                gr.update(label=t["chat_placeholder"], placeholder=t["chat_placeholder"]),
                gr.update(value=t["btn_ask"]),
                gr.update(value=t["btn_clear"]),
                gr.update(label=t["mic_label"]),
                gr.update(label=t["speak_label"]),
                f"### {t['mandi_header']}",
                gr.update(label=t["crop_label"]),
                gr.update(label=t["state_label"]),
                gr.update(label=t["dist_label"]),
                gr.update(value=t["btn_mandi"]),
                f"### {t['weather_header']}",
                gr.update(value=t["btn_weather"]),
                f"### {t['climate_header']}",
                gr.update(label=t["year_label"]),
                gr.update(value=t["btn_climate"]),
                f"### {t['policy_header']}",
                gr.update(label=t["file_label"]),
                gr.update(label=t["policy_q_label"], placeholder=t["policy_q_ph"]),
                gr.update(value=t["btn_policy"]),
                f"### {t['crop_header']}",
                t["crop_warn"],
                gr.update(label=t["crop_img_label"]),
                gr.update(value=t["btn_crop"]),
                f"### {t['agents_header']}",
                f"### {t['profile_header']}",
                gr.update(label=t["home_city"]),
                gr.update(label=t["home_dist"]),
                gr.update(label=t["home_crop"]),
                gr.update(label=t["consent"]),
                gr.update(value=t["btn_save"]),
                gr.update(value=t["btn_view_hist"]),
                gr.update(value=t["btn_del_hist"]),
            )

        lang.change(
            switch_language,
            inputs=[lang],
            outputs=[
                hero_el, nav_el,
                city, district, commodity,
                tab_chat, tab_mandi, tab_weather, tab_climate, tab_policy, tab_crop, tab_agents, tab_profile,
                chat_hdr, chatbot, question, submit_btn, clear_btn, auto_mic, speak,
                mandi_hdr, mandi_crop, mandi_state, mandi_district, mandi_btn,
                weather_hdr, weather_btn,
                climate_hdr, climate_year, climate_btn,
                policy_hdr, policy_file, policy_q, summarize_btn,
                crop_hdr, crop_warn_box, plant_img, crop_btn,
                agents_hdr,
                profile_hdr, saved_city, saved_district, saved_crop, consent_box,
                save_prof_btn, load_hist_btn, del_hist_btn,
            ],
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.queue(default_concurrency_limit=4).launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.green,
            secondary_hue=gr.themes.colors.emerald,
            neutral_hue=gr.themes.colors.slate,
            font=[gr.themes.GoogleFont("Plus Jakarta Sans"), "system-ui", "sans-serif"],
        ),
        css=CSS,
    )
