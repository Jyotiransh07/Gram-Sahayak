"""Comprehensive unit tests for Gram Sahayak multi-agent framework and features."""
from pathlib import Path
import pytest
from app import db, tools, rag
from app.agents import list_agents, route_by_rules, run_question, AGENT_REGISTRY
from app.services.documents import extract_text


def test_agent_registry_contains_all_agents():
    agents = list_agents()
    assert len(agents) == 11
    agent_names = [a["name"] for a in agents]
    assert "Safety & Triage Agent" in agent_names
    assert "Supervisor & Router Agent" in agent_names
    assert "Mandi Price Agent" in agent_names
    assert "Weather Agent" in agent_names
    assert "Climate Analysis Agent" in agent_names
    assert "Government Scheme Agent" in agent_names
    assert "Crop Vision Agent" in agent_names
    assert "Policy Summarizer Agent" in agent_names
    assert "Agriculture Knowledge Agent" in agent_names
    assert "Response Generator Agent" in agent_names
    assert "Verification Agent" in agent_names

    # Check each has metadata
    for a in agents:
        assert a.get("role")
        assert a.get("description")
        assert len(a.get("tools", [])) > 0
        assert len(a.get("data_sources", [])) > 0


def test_commodity_and_state_normalization():
    assert tools.normalize_commodity("प्याज") == "Onion"
    assert tools.normalize_commodity("प्याज़") == "Onion"
    assert tools.normalize_commodity("pyaz") == "Onion"
    assert tools.normalize_commodity("गेहूं") == "Wheat"
    assert tools.normalize_commodity("tamatar") == "Tomato"
    assert tools.normalize_commodity("आलू") == "Potato"
    assert tools.normalize_commodity("सोयाबीन") == "Soyabean"
    assert tools.normalize_commodity("कपास") == "Cotton"

    assert tools.normalize_state("महाराष्ट्र") == "Maharashtra"
    assert tools.normalize_state("मध्य प्रदेश") == "Madhya Pradesh"
    assert tools.normalize_state("पंजाब") == "Punjab"
    assert tools.normalize_state("rajasthan") == "Rajasthan"


def test_routing_rules_comprehensive():
    assert route_by_rules("Will it rain in Nashik tomorrow?") == "weather"
    assert route_by_rules("नासिक में कल का मौसम कैसा रहेगा?") == "weather"
    assert route_by_rules("What is the current mandi rate of onion?") == "mandi"
    assert route_by_rules("आज प्याज का भाव क्या है?") == "mandi"
    assert route_by_rules("Historical climate for 2024") == "climate"
    assert route_by_rules("PM Kisan subsidy eligibility") == "schemes"
    assert route_by_rules("किसान क्रेडिट कार्ड कैसे मिलेगा?") == "schemes"
    assert route_by_rules("How to fertilize black soil for cotton?") == "agriculture"
    assert route_by_rules("any query", image_path="leaf.jpg") == "vision"
    assert route_by_rules("Summarize this policy", document_text="Policy text...") == "policy_summary"


def test_document_extraction_txt(tmp_path):
    sample_file = tmp_path / "sample_policy.txt"
    sample_file.write_text("PM Kisan Samman Nidhi Yojana: Rs 6000 per year in 3 installments.", encoding="utf-8")
    extracted = extract_text(sample_file)
    assert "PM Kisan Samman Nidhi" in extracted
    assert "Rs 6000" in extracted


def test_emergency_triage_interception():
    res = run_question(query="Someone accidentally swallowed pesticide!", language="en")
    assert res.get("emergency") is True
    assert "112" in res.get("answer", "")

    res_hi = run_question(query="किसान ने कीटनाशक पी लिया है", language="hi")
    assert res_hi.get("emergency") is True
    assert "112" in res_hi.get("answer", "")
