"""
Chat Agent Nodes
Node functions for Chat Agent graph
"""
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import logging
import json
from app.v1.core.prompts import prompt_manager
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.memory import conversation_memory
from app.v1.services.agent_services.tools import get_chat_tools
from app.v1.core.logging_config import get_current_agent_callback
from langgraph.graph import END

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
        
        Following LangGraph agent pattern:
        https://docs.langchain.com/oss/python/langgraph/workflows-agents
        """
        try:
            conversation_id = state.get("conversation_id", "default_conv")
            
            # Get conversation-specific memory
            memory = conversation_memory.get_memory(conversation_id)
            
            # Prepare messages with system prompt from agent.yaml
            # Reads from: agents[name='chat_agent'].config.prompts.system
            system_prompt = prompt_manager.get_system_prompt('chat_agent')
            
            # Add context about recommended package_ids if available
            recommended_package_ids = state.get("recommended_package_ids", [])
            if recommended_package_ids:
                package_ids_context = f"\n\nIMPORTANT CONTEXT: Available package IDs from recent recommendations: {', '.join(recommended_package_ids)}. When creating booking, use one of these exact package IDs."
                system_prompt += package_ids_context
            
            # Combine memory messages with current state messages
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(list(memory.messages))
            
            # Add current state messages
            current_messages = state.get("messages", [])
            if current_messages:
                for msg in current_messages:
                    if not isinstance(msg, SystemMessage):
                        messages.append(msg)
            
            # Get LLM response with tools bound (with callback handler for logging)
            # Chat Agent will process the recommendation message and create a natural response
            llm_with_tools = self.llm.bind_tools(self.tools)
            agent_callback = get_current_agent_callback()
            response = await llm_with_tools.ainvoke(
                messages,
                config={"callbacks": [agent_callback]}
            )
            
            # Store response in state messages
            state["messages"] = [response]
            
            # Extract response content
            if hasattr(response, 'content'):
                state["chat_response"] = response.content
                # Update final_response - Chat Agent's response is the final one
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
            
            # Execute all tool calls (tool calls will be logged by callback handler)
            tool_results = []
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                
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
    
    def should_continue_tool_loop(self, state: AgentState) -> Literal["chat_tools", END]:
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
    
    def should_recommend(self, state: AgentState) -> Literal["recommendation_agent", "chat_llm"]:
        """
        Decide routing after tool execution
        
        If Chat Agent called request_recommendation tool, route to Recommendation Agent.
        Otherwise, loop back to Chat Agent for final response.
        """
        needs_recommendation = state.get("needs_recommendation", False)
        if needs_recommendation:
            return "recommendation_agent"
        return "chat_llm"
