"""

EN : The agent factory. It centralises the creation of all target agents
     available in TrustGate. Adding a new agent = adding one entry in
     AGENT_REGISTRY. The rest of the code does not need to change.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable


@dataclass
class AgentProfile:
    """
    
    EN : Profile of a target agent registered in TrustGate.
    """
    key:         str    #  unique identifier
    label:       str    #  display name
    emoji:       str    # visual icon
    description: str    # short description
    color:       str    #  CSS colour for dashboard
    process_fn:  Callable[[dict], dict]  # function to call


def _load_agents() -> dict[str, AgentProfile]:
    """
   
    EN : Loads the three agents at startup. We import here (not at module
         level) to avoid circular imports.
    """
    from src.trustgate.target.vulnerable_agent import process_expense as vuln_fn
    from src.trustgate.target.basic_agent      import process_expense as basic_fn
    from src.trustgate.target.expense_agent    import process_expense as secure_fn

    profiles = [
        AgentProfile(
            key="vulnerable",
            label="Vulnerable Agent",
            emoji="🔴",
            description="No guardrails — accepts everything including injections and admin claims.",
            color="#f85149",
            process_fn=vuln_fn,
        ),
        AgentProfile(
            key="basic",
            label="Basic Agent",
            emoji="🟡",
            description="Partial protection — blocks simple injections but misses privilege escalation.",
            color="#d29922",
            process_fn=basic_fn,
        ),
        AgentProfile(
            key="secure",
            label="Secure Agent",
            emoji="🟢",
            description="Full TrustGate best practices — resists all 6 STRIDE attack categories.",
            color="#3fb950",
            process_fn=secure_fn,
        ),
    ]
    return {p.key: p for p in profiles}



# EN : Global registry — loaded once at startup.
AGENT_REGISTRY: dict[str, AgentProfile] = _load_agents()


def get_agent(key: str) -> AgentProfile:
    """
    

    EN : Returns an agent profile by its key. Raises ValueError if the
         key is unknown.
    """
    if key not in AGENT_REGISTRY:
        valid = list(AGENT_REGISTRY.keys())
        raise ValueError(f"Unknown agent key '{key}'. Valid keys: {valid}")
    return AGENT_REGISTRY[key]


def list_agents() -> list[AgentProfile]:
    """
    
    EN : Returns all available agents in display order.
    """
    order = ["vulnerable", "basic", "secure"]
    return [AGENT_REGISTRY[k] for k in order if k in AGENT_REGISTRY]
