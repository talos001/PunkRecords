from typing import Dict, Type, Optional, List
from .base import BaseAgent


class AgentRegistry:
    """Registry for LLM agent backends.

    Allows dynamic registration and lookup of different agent implementations.
    """

    def __init__(self):
        self._registry: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_class: Type[BaseAgent]) -> None:
        """Register an agent backend class."""
        if not hasattr(agent_class, "name"):
            raise ValueError("Agent class must have a 'name' attribute")
        self._registry[agent_class.name] = agent_class

    def get_agent(self, name: str) -> Optional[Type[BaseAgent]]:
        """Get an agent class by name."""
        return self._registry.get(name)

    def has_agent(self, name: str) -> bool:
        """Check if an agent with given name is registered."""
        return name in self._registry

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._registry.keys())
