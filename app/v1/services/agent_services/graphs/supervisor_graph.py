
"""
Supervisor Graph
Main orchestration graph for multi-agent system
"""
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import logging
import os
import time
from typing import Dict, Tuple

# Try to import checkpointer for conversation memory
try:
    from langgraph.checkpoint.memory import MemorySaver
    HAS_MEMORY_SAVER = True
except ImportError:
    try:
        from langgraph.checkpoint import MemorySaver
        HAS_MEMORY_SAVER = True
    except ImportError:
        HAS_MEMORY_SAVER = False
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ MemorySaver not available - conversation history won't be persisted")

from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.nodes import ChatAgentNodes, RecommendationAgentNodes
from app.v1.services.agent_services.config import agent_config
from app.v1.services.agent_services.llm_providers import create_llm_provider
from app.v1.core.logging_config import agent_callback
from app.v1.services.chat_room_service import ChatRoomService
from app.v1.core.supabase import get_supabase_client

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
    
    Memory Management:
    - Uses LangGraph MemorySaver checkpointer for conversation history persistence
    - Each conversation_id acts as a thread_id for state management
    - All messages and context are automatically saved per conversation
    - Agent remembers full conversation history across requests
    
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
        
        # Add reasoning config if provided (only for OpenAI o1/o3 models)
        if hasattr(agent_config, 'reasoning') and agent_config.reasoning:
            llm_kwargs["reasoning"] = agent_config.reasoning
        
        # Add organization if provided
        if agent_config.organization:
            llm_kwargs["organization"] = agent_config.organization
        
        provider = create_llm_provider()
        self.llm = provider.get_llm(**llm_kwargs)
        
        # Initialize nodes with LLM
        self.chat_nodes = ChatAgentNodes(self.llm)
        self.recommendation_nodes = RecommendationAgentNodes()
        self.graph = self._build_graph()

        # Initialize ChatRoomService for loading history from Supabase
        try:
            supabase_client = get_supabase_client()
            self.chat_room_service = ChatRoomService(supabase_client)
            logger.info("✅ ChatRoomService initialized for SupervisorGraph")
        except Exception as e:
            self.chat_room_service = None
            logger.error(f"❌ Failed to init ChatRoomService: {str(e)}")
        
        # In-memory cache for conversation history (TTL: 5 minutes)
        # Format: {conversation_id: (messages, timestamp)}
        self._history_cache: Dict[str, Tuple[list, float]] = {}
        self._cache_ttl = 300  # 5 minutes in seconds

    async def _load_history_from_supabase(self, conversation_id: str, user_id: str, limit: int = 15) -> list[BaseMessage]:
        """
        Load chat history from Supabase for a conversation/user with caching.
        
        Uses in-memory cache with 5-minute TTL to reduce database queries.
        Only loads last 15 messages (reduced from 50) to minimize prompt size.

        Only load when conversation_id is not default_conv to avoid accidental cross-user leakage.
        """
        history_messages: list[BaseMessage] = []

        # Guard: service available and conversation_id valid
        if not self.chat_room_service:
            return history_messages
        if not conversation_id or conversation_id == "default_conv":
            return history_messages

        # Check cache first
        cache_key = f"{conversation_id}:{user_id}"
        current_time = time.time()
        
        if cache_key in self._history_cache:
            cached_messages, cache_timestamp = self._history_cache[cache_key]
            if current_time - cache_timestamp < self._cache_ttl:
                logger.info(f"📦 Using cached history for {conversation_id} ({len(cached_messages)} messages)")
                return cached_messages
            else:
                # Cache expired, remove it
                del self._history_cache[cache_key]

        try:
            result = self.chat_room_service.get_room_messages(
                room_id=conversation_id,
                user_id=user_id,
                limit=limit,  # Reduced from 50 to 15
                offset=0
            )

            if result.get("EC") != 0:
                logger.warning(
                    f"⚠️ Could not load history for room {conversation_id}: {result.get('EM')}"
                )
                return history_messages

            db_messages = result.get("data") or []
            for msg in db_messages:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    history_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    history_messages.append(AIMessage(content=content))

            # Cache the loaded messages
            if history_messages:
                self._history_cache[cache_key] = (history_messages, current_time)
                logger.info(
                    f"📥 Loaded {len(history_messages)} messages from Supabase for room {conversation_id} (cached)"
                )

        except Exception as e:
            logger.error(f"❌ Error loading history from Supabase: {str(e)}")

        return history_messages
    
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

        # Conditional routing after tools execution
        workflow.add_conditional_edges(
            "chat_tools",
            self.chat_nodes.should_recommend,
            {
                "recommendation_agent": "recommendation_agent",
                "chat_llm": "chat_llm"
            }
        )
        
        # After recommendation agent, go back to Chat Agent to generate final response
        workflow.add_edge("recommendation_agent", "chat_llm")
        
        # Compile with memory checkpointer for conversation history persistence
        if HAS_MEMORY_SAVER:
            # Enable conversation memory
            self.memory = MemorySaver()
            return workflow.compile(checkpointer=self.memory)
        else:
            logger.warning("⚠️ Compiling without checkpointer - no conversation history persistence")
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
        
        # Add conversation history if provided, else load from Supabase when available
        history_messages = []

        # Prefer explicitly provided history
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        history_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        history_messages.append(AIMessage(content=content))

        # Fallback: load history from Supabase if buffer empty
        if not history_messages:
            loaded = await self._load_history_from_supabase(conversation_id, user_id, limit=15)
            if loaded:
                history_messages = loaded
            
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
            
            # Log memory checkpoint info
            logger.info(f"📝 Loading conversation state for thread_id: {conversation_id}")
            
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Extract final response
            final_response = final_state.get("final_response", "") or final_state.get("chat_response", "")
            
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

    async def process_message_stream(
        self,
        user_message: str,
        conversation_history: list = None,
        conversation_id: str = "default_conv",
        user_id: str = "anonymous_user"
    ):
        """
        Process user message through multi-agent system with streaming
        
        Args:
            user_message: User's input
            conversation_history: Previous messages
            conversation_id: Conversation ID for tracking
            user_id: User ID for personalization
            
        Yields:
            Stream events from LangGraph execution
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
        
        # Add conversation history if provided, else load from Supabase when available
        history_messages = []

        # Prefer explicitly provided history
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        history_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        history_messages.append(AIMessage(content=content))

        # Fallback: load history from Supabase if buffer empty
        if not history_messages:
            loaded = await self._load_history_from_supabase(conversation_id, user_id, limit=15)
            if loaded:
                history_messages = loaded
            
            if history_messages:
                initial_state["messages"] = history_messages + initial_state["messages"]
        
        # Stream graph execution with optimized streaming mode
        config = {
            "configurable": {
                "thread_id": conversation_id,
                "max_iterations": agent_config.max_iterations
            }
        }
        
        logger.info(f"📝 Streaming conversation for thread_id: {conversation_id}")
        
        try:
            # Use v2 streaming API with "values" mode for state updates
            # This yields state updates immediately as they occur, improving TTFT
            # Filter events to only yield what we need (skip reasoning, on_llm_start, etc.)
            async for event in self.graph.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event", "")
                # Only yield events we actually need for frontend
                # Skip: "reasoning", "on_llm_start", "on_chain_start", etc.
                if event_type in ["on_chat_model_stream", "on_chain_end"]:
                    yield event
                
        except Exception as e:
            logger.error(f"❌ Error streaming message: {str(e)}")
            yield {
                "event": "error",
                "data": {
                    "error": str(e)
                }
            }


# Singleton instance
supervisor_graph = SupervisorGraph()
