
"""
Supervisor Graph
Main orchestration graph for multi-agent system
"""
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import logging

from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.nodes import ChatAgentNodes, RecommendationAgentNodes
from app.v1.services.agent_services.config import agent_config
from app.v1.core.logging_config import agent_callback

logger = logging.getLogger(__name__)


class GraphConfig(BaseModel):
    """Configuration schema for the graph"""
    max_iterations: int = 10
    timeout: int = 300
    enable_streaming: bool = True
    enable_falkor_tracking: bool = False


class SupervisorGraph:
    """
    Supervisor Graph - Orchestrates Chat Agent and Recommendation Agent
    
    Architecture:
    - Chat Agent: Handles conversation with tool calling loop
    - Recommendation Agent: Provides tour recommendations (called by Chat Agent via tool)
    
    Flow:
    1. START → chat_llm (LLM decides to use tools or respond)
    2. chat_llm → should_continue → 
       - If tool_calls: chat_tools → should_recommend
       - If no tool_calls: END
    3. chat_tools → should_recommend →
       - If recommendation requested: recommendation_agent → END
       - Otherwise: chat_llm (loop back)
    """
    
    def __init__(self):
        """Initialize Supervisor Graph"""
        # Initialize LLM for Chat Agent
        callbacks = [agent_callback] if agent_callback and agent_config.enable_streaming else []
        
        # Build LLM kwargs
        llm_kwargs = {
            "model": agent_config.model,
            "api_key": agent_config.api_key,
            "temperature": agent_config.temperature,
            "streaming": agent_config.enable_streaming,
            "callbacks": callbacks,
            "verbose": agent_config.enable_streaming
        }
        
        # Add organization if provided
        if agent_config.organization:
            llm_kwargs["organization"] = agent_config.organization
        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        # Initialize nodes with LLM
        self.chat_nodes = ChatAgentNodes(self.llm)
        self.recommendation_nodes = RecommendationAgentNodes()
        self.graph = self._build_graph()
        logger.info("✅ Supervisor Graph initialized")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the multi-agent graph following LangGraph agent pattern
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(AgentState, config_schema=GraphConfig)
        
        # Add nodes
        workflow.add_node("chat_llm", self.chat_nodes.chat_llm_node)
        workflow.add_node("chat_tools", self.chat_nodes.chat_tools_node)
        workflow.add_node("recommendation_agent", self.recommendation_nodes.recommendation_node)
        
        # Build workflow
        workflow.add_edge(START, "chat_llm")
        
        # Conditional routing for tool calling loop
        workflow.add_conditional_edges(
            "chat_llm",
            self.chat_nodes.should_continue_tool_loop,
            {
                "chat_tools": "chat_tools",
                END: END
            }
        )
        
        # After tool execution: check if recommendation was requested
        workflow.add_conditional_edges(
            "chat_tools",
            self.chat_nodes.should_recommend,
            {
                "recommendation_agent": "recommendation_agent",
                "chat_llm": "chat_llm"  # Loop back if no recommendation needed
            }
        )
        
        # After recommendation agent, go back to Chat Agent to generate final response
        workflow.add_edge("recommendation_agent", "chat_llm")
        
        return workflow.compile()
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: list = None,
        conversation_id: str = "default_conv",
        user_id: str = "anonymous_user"
    ) -> dict:
        """
        Process user message through multi-agent system
        
        Args:
            user_message: User's input
            conversation_history: Previous messages
            conversation_id: Conversation ID for tracking
            user_id: User ID for personalization
            
        Returns:
            Dict with response and metadata
        """
        # Initialize state
        initial_state = AgentState(
            messages=[HumanMessage(content=user_message)],
            conversation_id=conversation_id,
            user_id=user_id,
            chat_response="",
            needs_recommendation=False,
            recommendation_params={},
            recommended_package_ids=[],
            final_response=""
        )
        
        # Add conversation history if provided
        if conversation_history:
            history_messages = []
            for msg in conversation_history:
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        history_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        history_messages.append(HumanMessage(content=content))
            
            if history_messages:
                initial_state["messages"] = history_messages + initial_state["messages"]
        
        # Invoke graph
        try:
            config = {
                "configurable": {
                    "thread_id": conversation_id,
                    "max_iterations": agent_config.max_iterations
                }
            }
            
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Extract final response
            final_response = final_state.get("final_response", "") or final_state.get("chat_response", "")
            
            # Log final response in a nice format
            try:
                from colorama import Fore, Style
                COLORAMA_AVAILABLE = True
            except ImportError:
                COLORAMA_AVAILABLE = False
                class Fore:
                    CYAN = '\033[96m'
                    GREEN = '\033[92m'
                    RESET = '\033[0m'
                class Style:
                    BRIGHT = '\033[1m'
                    RESET_ALL = '\033[0m'
            
            if COLORAMA_AVAILABLE:
                print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}", flush=True)
                print(f"{Fore.CYAN}{Style.BRIGHT}> Final Response:{Style.RESET_ALL}", flush=True)
                print(f"{Fore.GREEN}{final_response}{Style.RESET_ALL}", flush=True)
                print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}\n", flush=True)
            else:
                print(f"\n{'='*60}", flush=True)
                print(f"> Final Response:", flush=True)
                print(f"{final_response}", flush=True)
                print(f"{'='*60}\n", flush=True)
            
            return {
                "response": final_response,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "recommendations": final_state.get("recommended_package_ids", []),
                "metadata": {
                    "needs_recommendation": final_state.get("needs_recommendation", False),
                    "has_package_ids": len(final_state.get("recommended_package_ids", [])) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            return {
                "response": "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại.",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "recommendations": [],
                "error": str(e)
            }


# Singleton instance
supervisor_graph = SupervisorGraph()
