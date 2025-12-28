"""
Admin Agent LangGraph Nodes
Node functions for admin agent workflow
Config loaded from admin_agent.yaml
"""
import logging
from typing import Dict, Any, Literal
from langgraph.graph import END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.v1.services.agent_services.state import AgentState
from .config import admin_agent_config, get_system_prompt
from .tools import get_admin_tools

logger = logging.getLogger(__name__)


class AdminAgentNodes:
    """
    Node functions for Admin Agent LangGraph
    
    Implements the ReAct pattern:
    1. admin_llm_node: LLM decides action
    2. admin_tools_node: Execute tools
    3. should_continue: Routing logic
    """
    
    def __init__(self, llm):
        """
        Initialize Admin Agent nodes
        
        Args:
            llm: LLM instance with tools bound
        """
        self.llm = llm
        self.tools = get_admin_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    async def admin_llm_node(self, state: AgentState) -> AgentState:
        """
        LLM node: Decides whether to call a tool or respond directly
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with LLM response
        """
        logger.info("🤖 [Admin LLM] Processing...")
        
        try:
            messages = state.get("messages", [])
            
            # Add system prompt if not present
            has_system = any(
                isinstance(m, SystemMessage) for m in messages
            )
            
            if not has_system:
                messages = [
                    SystemMessage(content=get_system_prompt())
                ] + messages
            
            # Call LLM with tools
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Update state
            state["messages"] = messages + [response]
            
            # Extract response content
            if hasattr(response, 'content') and response.content:
                state["admin_response"] = response.content
                state["final_response"] = response.content
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Admin LLM Error: {str(e)}")
            error_msg = AIMessage(
                content="Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu. Vui lòng thử lại."
            )
            state["messages"] = state.get("messages", []) + [error_msg]
            state["admin_response"] = error_msg.content
            return state
    
    async def admin_tools_node(self, state: AgentState) -> AgentState:
        """
        Tools node: Executes tool calls from LLM
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with tool results
        """
        logger.info("🔧 [Admin Tools] Executing...")
        
        try:
            messages = state.get("messages", [])
            last_message = messages[-1] if messages else None
            
            if not last_message or not hasattr(last_message, 'tool_calls'):
                return state
            
            tool_calls = last_message.tool_calls
            if not tool_calls:
                return state
            
            # Execute each tool call
            tool_messages = []
            
            for tool_call in tool_calls:
                tool_name = tool_call.get('name')
                tool_args = tool_call.get('args', {})
                tool_id = tool_call.get('id', tool_name)
                
                logger.info(f"⚙️ Executing tool: {tool_name}")
                
                if tool_name in self.tools_by_name:
                    tool = self.tools_by_name[tool_name]
                    try:
                        # Use ainvoke if available (better for async tools)
                        if hasattr(tool, 'ainvoke'):
                            result = await tool.ainvoke(tool_args)
                        else:
                            result = tool.invoke(tool_args)
                            
                        # Fix for "coroutine was never awaited" issue:
                        # If result is a coroutine object, it means it wasn't awaited inside invoke/ainvoke
                        import asyncio
                        if asyncio.iscoroutine(result):
                            logger.info(f"⏳ Awaiting coroutine result for admin tool: {tool_name}")
                            result = await result
                            
                        result_str = str(result) if not isinstance(result, str) else result
                    except Exception as e:
                        result_str = f"Error executing {tool_name}: {str(e)}"
                        logger.error(result_str)
                else:
                    result_str = f"Unknown tool: {tool_name}"
                    logger.warning(result_str)
                
                # Create tool message
                tool_messages.append(
                    ToolMessage(
                        content=result_str,
                        tool_call_id=tool_id
                    )
                )
            
            # Add tool messages to state
            state["messages"] = messages + tool_messages
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Admin Tools Error: {str(e)}")
            return state
    
    def should_continue(self, state: AgentState) -> Literal["admin_tools", "__end__"]:
        """
        Routing logic: Continue to tools or end
        
        Args:
            state: Current agent state
            
        Returns:
            "admin_tools" if tool calls exist, END otherwise
        """
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        # If LLM made tool calls, execute them
        if (last_message and 
            hasattr(last_message, 'tool_calls') and 
            last_message.tool_calls):
            return "admin_tools"
        
        # Otherwise, end
        return END
