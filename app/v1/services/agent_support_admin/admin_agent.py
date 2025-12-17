"""
Admin Agent
LangGraph-based agent for admin database queries
Loads config from admin_agent.yaml
"""
import logging
import json
import re
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
        Process admin query with ReAct loop (Multi-step)
        
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
            
            # 1. Build initial messages
            messages = [
                SystemMessage(content=get_system_prompt()),
                *memory.messages[-10:],  # Context
                HumanMessage(content=query)
            ]
            
            all_tool_results = []
            final_response_content = ""
            max_iterations = self.config.max_iterations
            
            # 2. ReAct Loop
            for i in range(max_iterations):
                logger.info(f"🔄 ReAct Iteration {i+1}/{max_iterations}")
                
                # Invoke LLM (WITH defined tools)
                response = await self.llm_with_tools.ainvoke(messages)
                
                # Check for tool calls
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"🛠️ Tool calls detected: {len(response.tool_calls)}")
                    
                    # Execute tools
                    tool_messages = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get('name')
                        tool_args = tool_call.get('args', {})
                        tool_call_id = tool_call.get('id', f"call_{tool_name}")
                        
                        logger.info(f"🔧 Calling tool: {tool_name}")
                        
                        result_str = ""
                        if tool_name in self.tools_by_name:
                            tool = self.tools_by_name[tool_name]
                            try:
                                result = tool.invoke(tool_args)
                                # Append to global results
                                all_tool_results.append({
                                    "tool": tool_name,
                                    "result": result
                                })
                                result_str = json.dumps(result, ensure_ascii=False, default=str)
                            except Exception as e:
                                error_msg = f"Error executing {tool_name}: {str(e)}"
                                logger.error(error_msg)
                                result_str = json.dumps({"error": error_msg})
                                all_tool_results.append({
                                    "tool": tool_name,
                                    "error": error_msg
                                })
                        else:
                            msg = f"Unknown tool: {tool_name}"
                            result_str = json.dumps({"error": msg})
                            all_tool_results.append({"tool": tool_name, "error": msg})
                        
                        # Create ToolMessage
                        tool_messages.append(
                            ToolMessage(
                                content=result_str,
                                tool_call_id=tool_call_id
                            )
                        )
                    
                    # Append AIMessage (with tool_calls) and ToolMessages to history
                    messages.append(response)
                    messages.extend(tool_messages)
                    
                    # CONTINUE LOOP to let LLM process results
                    continue
                
                else:
                    # No tool calls -> Final Answer
                    logger.info("✅ Final answer received")
                    final_response_content = response.content
                    break
            
            # Check if loop exhausted without final answer
            if not final_response_content and i == max_iterations - 1:
                logger.warning("⚠️ Max iterations reached without final answer")
                final_response_content = "Tôi không thể xử lý yêu cầu này sau nhiều bước. Vui lòng thử lại cụ thể hơn."

            # 3. Cleanup and Response
            response_text = final_response_content
            if hasattr(final_response_content, 'content'): # Should be string, but safety check
                response_text = final_response_content.content
            
            response_text = str(response_text)
            
            # Line-based cleanup for artifacts (still good to have)
            if "type: ChatGeneration" in response_text or '{"sql_query":' in response_text or '{"success":' in response_text:
                 logger.warning("⚠️ Cleaning artifacts from final response...")
                 lines = response_text.split('\n')
                 clean_lines = []
                 for line in lines:
                     stripped = line.strip()
                     if (stripped.startswith('type: ChatGeneration') or 
                         stripped.startswith('llm_output:') or
                         '{"sql_query":' in stripped or 
                         '{"success":' in stripped or
                         '"completion_tokens":' in stripped):
                         continue
                     clean_lines.append(line)
                 response_text = '\n'.join(clean_lines).strip()

            # Save to Memory (User Query + Final Answer)
            # We do NOT save the intermediate tool steps to long-term memory to save context
            memory.add_user_message(query)
            memory.add_ai_message(response_text)
            
            return {
                "success": True,
                "response": response_text,
                "tool_calls": all_tool_results,
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
