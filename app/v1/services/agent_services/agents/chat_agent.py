"""
Chat Agent
Main conversational agent with tool calling capabilities
"""
from typing import Dict, Any, List
import logging
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_community.chat_message_histories import ChatMessageHistory
from app.v1.core.prompts import prompt_manager
from app.v1.services.agent_services.agents.base_agent import BaseAgent
from app.v1.services.agent_services.tools import get_chat_tools

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """
    Chat Agent - Handles conversation with tool calling loop
    
    Uses ReAct pattern: Reasoning + Acting
    Can call tools including request_recommendation to communicate with Recommendation Agent
    """
    
    def __init__(self):
        """Initialize Chat Agent"""
        super().__init__(
            name="Chat Agent",
            temperature=1.0
        )
        
        # Initialize memory storage - will create per-conversation memory
        self.memory_storage: Dict[str, ChatMessageHistory] = {}
        
        # Initialize tools
        self.tools = get_chat_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        
        logger.info(f"✅ Chat Agent initialized with {len(self.tools)} tools")
    
    def get_conversation_memory(self, conversation_id: str) -> ChatMessageHistory:
        """Get or create memory for a specific conversation"""
        if conversation_id not in self.memory_storage:
            self.memory_storage[conversation_id] = ChatMessageHistory()
        return self.memory_storage[conversation_id]
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process chat message (implements BaseAgent interface)
        
        Args:
            state: Agent state
            
        Returns:
            Updated state
        """
        # This will be handled by graph nodes
        # Chat Agent logic is in nodes/chat/
        return state
