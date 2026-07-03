"""

EN : Base class for all TrustGate agents. It enforces a minimal contract
     (run() method) and provides a logger configured with the agent's name.
     In the course, ADK agents follow the same principle: each agent has a
     name, a clear role, and a well-defined interface.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    
    EN : All agents inherit from this class. It guarantees they all have the
         same externally visible structure, which greatly simplifies the
         orchestrator.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        
        # EN : One logger per agent makes debugging in production much easier.
        self.logger = logging.getLogger(f"trustgate.agent.{name}")

    @abstractmethod
    def run(self, context: dict) -> dict:
        """
       

        EN : Executes the agent's work and returns an enriched context.
             The "context" dictionary is the communication medium between
             agents: each one reads what it needs from it and writes its
             results back into it.
        """
        raise NotImplementedError
