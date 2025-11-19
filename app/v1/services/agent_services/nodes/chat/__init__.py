"""
Chat Agent Nodes
Node functions for Chat Agent graph
"""
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import END
import logging
import json
from app.v1.core.prompts import prompt_manager
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.memory import conversation_memory
from app.v1.services.agent_services.tools import get_chat_tools
from app.v1.core.logging_config import get_current_agent_callback

logger = logging.getLogger(__name__)


class ChatAgentNodes:
    """
    Node functions for Chat Agent
    
    Separated from agent class for better organization
    """
    
    def __init__(self, llm):
        """
        Initialize Chat Agent nodes
        
        Args:
            llm: LLM instance to use
        """
        self.llm = llm
        self.tools = get_chat_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
    
    async def chat_llm_node(self, state: AgentState) -> AgentState:
        """
        LLM node: LLM decides whether to call a tool or respond
        
        Uses Mem0 for semantic memory search instead of buffer memory
        """
        logger.info("🤖 [Chat LLM] Processing...")
        try:
            conversation_id = state.get("conversation_id", "default_conv")
            user_id = state.get("user_id", "anonymous_user")
            
            # Get current user message for context search
            current_messages = state.get("messages", [])
            user_query = ""
            if current_messages:
                last_msg = current_messages[-1]
                if hasattr(last_msg, 'content'):
                    user_query = last_msg.content
            
            # Search Mem0 for relevant context instead of loading all messages
            relevant_memories = []
            if user_query:
                relevant_memories = await conversation_memory.search_context(
                    query=user_query,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    limit=2
                )
            
            # Prepare system prompt
            system_prompt = prompt_manager.get_system_prompt('chat_agent')
            
            # Add Mem0 context if available
            if relevant_memories:
                context_str = "\n\nRELEVANT CONTEXT FROM MEMORY:\n"
                for idx, mem in enumerate(relevant_memories, 1):
                    memory_content = mem.get("memory", "") or mem.get("content", "")
                    context_str += f"{idx}. {memory_content}\n"
                system_prompt += context_str
            
            # Add context about recommended tours if available
            recommended_package_ids = state.get("recommended_package_ids", [])
            tour_packages = state.get("tour_packages", [])
            
            if tour_packages:
                # Build detailed context about available tours
                tours_context = "\n\n⚠️ CRITICAL CONTEXT - YOU ALREADY HAVE TOUR RECOMMENDATIONS:\n"
                tours_context += "You have already shown these tours to the user. User is likely SELECTING from this list, NOT requesting new tours.\n\n"
                tours_context += "Available tours (user may refer to them by number):\n"
                for idx, pkg in enumerate(tour_packages, start=1):
                    pkg_name = pkg.get("package_name", "Unknown Tour")
                    pkg_id = pkg.get("package_id", "N/A")
                    destination = pkg.get("destination", "N/A")
                    price = pkg.get("price", 0)
                    duration = pkg.get("duration_days", 0)
                    tours_context += f"{idx}. {pkg_name} (ID: {pkg_id}) - {destination}, {duration} days, {price:,} VND\n"
                tours_context += f"\n⚠️ DO NOT call request_recommendation if:\n"
                tours_context += "- User mentions this destination (e.g., '{tour_packages[0].get('destination', 'Đà Lạt')}') - they're selecting, not requesting\n"
                tours_context += "- User provides number of people or phone - they're booking, not searching\n"
                tours_context += "- User says 'tour đà lạt đi' or similar - they're choosing from your list\n"
                tours_context += f"- User refers to tours by number ('tour 1', 'tour số 2') - use package_id from above\n\n"
                tours_context += "ONLY call request_recommendation if user EXPLICITLY asks for NEW/DIFFERENT tours.\n\n"
                
                # Add date information context
                tours_context += "📅 CRITICAL - ABOUT DATES:\n"
                tours_context += "- Each tour package has FIXED start_date and end_date (already shown in tour details)\n"
                tours_context += "- Dates are NOT user choice - they are predetermined in the package\n"
                tours_context += "- DO NOT ask user for 'ngày dự kiến khởi hành' or 'ngày đi'\n"
                tours_context += "- When displaying tours, always show start_date and end_date from package data\n"
                tours_context += "- For booking, you only need: phone, package_id, and number_of_people\n"
                
                system_prompt += tours_context
            elif recommended_package_ids:
                # Fallback: only have IDs
                package_ids_context = f"\n\nIMPORTANT CONTEXT: Available package IDs from recent recommendations: {', '.join(recommended_package_ids)}. When creating booking, use one of these exact package IDs."
                system_prompt += package_ids_context
            
            # Build messages for LLM
            messages = [SystemMessage(content=system_prompt)]
            
            # Add current state messages
            if current_messages:
                for msg in current_messages:
                    if not isinstance(msg, SystemMessage):
                        messages.append(msg)
            
            # Get LLM response with tools bound
            llm_with_tools = self.llm.bind_tools(self.tools)
            agent_callback = get_current_agent_callback()
            response = await llm_with_tools.ainvoke(
                messages,
                config={"callbacks": [agent_callback]}
            )
            
            # Log tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    logger.info(f"🔧 [Chat LLM] Calling tool: {tool_call.get('name')}")
            
            # Append response to messages (don't replace!)
            state["messages"].append(response)
            
            # Extract response content (only if no tool calls)
            if hasattr(response, 'content') and response.content:
                state["chat_response"] = response.content
                state["final_response"] = response.content
            
            return state
            
        except Exception as e:
            logger.error(f"CHAT LLM: Error: {str(e)}")
            error_msg = AIMessage(content="Xin lỗi, tôi gặp một chút khó khăn. Bạn có thể thử lại không?")
            state["messages"] = [error_msg]
            state["chat_response"] = error_msg.content
            return state
    
    async def chat_tools_node(self, state: AgentState) -> AgentState:
        """
        Tool node: Performs the tool call
        
        Following LangGraph agent pattern:
        https://docs.langchain.com/oss/python/langgraph/workflows-agents
        """
        try:
            messages = state.get("messages", [])
            last_message = messages[-1] if messages else None
            
            if not last_message or not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
                return state
            
            # Check if Chat Agent is requesting recommendation
            recommendation_requested = False
            recommendation_params = {}
            for tool_call in last_message.tool_calls:
                if tool_call.get("name") == "request_recommendation":
                    recommendation_requested = True
                    recommendation_params = tool_call.get("args", {})
                    break
            
            # Execute all tool calls
            logger.info(f"⚙️ [Chat Tools] Executing {len(last_message.tool_calls)} tool(s)...")
            tool_results = []
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                logger.info(f"  → {tool_name}")
                
                # Get tool by name
                tool = self.tools_by_name.get(tool_name)
                if not tool:
                    logger.error(f"CHAT TOOLS: Tool '{tool_name}' not found")
                    result = f"Error: Tool '{tool_name}' not found"
                else:
                    try:
                        # Handle JSON string in args if present
                        if isinstance(tool_args, dict) and "__arg1" in tool_args and len(tool_args) == 1:
                            try:
                                json_str = tool_args["__arg1"]
                                if isinstance(json_str, str):
                                    parsed_args = json.loads(json_str)
                                    if isinstance(parsed_args, dict):
                                        tool_args = parsed_args
                            except (json.JSONDecodeError, Exception):
                                pass
                        
                        # Optional validation for create_booking tool (only warn, don't block)
                        if tool_name == "create_booking" and isinstance(tool_args, dict):
                            package_id = tool_args.get("package_id")
                            recommended_package_ids = state.get("recommended_package_ids", [])
                            
                            # Just log warning if no recommendations, but allow booking to proceed
                            # MCP server will validate the package_id anyway
                            if not recommended_package_ids:
                                logger.info(f"ℹ️ Agent creating booking without recommendations (package_id: {package_id})")
                            
                            # Optional: warn if package_id is not in recommended list, but still allow
                            if package_id and recommended_package_ids and package_id not in recommended_package_ids:
                                logger.info(f"ℹ️ Package ID {package_id} not in recommended list, but proceeding anyway")
                        
                        # Execute tool (logging handled by callback handler)
                        try:
                            # Use ainvoke for async execution with callbacks
                            agent_callback = get_current_agent_callback()
                            result = await tool.ainvoke(
                                tool_args,
                                config={"callbacks": [agent_callback]}
                            )
                        except Exception as invoke_error:
                            logger.error(f"CHAT TOOLS: Tool '{tool_name}' failed: {str(invoke_error)}")
                            raise
                    except Exception as e:
                        logger.error(f"CHAT TOOLS: Error executing tool '{tool_name}': {str(e)}")
                        result = f"Error executing tool: {str(e)}"
                
                # Create ToolMessage with result
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                )
                tool_results.append(tool_message)
            
            # Add tool results to state messages
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + tool_results
            
            # If Chat Agent requested recommendation, set flag for routing
            if recommendation_requested:
                state["needs_recommendation"] = True
                state["recommendation_params"] = recommendation_params
            
            return state
            
        except Exception as e:
            logger.error(f"CHAT TOOLS: Error: {str(e)}")
            return state
    
    def should_continue_tool_loop(self, state: AgentState) -> str:
        """
        Decide if we should continue the tool loop or end
        
        Returns:
            "chat_tools" if tool calls exist, END otherwise
        """
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        # If the LLM makes a tool call, then perform an action
        if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "chat_tools"
        
        # Otherwise, end (Chat Agent decided no tools needed)
        return END
    
    def should_recommend(self, state: AgentState) -> str:
        """
        Decide routing after tool execution
        
        If Chat Agent called request_recommendation tool, route to Recommendation Agent.
        Otherwise, loop back to Chat Agent for final response.
        """
        needs_recommendation = state.get("needs_recommendation", False)
        if needs_recommendation:
            logger.info("🔀 [Supervisor] Routing to Recommendation Agent")
            return "recommendation_agent"
        logger.info("✅ [Supervisor] Conversation complete")
        return "chat_llm"

