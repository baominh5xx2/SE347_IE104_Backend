"""
Chat Agent Nodes
Node functions for Chat Agent graph
"""
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import END
import logging
import json
import asyncio
from app.v1.core.prompts import prompt_manager
from app.v1.services.agent_services.state import AgentState
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
        
        Follows standard LangGraph agent pattern - uses state messages only.
        No external context injection - LLM works with conversation history from state.
        """
        logger.info("🤖 [Chat LLM] Processing...")
        try:
            # Get system prompt
            system_prompt = prompt_manager.get_system_prompt('chat_agent')
            
            # Get current messages from state (LangGraph checkpointer handles persistence)
            current_messages = state.get("messages", [])
            
            # Build messages for LLM - standard LangGraph pattern
            messages = [SystemMessage(content=system_prompt)]
            
            # Add all state messages (conversation history)
            if current_messages:
                for msg in current_messages:
                    if not isinstance(msg, SystemMessage):
                        messages.append(msg)
            
            # Get LLM response with tools bound
            # Try with tools first, fallback to no tools if provider doesn't support it
            agent_callback = get_current_agent_callback()
            try:
                llm_with_tools = self.llm.bind_tools(self.tools)
                response = await llm_with_tools.ainvoke(
                    messages,
                    config={"callbacks": [agent_callback]}
                )
            except Exception as e:
                error_msg = str(e)
                # Check if error is about tool calling not supported
                if "tool choice" in error_msg.lower() or "tool-call" in error_msg.lower():
                    logger.warning(f"⚠️ Tool calling not supported by LLM provider, falling back to no tools: {error_msg}")
                    # Fallback: use LLM without tools
                    response = await self.llm.ainvoke(
                        messages,
                        config={"callbacks": [agent_callback]}
                    )
                else:
                    # Re-raise if it's a different error
                    raise
            
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
            
            # Extract user_id and user_phone from state (will be used for auto-injection)
            user_id = state.get("user_id", "")
            user_phone = state.get("user_phone", "")
            
            # Prepare tool execution tasks for parallel execution
            logger.info(f"⚙️ [Chat Tools] Executing {len(last_message.tool_calls)} tool(s)...")
            
            # Define tool dependencies (tools that must run sequentially)
            # generate_payment_ui depends on create_payment completing first
            DEPENDENCIES = {
                "generate_payment_ui": ["create_payment"],
                "generate_tour_ui": ["request_recommendation", "search_tour_packages"]
            }
            
            # Group tools by dependency level (independent tools can run in parallel)
            async def prepare_tool_task(tool_call):
                """Prepare a single tool call for execution"""
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                
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
                
                # Auto-inject user_id for get_user_bookings tool
                if tool_name == "get_user_bookings" and user_id:
                    tool_args["user_id"] = user_id
                    logger.info(f"✅ Auto-injected user_id '{user_id}' into get_user_bookings")
                
                # Auto-inject payment data for generate_payment_ui from the latest create_payment result
                if tool_name == "generate_payment_ui":
                    latest_payment = state.get("latest_payment", {})
                    if isinstance(latest_payment, dict):
                        if latest_payment.get("payment_url"):
                            tool_args["payment_url"] = latest_payment.get("payment_url")
                        if latest_payment.get("booking_id"):
                            tool_args["booking_id"] = latest_payment.get("booking_id")
                        if latest_payment.get("amount") is not None:
                            tool_args["total_amount"] = latest_payment.get("amount")
                        booking_info = latest_payment.get("booking_info", {}) or {}
                        tour_name = latest_payment.get("tour_name") or booking_info.get("tour_name")
                        if tour_name:
                            tool_args["tour_name"] = tour_name
                        if latest_payment.get("payment_method"):
                            tool_args["payment_method"] = latest_payment.get("payment_method")
                        logger.info(f"✅ Auto-injected payment data into generate_payment_ui from latest create_payment")
                
                # Auto-inject user_phone and user_id for create_booking tool
                if tool_name == "create_booking":
                    # Inject user_phone if available and not provided
                    if user_phone and not tool_args.get("user_phone"):
                        tool_args["user_phone"] = user_phone
                        logger.info(f"✅ Auto-injected user_phone '{user_phone}' into create_booking")
                    
                    # Inject user_id if available and not provided
                    if user_id and not tool_args.get("user_id"):
                        tool_args["user_id"] = user_id
                        logger.info(f"✅ Auto-injected user_id '{user_id}' into create_booking")
                
                # Optional validation for create_booking tool (only warn, don't block)
                if tool_name == "create_booking" and isinstance(tool_args, dict):
                    package_id = tool_args.get("package_id")
                    
                    # Get packages from state (persisted from recommendation)
                    tour_packages = state.get("tour_packages", [])
                    recommended_package_ids = [pkg.get("package_id") for pkg in tour_packages if pkg.get("package_id")]
                    
                    # Simple safety net: validate UUID, else fallback to first recommended package
                    if package_id and tour_packages:
                        import re
                        
                        package_id_str = str(package_id)
                        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
                        is_valid_uuid = bool(uuid_pattern.match(package_id_str))
                        
                        if not is_valid_uuid:
                            real_package_id = tour_packages[0].get("package_id")
                            if real_package_id:
                                logger.warning(f"⚠️ Invalid package_id '{package_id}', using first available '{real_package_id}'")
                                tool_args["package_id"] = real_package_id
                                package_id = real_package_id
                        else:
                            logger.info(f"✅ Valid package_id '{package_id}' found")
                    
                    # Just log warning if no recommendations, but allow booking to proceed
                    if not recommended_package_ids:
                        logger.info(f"ℹ️ Agent creating booking without recommendations (package_id: {package_id})")
                    
                    # Optional: warn if package_id is not in recommended list, but still allow
                    if package_id and recommended_package_ids and package_id not in recommended_package_ids:
                        logger.info(f"ℹ️ Package ID {package_id} not in recommended list, but proceeding anyway")
                
                # === CRITICAL FIX: Auto-inject tour data from state ===
                if tool_name == "generate_tour_ui":
                    tour_packages = state.get("tour_packages", [])
                    if tour_packages:
                        tool_args["packages"] = tour_packages
                        logger.info(f"✅ Auto-injected {len(tour_packages)} packages from state into generate_tour_ui tool")
                        if len(tour_packages) > 0:
                            pkg = tour_packages[0]
                            logger.info(f"   Sample data: {pkg.get('package_name')} | Img: {str(pkg.get('image_urls') or pkg.get('image_url'))[:30]}...")
                    else:
                        logger.warning("⚠️ generate_tour_ui called but NO packages found in state!")
                
                # Get tool by name
                tool = self.tools_by_name.get(tool_name)
                if not tool:
                    logger.error(f"CHAT TOOLS: Tool '{tool_name}' not found")
                    return tool_call["id"], f"Error: Tool '{tool_name}' not found"
                
                # Execute tool (async)
                try:
                    agent_callback = get_current_agent_callback()
                    logger.info(f"  → {tool_name}")
                    result = await tool.ainvoke(
                        tool_args,
                        config={"callbacks": [agent_callback]}
                    )
                    
                    # Fix for "coroutine was never awaited" issue:
                    # If result is a coroutine object, it means it wasn't awaited inside ainvoke
                    if asyncio.iscoroutine(result):
                        logger.info(f"⏳ Awaiting coroutine result for tool: {tool_name}")
                        result = await result
                    
                    # Return result with tool name for state updates after parallel execution
                    return tool_call["id"], tool_name, result
                    
                except Exception as invoke_error:
                    logger.error(f"CHAT TOOLS: Tool '{tool_name}' failed: {str(invoke_error)}")
                    return tool_call["id"], tool_name, f"Error executing tool: {str(invoke_error)}"
            
            # Execute tools in parallel (all independent tools run concurrently)
            # Note: We don't enforce strict dependency ordering here since most tools are independent
            # Dependencies like generate_payment_ui -> create_payment are handled by state injection
            tool_tasks = [prepare_tool_task(tool_call) for tool_call in last_message.tool_calls]
            tool_results_data = await asyncio.gather(*tool_tasks, return_exceptions=True)
            
            # Create ToolMessages from results and handle state updates sequentially
            tool_results = []
            for tool_call in last_message.tool_calls:
                # Find matching result
                tool_call_id = tool_call["id"]
                tool_name = tool_call["name"]
                result_str = None
                result_obj = None
                
                for result_data in tool_results_data:
                    if isinstance(result_data, Exception):
                        logger.error(f"CHAT TOOLS: Exception in tool execution: {str(result_data)}")
                        result_str = f"Error: {str(result_data)}"
                        break
                    elif isinstance(result_data, tuple) and len(result_data) >= 2 and result_data[0] == tool_call_id:
                        if len(result_data) == 3:
                            # New format: (tool_call_id, tool_name, result)
                            _, _, result_obj = result_data
                        else:
                            # Old format: (tool_call_id, result_str)
                            result_obj = result_data[1]
                        break
                
                if result_str is None:
                    if result_obj is None:
                        result_str = "Error: No result returned from tool"
                    else:
                        # Handle state updates for specific tools (sequential to avoid race conditions)
                        if tool_name == "create_payment" and isinstance(result_obj, dict):
                            if result_obj.get("success"):
                                state["latest_payment"] = result_obj
                                logger.info("✅ Stored latest payment data in state for payment UI generation")
                        
                        # === MCP-UI INTEGRATION ===
                        if tool_name in ["generate_tour_ui", "generate_payment_ui"] and isinstance(result_obj, dict):
                            html_content = result_obj.get("html")
                            ui_resource = result_obj.get("ui_resource")
                            
                            if ui_resource:
                                state["mcp_ui_resource"] = ui_resource
                                logger.info(f"✅ Saved MCP UI Resource to state (URI: {ui_resource.get('uri', 'unknown')}, type: {ui_resource.get('type', 'unknown')})")
                            
                            if html_content:
                                state["mcp_ui_html"] = html_content
                            
                            if ui_resource or html_content:
                                result_str = "MCP UI generated successfully. UI Resource ready for client rendering."
                            else:
                                result_str = str(result_obj)
                        else:
                            result_str = str(result_obj)
                
                tool_message = ToolMessage(
                    content=str(result_str),
                    tool_call_id=tool_call_id
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
            # CRITICAL FIX: If recommendation is requested, ALWAYS go to recommendation agent
            # even if there's a chat response, to ensure tours are displayed.
            logger.info("🔀 [Supervisor] Routing to Recommendation Agent")
            return "recommendation_agent"
        
        # Early exit: if we already have a response and no recommendation needed,
        # skip back to chat_llm for final formatting or END
        chat_response = state.get("chat_response", "")
        final_response = state.get("final_response", "")
        if chat_response or final_response:
            logger.info("✅ [Supervisor] Skipping recommendation - response already complete")
            return "chat_llm"
            
        logger.info("✅ [Supervisor] Conversation complete")
        return "chat_llm"

