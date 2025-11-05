"""
Simple Logging Configuration for Agent System
Following LangChain best practices with LangSmith integration
"""
import logging
import sys
import os
import json
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish

# Try to import colorama for cross-platform colored output
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback ANSI codes (works on most terminals)
    class Fore:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        RESET = '\033[0m'
        BRIGHT = '\033[1m'
    class Style:
        RESET_ALL = '\033[0m'


class SimpleFormatter(logging.Formatter):
    """Simple formatter - minimal output for cleaner logs"""
    
    def __init__(self):
        super().__init__(
            fmt='%(message)s',  # Just show message, no timestamp/name for cleaner output
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
        """Run when LLM starts running - minimal logging"""
        # Only log if DEBUG level
        self.logger.debug("LLM call started")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running - minimal logging"""
        # Only log if DEBUG level
        self.logger.debug("LLM call completed")
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when LLM errors."""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.RED}{Style.BRIGHT}❌ LLM Error:{Style.RESET_ALL} {str(error)}", flush=True)
        else:
            print(f"\n❌ LLM Error: {str(error)}", flush=True)
        self.logger.error(f"LLM ERROR: {str(error)}")
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running - minimal logging"""
        # Only log if DEBUG level
        self.logger.debug("Chain started")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running - minimal logging"""
        # Only log if DEBUG level
        self.logger.debug("Chain ended")
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when chain errors."""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.RED}{Style.BRIGHT}❌ Chain Error:{Style.RESET_ALL} {str(error)}", flush=True)
        else:
            print(f"\n❌ Chain Error: {str(error)}", flush=True)
        self.logger.error(f"CHAIN ERROR: {str(error)}")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Run on agent action - minimal logging"""
        # Only log if DEBUG level
        self.logger.debug(f"Agent action: {action.tool}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent finish - minimal logging"""
        # Only log if DEBUG level
        self.logger.debug("Agent finished")
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running - LangChain Agent Executor style with colors."""
        tool_name = "unknown"
        if serialized:
            tool_name = serialized.get("name", "unknown")
        
        # Format input nicely if it's JSON-like
        try:
            # Try to parse and pretty-print if it's JSON
            if isinstance(input_str, str) and (input_str.startswith('{') or input_str.startswith('[')):
                parsed = json.loads(input_str)
                formatted_input = json.dumps(parsed, indent=2, ensure_ascii=False)
            else:
                formatted_input = input_str
        except:
            formatted_input = input_str
        
        # LangChain Agent Executor style output with colors
        # Format: > Entering new Tool: tool_name
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}> Entering new Tool: {tool_name}{Style.RESET_ALL}", flush=True)
            print(f"{Fore.YELLOW}{Style.BRIGHT}Input:{Style.RESET_ALL}", flush=True)
            # Truncate long inputs
            if len(formatted_input) > 300:
                print(f"{Fore.YELLOW}{formatted_input[:300]}...{Style.RESET_ALL}", flush=True)
            else:
                print(f"{Fore.YELLOW}{formatted_input}{Style.RESET_ALL}", flush=True)
        else:
            print(f"\n> Entering new Tool: {tool_name}", flush=True)
            print(f"Input:", flush=True)
            if len(formatted_input) > 300:
                print(f"{formatted_input[:300]}...", flush=True)
            else:
                print(formatted_input, flush=True)
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running - LangChain Agent Executor style with colors."""
        tool_name = kwargs.get("name", "unknown")
        
        # Format output nicely if it's JSON-like
        output_str = str(output)
        try:
            # Try to parse and pretty-print if it's JSON
            if isinstance(output_str, str) and (output_str.startswith('{') or output_str.startswith('[')):
                parsed = json.loads(output_str)
                formatted_output = json.dumps(parsed, indent=2, ensure_ascii=False)
            else:
                formatted_output = output_str
        except:
            formatted_output = output_str
        
        # LangChain Agent Executor style output with colors
        # Display full output (no truncation for tool results - they're important)
        if COLORAMA_AVAILABLE:
            print(f"{Fore.GREEN}{Style.BRIGHT}> Tool Output:{Style.RESET_ALL}", flush=True)
            # Print full formatted output (only truncate if extremely long > 50000 chars)
            if len(formatted_output) > 50000:
                print(f"{Fore.GREEN}{formatted_output[:50000]}...{Style.RESET_ALL}", flush=True)
                print(f"{Fore.CYAN}(Output truncated at 50000 chars, {len(formatted_output)} chars total){Style.RESET_ALL}", flush=True)
            else:
                print(f"{Fore.GREEN}{formatted_output}{Style.RESET_ALL}", flush=True)
            print(f"{Fore.CYAN}{Style.BRIGHT}> Finished tool: {tool_name}{Style.RESET_ALL}\n", flush=True)
        else:
            print(f"> Tool Output:", flush=True)
            # Print full formatted output (only truncate if extremely long > 50000 chars)
            if len(formatted_output) > 50000:
                print(f"{formatted_output[:50000]}...", flush=True)
                print(f"(Output truncated at 50000 chars, {len(formatted_output)} chars total)", flush=True)
            else:
                print(formatted_output, flush=True)
            print(f"> Finished tool: {tool_name}\n", flush=True)
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when tool errors - LangChain Agent Executor style."""
        tool_name = kwargs.get("name", "unknown")
        
        # LangChain Agent Executor style error output with colors
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.RED}{Style.BRIGHT}> Tool Error: {tool_name}{Style.RESET_ALL}", flush=True)
            print(f"{Fore.RED}Error: {str(error)}{Style.RESET_ALL}", flush=True)
            print(f"{Fore.RED}Error Type: {type(error).__name__}{Style.RESET_ALL}\n", flush=True)
        else:
            print(f"\n> Tool Error: {tool_name}", flush=True)
            print(f"Error: {str(error)}", flush=True)
            print(f"Error Type: {type(error).__name__}\n", flush=True)
        
        # Also log via logger
        self.logger.error(f"> Tool Error: {tool_name}")
        self.logger.error(f"Error: {str(error)}")
        self.logger.error(f"Error Type: {type(error).__name__}")
    
    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on arbitrary text."""
        self.logger.debug(f"Text: {text}")


# Global flag to prevent duplicate setup
_logging_configured = False

def setup_logging(
    level: str = "INFO",
    enable_langchain_tracing: bool = False,
    enable_callback: bool = True,
    langchain_api_key: str = "",
    langchain_project: str = "ai-assistant-backend",
    langsmith_endpoint: str = ""
) -> AgentCallbackHandler:
    """
    Setup simple logging for the agent system with LangSmith integration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_langchain_tracing: Enable LangChain tracing
        enable_callback: Enable custom callback handler
        langchain_api_key: LangSmith API key (optional)
        langchain_project: LangSmith project name
        langsmith_endpoint: LangSmith API endpoint (optional)
        
    Returns:
        AgentCallbackHandler instance
    """
    global _logging_configured
    
    # Prevent duplicate setup
    if _logging_configured:
        return get_agent_callback() if enable_callback else None
    
    from app.v1.core.config import settings
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(SimpleFormatter())
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers - reduce verbosity
    loggers_config = {
        'app.v1.services.agent_services': 'WARNING',  # Only show warnings/errors
        'app.v1.services.agent_services.nodes': 'WARNING',  # Reduce node logs
        'app.v1.services.agent_services.agents': 'WARNING',  # Reduce agent logs
        'app.v1.services.agent_services.memory': 'WARNING',  # Reduce memory logs
        'app.v1.services.agent_services.mcp_intergation': 'WARNING',  # Reduce MCP logs
        'agent.callback': 'DEBUG',  # Keep callback for tool logging
        'langchain': 'WARNING',  # Too verbose
        'langgraph': 'WARNING',  # Too verbose
        'openai': 'WARNING',  # Too verbose
        'httpx': 'WARNING',   # Too verbose
        'httpcore': 'WARNING', # Too verbose
        'graphiti_core': 'WARNING',  # Disable Graphiti verbose logs
        'graphiti_core.driver': 'WARNING',
        'graphiti_core.llm_client': 'WARNING',
        'graphiti_core.embedder': 'WARNING',
        'mcp_server': 'WARNING',  # Reduce MCP server logs
        'src.mcp_server': 'WARNING',  # Reduce MCP server logs
    }
    
    for logger_name, logger_level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, logger_level.upper()))
    
    # Enable LangChain tracing if requested
    if enable_langchain_tracing:
        os.environ['LANGCHAIN_TRACING_V2'] = 'true'
        os.environ['LANGCHAIN_PROJECT'] = langchain_project or settings.LANGCHAIN_PROJECT
        
        # Set API key if provided
        api_key = langchain_api_key or settings.LANGCHAIN_API_KEY
        if api_key:
            os.environ['LANGCHAIN_API_KEY'] = api_key
        
        # Set LangSmith endpoint if provided
        endpoint = langsmith_endpoint or settings.LANGSMITH_ENDPOINT
        if endpoint:
            os.environ['LANGCHAIN_ENDPOINT'] = endpoint
        
        if api_key:
            logging.info(f"✅ LangSmith tracing enabled (project: {langchain_project or settings.LANGCHAIN_PROJECT}, endpoint: {endpoint})")
        else:
            logging.warning("⚠️ LangSmith tracing enabled but no API key provided. Set LANGCHAIN_API_KEY in .env")
    
    # Create callback handler
    callback_handler = None
    if enable_callback:
        callback_handler = AgentCallbackHandler()
    
    # Mark as configured (already declared global at start of function)
    _logging_configured = True
    
    logging.info(f"Logging configured (level={level}, tracing={enable_langchain_tracing})")
    
    return callback_handler


def get_agent_callback() -> AgentCallbackHandler:
    """Get or create agent callback handler"""
    return AgentCallbackHandler()


# Module-level agent_callback - will be set by main.py
agent_callback = None


def get_current_agent_callback():
    """Get the current agent callback instance"""
    global agent_callback
    if agent_callback is None:
        # Create a default callback if not initialized
        agent_callback = AgentCallbackHandler()
    return agent_callback

