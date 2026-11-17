"""Compatibility wrapper for Gram Sahayak workflow.

Re-exports agent definitions and execution graph from app.agents.
"""
from __future__ import annotations

from .agents import (
    FarmState,
    ROUTES,
    AGENT_REGISTRY,
    list_agents,
    route_by_rules,
    safety_triage_node as triage,
    supervisor_node as supervisor,
    mandi_node as mandi,
    weather_node as weather,
    climate_node as climate,
    schemes_node as schemes,
    vision_node as vision,
    policy_summary_node as policy_summary,
    agriculture_node as agriculture,
    response_generator_node as response_generator,
    verifier_node as verifier,
    build_agent_graph,
    get_agent_graph,
    run_question,
)

__all__ = [
    "FarmState",
    "ROUTES",
    "AGENT_REGISTRY",
    "list_agents",
    "route_by_rules",
    "triage",
    "supervisor",
    "mandi",
    "weather",
    "climate",
    "schemes",
    "vision",
    "policy_summary",
    "agriculture",
    "response_generator",
    "verifier",
    "build_agent_graph",
    "get_agent_graph",
    "run_question",
]
