"""
Prompt Management - Load prompts from agent.yaml
Following LangGraph best practices
"""
import yaml
import os
from typing import Dict, Any
from pathlib import Path

class PromptManager:
    """Manages prompt templates from agent.yaml"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent.parent / "agent.yaml"
        self.config = self._load_config()
        self.prompts = self._extract_prompts()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load agent.yaml configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading agent.yaml: {e}")
            return {}
    
    def _extract_prompts(self) -> Dict[str, Dict[str, str]]:
        """Extract all prompts from config"""
        prompts = {}
        
        agents = self.config.get('agents', [])
        for agent in agents:
            agent_name = agent.get('name')
            agent_prompts = agent.get('config', {}).get('prompts', {})
            if agent_name and agent_prompts:
                prompts[agent_name] = agent_prompts
        
        return prompts
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP configuration from agent.yaml"""
        return self.config.get('mcp', {})
    
    def get_prompt(self, agent_name: str, prompt_name: str, **kwargs) -> str:
        """
        Get a prompt template and format it with variables
        
        Args:
            agent_name: Name of the agent (e.g., 'chat_agent')
            prompt_name: Name of the prompt (e.g., 'system', 'intent_classification')
            **kwargs: Variables to format the prompt with
            
        Returns:
            Formatted prompt string
        """
        if agent_name not in self.prompts:
            raise ValueError(f"Agent '{agent_name}' not found in prompts")
        
        if prompt_name not in self.prompts[agent_name]:
            raise ValueError(f"Prompt '{prompt_name}' not found for agent '{agent_name}'")
        
        template = self.prompts[agent_name][prompt_name]
        
        # Format with provided variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable {e} for prompt formatting")
    
    def get_system_prompt(self, agent_name: str) -> str:
        """Get system prompt for an agent"""
        return self.get_prompt(agent_name, 'system')
    
    def get_all_prompts(self, agent_name: str) -> Dict[str, str]:
        """Get all prompts for an agent"""
        if agent_name not in self.prompts:
            raise ValueError(f"Agent '{agent_name}' not found in prompts")
        return self.prompts[agent_name]


# Singleton instance
prompt_manager = PromptManager()
