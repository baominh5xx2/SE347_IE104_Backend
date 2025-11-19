"""
Logging Configuration with Colors
"""
import logging
import sys
import os
import warnings
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        record.name = f"\033[90m{record.name}{self.COLORS['RESET']}"
        return super().format(record)
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )


class AgentCallbackHandler(BaseCallbackHandler):
    """
    Simple callback handler for agent logging
    Following LangChain's callback pattern
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("agent.callback")
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.logger.info("=== LLM CALL STARTED ===")
        if serialized:
            self.logger.debug(f"Model: {serialized.get('name', 'unknown')}")
        for i, prompt in enumerate(prompts, 1):
            self.logger.debug(f"Prompt {i}: {prompt[:100]}...")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        self.logger.info("LLM CALL COMPLETED")
        if response.generations:
            for i, generation in enumerate(response.generations[0], 1):
                self.logger.debug(f"Generation {i}: {generation.text[:100]}...")
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when LLM errors."""
        self.logger.error(f"LLM ERROR: {str(error)}")
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        chain_name = "unknown"
        if serialized:
            chain_name = serialized.get("name", "unknown")
        self.logger.info(f"CHAIN START: {chain_name}")
        if inputs:
            self.logger.debug(f"Inputs: {inputs}")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""
        self.logger.info("CHAIN END")
        if outputs:
            self.logger.debug(f"Outputs: {outputs}")
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when chain errors."""
        self.logger.error(f"CHAIN ERROR: {str(error)}")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Run on agent action."""
        self.logger.info("AGENT ACTION")
        self.logger.info(f"Tool: {action.tool}")
        self.logger.info(f"Input: {action.tool_input}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent finish."""
        self.logger.info("AGENT FINISHED")
        self.logger.info(f"Output: {finish.return_values}")
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running."""
        tool_name = "unknown"
        if serialized:
            tool_name = serialized.get("name", "unknown")
        self.logger.info(f"TOOL START: {tool_name}")
        self.logger.debug(f"Input: {input_str}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        self.logger.info("TOOL END")
        try:
            if isinstance(output, str) and len(output) > 100:
                self.logger.debug(f"Output: {output[:100]}...")
            elif output:
                self.logger.debug(f"Output: {str(output)[:100]}")
        except:
            pass
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when tool errors."""
        self.logger.error(f"TOOL ERROR: {str(error)}")
    
    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on arbitrary text."""
        self.logger.debug(f"Text: {text}")


def setup_logging(
    level: str = "INFO",
    enable_langchain_tracing: bool = False,
    enable_callback: bool = True
) -> AgentCallbackHandler:
    """
    Setup simple logging for the agent system
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_langchain_tracing: Enable LangChain tracing
        enable_callback: Enable custom callback handler
        
    Returns:
        AgentCallbackHandler instance
    """
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)
    
    # Suppress warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.filterwarnings('ignore', module='supabase')
    warnings.filterwarnings('ignore', module='pydantic')
    warnings.filterwarnings('ignore', module='fastmcp')
    warnings.filterwarnings('ignore', module='websockets')
    warnings.filterwarnings('ignore', module='langgraph')
    
    # Configure specific loggers
    loggers_config = {
        'app.v1.services.agent_services': level,
        'src.mcp_server': 'WARNING',
        'mcp': 'WARNING',
        'uvicorn': 'WARNING',
        'uvicorn.access': 'WARNING',
        'watchfiles': 'WARNING',
        'openai': 'WARNING',
        'httpx': 'WARNING',
        'httpcore': 'WARNING',
        'langchain': 'WARNING',
        'langgraph': 'WARNING',
        'graphiti_core': 'WARNING'
    }
    
    for logger_name, logger_level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, logger_level.upper()))
    
    # Enable LangChain tracing if requested
    if enable_langchain_tracing:
        os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    
    # Create callback handler
    callback_handler = None
    if enable_callback:
        callback_handler = AgentCallbackHandler()
    
    return callback_handler


def get_agent_callback() -> AgentCallbackHandler:
    """Get or create agent callback handler"""
    return AgentCallbackHandler()


def get_current_agent_callback() -> AgentCallbackHandler:
    """Get current agent callback handler (alias for get_agent_callback)"""
    return get_agent_callback()


# Initialize logging on import
agent_callback = setup_logging(
    level="INFO",
    enable_langchain_tracing=False,  # Set to True if you want LangSmith tracing
    enable_callback=True
)

