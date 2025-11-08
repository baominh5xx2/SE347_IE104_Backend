"""
Agent Services Module

New Structure:
- agents/: Agent definitions (ChatAgent, RecommendationAgent)
- graphs/: LangGraph workflows (SupervisorGraph)
- nodes/: Node functions for graphs
- state/: State schemas (AgentState)
- tools/: Agent tools (MCP tools)
- memory/: Memory management (ConversationMemory)
- config.py: Configuration
- app.py: Main entry point

Legacy exports for backward compatibility:
- dual_agent_system -> supervisor_graph
- DualAgentSystem -> SupervisorGraph
"""

# New structure exports
from .graphs import SupervisorGraph, supervisor_graph, GraphConfig
from .agents import ChatAgent, RecommendationAgent, recommendation_agent

# Legacy exports for backward compatibility
from .app import DualAgentSystem, dual_agent_system

__all__ = [
    # New structure
    "SupervisorGraph",
    "supervisor_graph",
    "GraphConfig",
    "ChatAgent",
    "RecommendationAgent",
    "recommendation_agent",
    # Legacy compatibility
    "dual_agent_system",
    "DualAgentSystem",
]

