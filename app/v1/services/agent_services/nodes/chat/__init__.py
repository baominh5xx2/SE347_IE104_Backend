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
            
            # If we have tour packages in state from previous recommendation, inject them
            tour_packages_in_state = state.get("tour_packages", [])
            if tour_packages_in_state:
                packages_str = "\n\n🎯 AVAILABLE TOURS (use these exact package_ids for booking):\n"
                for idx, pkg in enumerate(tour_packages_in_state[:10], 1):  # Max 10
                    packages_str += f"{idx}. {pkg.get('package_name', 'Unknown')}\n"
                    packages_str += f"   📍 {pkg.get('destination', '')} - {pkg.get('duration_days', 0)} ngày\n"
                    packages_str += f"   💰 {pkg.get('price', 0):,.0f} VNĐ/người\n"
                    packages_str += f"   🆔 package_id: {pkg.get('package_id', 'N/A')}\n\n"
                system_prompt += packages_str
                logger.info(f"✅ Injected {len(tour_packages_in_state)} tours from state into agent context")
                        
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
            
            # Extract user_id and user_phone from state (will be used for auto-injection)
            user_id = state.get("user_id", "")
            user_phone = state.get("user_phone", "")
            
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
                        
                        # Auto-inject user_id for get_user_bookings tool
                        if tool_name == "get_user_bookings" and user_id:
                            tool_args["user_id"] = user_id
                            logger.info(f"✅ Auto-injected user_id '{user_id}' into get_user_bookings")
                        
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
                            
                            # === CRITICAL FIX: Auto-inject tour data from state ===
                            # LLM cannot remember full JSON objects. We MUST inject the data from state.
                            if tool_name == "generate_tour_ui":
                                if tour_packages:
                                    tool_args["packages"] = tour_packages
                                    logger.info(f"✅ Auto-injected {len(tour_packages)} packages from state into generate_tour_ui tool")
                                    # Log first package for verification
                                    if len(tour_packages) > 0:
                                        pkg = tour_packages[0]
                                        logger.info(f"   Sample data: {pkg.get('package_name')} | Img: {str(pkg.get('image_urls') or pkg.get('image_url'))[:30]}...")
                                else:
                                    logger.warning("⚠️ generate_tour_ui called but NO packages found in state!")

                            # SMART ID RESOLUTION: Map index/number/hallucinated_id to real package_id
                            # If package_id is a small number (e.g. "1", "2") or "tour 1", map it to real ID
                            if package_id and tour_packages:
                                try:
                                    # 1. Try index-based mapping (e.g. "1", "tour 1")
                                    clean_id = str(package_id).lower().replace("tour", "").replace("số", "").strip()
                                    if clean_id.isdigit():
                                        idx = int(clean_id) - 1 # 1-based index to 0-based
                                        if 0 <= idx < len(tour_packages):
                                            real_package_id = tour_packages[idx].get("package_id")
                                            if real_package_id:
                                                logger.info(f"🔄 Smart Resolution: Mapped index '{package_id}' -> '{real_package_id}'")
                                                tool_args["package_id"] = real_package_id
                                                package_id = real_package_id # Update local var
                                    
                                    # 2. Try fallback for hallucinated IDs (e.g. "pkg_tour_1", "package_1")
                                    # If it's NOT a valid UUID and we have packages, default to the first package or try to match
                                    elif len(str(package_id)) < 30: # UUIDs are 36 chars
                                        logger.warning(f"⚠️ Detect potential hallucinated ID: '{package_id}'")
                                        
                                        # Simple heuristic: if user says "tour 1" or similar, we handled it above.
                                        # If LLM hallucinated "pkg_tour_1" likely it means the first tour presented.
                                        if "1" in str(package_id) and len(tour_packages) >= 1:
                                            real_package_id = tour_packages[0].get("package_id")
                                            logger.info(f"🔄 Smart Resolution: Mapped hallucinated '{package_id}' -> '{real_package_id}' (First package)")
                                            tool_args["package_id"] = real_package_id
                                            package_id = real_package_id
                                        elif "2" in str(package_id) and len(tour_packages) >= 2:
                                            real_package_id = tour_packages[1].get("package_id")
                                            logger.info(f"🔄 Smart Resolution: Mapped hallucinated '{package_id}' -> '{real_package_id}' (Second package)")
                                            tool_args["package_id"] = real_package_id
                                            package_id = real_package_id
                                        else:
                                            # Ultimate fallback: Use the first package if available
                                            # This is better than crashing with invalid UUID
                                            if tour_packages:
                                                real_package_id = tour_packages[0].get("package_id")
                                                logger.info(f"🔄 Smart Resolution: Fallback mapped '{package_id}' -> '{real_package_id}' (First available)")
                                                tool_args["package_id"] = real_package_id
                                                package_id = real_package_id
                                                
                                except Exception as map_err:
                                    logger.warning(f"⚠️ Failed to map package_id '{package_id}': {map_err}")

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
                            
                            # === MCP-UI INTEGRATION ===
                            # Capture the UI Resource from the tool result
                            if tool_name == "generate_tour_ui" and isinstance(result, dict):
                                # Support both legacy HTML and new UI Resource format
                                html_content = result.get("html")
                                ui_resource = result.get("ui_resource")
                                
                                if ui_resource:
                                    state["mcp_ui_resource"] = ui_resource
                                    logger.info(f"✅ Saved MCP UI Resource to state (URI: {ui_resource.get('uri', 'unknown')})")
                                
                                if html_content:
                                    state["mcp_ui_html"] = html_content
                                    
                                if ui_resource or html_content:
                                    result_str = "MCP UI generated successfully. UI Resource ready for client rendering."
                                else:
                                    result_str = str(result)
                            else:
                                result_str = str(result)
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

