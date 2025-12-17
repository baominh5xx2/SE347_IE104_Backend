"""
Admin Agent
LangGraph-based agent for admin database queries
Loads config from admin_agent.yaml
"""
import logging
import json
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_community.chat_message_histories import ChatMessageHistory

from app.v1.services.agent_services.llm_providers import create_llm_provider
from .config import admin_agent_config, get_system_prompt
from .tools import get_admin_tools

logger = logging.getLogger(__name__)


class AdminAgent:
    """
    Admin Agent - Handles admin queries with database access
    
    Uses LangGraph pattern for tool calling loop:
    1. Receive admin query (natural language)
    2. LLM generates SQL via query_database tool
    3. Execute query via Supabase RPC
    4. Format and return results
    
    Config loaded from admin_agent.yaml
    """
    
    def __init__(self):
        """Initialize Admin Agent from config"""
        self.name = admin_agent_config.name
        self.config = admin_agent_config
        
        # Create LLM from config
        provider = create_llm_provider()
        self.llm = provider.get_llm(
            model=admin_agent_config.model,
            api_key=admin_agent_config.api_key,
            temperature=admin_agent_config.temperature,
        )
        
        # Initialize tools
        self.tools = get_admin_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Memory storage (per session)
        self.memory_storage: Dict[str, ChatMessageHistory] = {}
        
        logger.info(f"✅ {self.name} initialized with model: {admin_agent_config.model}")
    
    def get_memory(self, session_id: str) -> ChatMessageHistory:
        """Get or create memory for a session"""
        if session_id not in self.memory_storage:
            self.memory_storage[session_id] = ChatMessageHistory()
        return self.memory_storage[session_id]
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process admin query
        
        Args:
            query: Natural language query from admin
            user_id: Admin user ID
            session_id: Optional session ID for memory
            
        Returns:
            Query result with data and explanation
        """
        try:
            session_id = session_id or f"admin_{user_id}"
            memory = self.get_memory(session_id)
            
            # Build messages
            messages = [
                SystemMessage(content=get_system_prompt()),
                *memory.messages[-10:],  # Last 10 messages for context
                HumanMessage(content=query)
            ]
            
            # LLM decides what to do
            logger.info(f"🤖 Admin Agent processing: {query[:50]}...")
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Check if tool call is needed
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tool calls and create proper ToolMessages
                tool_results = []
                tool_messages = []
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name')
                    tool_args = tool_call.get('args', {})
                    tool_call_id = tool_call.get('id', f"call_{tool_name}")
                    
                    logger.info(f"🔧 Calling tool: {tool_name}")
                    
                    if tool_name in self.tools_by_name:
                        tool = self.tools_by_name[tool_name]
                        result = tool.invoke(tool_args)
                        result_str = json.dumps(result, ensure_ascii=False, default=str)
                        tool_results.append({
                            "tool": tool_name,
                            "result": result
                        })
                    else:
                        result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                        tool_results.append({
                            "tool": tool_name,
                            "error": f"Unknown tool: {tool_name}"
                        })
                    
                    # Create proper ToolMessage for OpenAI
                    tool_messages.append(
                        ToolMessage(
                            content=result_str,
                            tool_call_id=tool_call_id
                        )
                    )
                
                # Build final messages with proper tool responses
                final_messages = messages + [response] + tool_messages
                
                # Get final response from LLM
                final_response = await self.llm.ainvoke(final_messages)
                
                # Store in memory
                memory.add_user_message(query)
                memory.add_ai_message(final_response.content)
                
                return {
                    "success": True,
                    "response": final_response.content,
                    "tool_calls": tool_results,
                    "query": query
                }
            
            else:
                # No tool call, direct response
                memory.add_user_message(query)
                memory.add_ai_message(response.content)
                
                return {
                    "success": True,
                    "response": response.content,
                    "tool_calls": [],
                    "query": query
                }
                
        except Exception as e:
            logger.error(f"❌ Admin Agent error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process state (implements BaseAgent interface)
        
        For LangGraph integration
        """
        query = state.get("query", "")
        user_id = state.get("user_id", "")
        
        result = await self.process_query(query, user_id)
        
        state["admin_result"] = result
        state["final_response"] = result.get("response", "")
        
        return state


# Singleton instance
_admin_agent: Optional[AdminAgent] = None


def get_admin_agent() -> AdminAgent:
    """Get or create admin agent instance"""
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = AdminAgent()
    return _admin_agent
