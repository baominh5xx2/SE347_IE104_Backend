"""
Admin Agent LangGraph Workflow
Builds the admin agent graph
Config loaded from admin_agent.yaml
"""
import logging
from typing import Optional
from langgraph.graph import StateGraph, START, END

from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.llm_providers import create_llm_provider
from .config import admin_agent_config
from .nodes import AdminAgentNodes

logger = logging.getLogger(__name__)

# Check for memory saver
try:
    from langgraph.checkpoint.memory import MemorySaver
    HAS_MEMORY_SAVER = True
except ImportError:
    HAS_MEMORY_SAVER = False
    logger.warning("MemorySaver not available")


class AdminGraph:
    """
    Admin Agent Graph
    
    LangGraph workflow for admin queries
    Config loaded from admin_agent.yaml
    """
    
    def __init__(self):
        """Initialize Admin Graph from config"""
        # Create LLM from config
        provider = create_llm_provider()
        self.llm = provider.get_llm(
            model=admin_agent_config.model,
            api_key=admin_agent_config.api_key,
            temperature=admin_agent_config.temperature
        )
        
        # Initialize nodes
        self.nodes = AdminAgentNodes(self.llm)
        
        # Build graph
        self.graph = self._build_graph()
        
        logger.info(f"✅ Admin Graph initialized with model: {admin_agent_config.model}")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the admin agent graph
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("admin_llm", self.nodes.admin_llm_node)
        workflow.add_node("admin_tools", self.nodes.admin_tools_node)
        
        # Set entry point
        workflow.add_edge(START, "admin_llm")
        
        # Add conditional routing
        workflow.add_conditional_edges(
            "admin_llm",
            self.nodes.should_continue,
            {
                "admin_tools": "admin_tools",
                END: END
            }
        )
        
        # After tools, go back to LLM
        workflow.add_edge("admin_tools", "admin_llm")
        
        # Compile with memory if available
        if HAS_MEMORY_SAVER:
            self.memory = MemorySaver()
            return workflow.compile(checkpointer=self.memory)
        else:
            return workflow.compile()
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Process admin query through the graph
        
        Args:
            query: Natural language query
            user_id: Admin user ID
            session_id: Optional session ID for memory
            
        Returns:
            Query result
        """
        from langchain_core.messages import HumanMessage
        
        session_id = session_id or f"admin_{user_id}"
        
        # Build initial state
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "user_id": user_id,
            "query": query
        }
        
        # Config for checkpointer
        config = {"configurable": {"thread_id": session_id}}
        
        try:
            # Run graph
            result = await self.graph.ainvoke(initial_state, config)
            
            return {
                "success": True,
                "response": result.get("final_response", ""),
                "messages": result.get("messages", []),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"❌ Admin Graph error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }


# Singleton instance
_admin_graph: Optional[AdminGraph] = None


def get_admin_graph() -> AdminGraph:
    """Get or create admin graph instance"""
    global _admin_graph
    if _admin_graph is None:
        _admin_graph = AdminGraph()
    return _admin_graph


# Export singleton
admin_graph = None

def init_admin_graph():
    """Initialize admin graph (lazy loading)"""
    global admin_graph
    if admin_graph is None:
        admin_graph = get_admin_graph()
    return admin_graph
