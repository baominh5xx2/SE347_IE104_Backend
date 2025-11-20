"""
Main Application Entry Point
Legacy compatibility exports
"""
from app.v1.services.agent_services.graphs import SupervisorGraph, supervisor_graph, GraphConfig
from app.v1.services.agent_services.agents import ChatAgent, RecommendationAgent, recommendation_agent

# Legacy exports for backward compatibility
DualAgentSystem = SupervisorGraph
dual_agent_system = supervisor_graph

__all__ = [
    "SupervisorGraph",
    "supervisor_graph",
    "GraphConfig",
    "ChatAgent",
    "RecommendationAgent",
    "recommendation_agent",
    "DualAgentSystem",
    "dual_agent_system"
]
