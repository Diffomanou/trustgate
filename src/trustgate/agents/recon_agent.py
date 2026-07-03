"""

EN : The reconnaissance agent. It maps the "attack surface" of the target
     agent before launching any tests. This is the first step of the course's
     official "stride-threat-model" skill: "Analyze System Boundaries".
     In production it would read the target's CONTEXT.md and SKILL.md files
     and query the MCP server. In this repository it works with a static
     description of the Ambient Expense Agent (which we already know well).
"""

from __future__ import annotations
from src.trustgate.agents.base_agent import BaseAgent

# EN : Static description of the target agent. In production, this block
#      would be built dynamically by reading the agent's config files
#      (CONTEXT.md, SKILL.md, etc.).
TARGET_PROFILE = {
    "name": "Ambient Expense Agent",
    "description": (
        "An ADK-based expense-approval agent with human-in-the-loop triage. "
        "It auto-approves expenses below $100 and routes higher amounts to a "
        "human manager."
    ),
    "entry_points": ["process_expense"],
    "guardrails": [
        "PII masking (pre-LLM screen)",
        "Prompt-injection keyword detection",
        "Maximum input length: 10,000 characters",
        "Human-in-the-loop for amounts >= $100",
    ],
    "data_stores": ["in-memory expense log"],
    "external_dependencies": [],
    "trust_boundary": (
        "All user inputs are untrusted. Manager approvals are trusted "
        "only when they come through the internal notification channel."
    ),
}


class ReconAgent(BaseAgent):
    """


    EN : Maps the attack surface and records the target profile in the shared
         context for subsequent agents to use.
    """

    def __init__(self) -> None:
        super().__init__(name="recon_agent")

    def run(self, context: dict) -> dict:
        self.logger.info(
            
            "Analysing attack surface of '%s'",
            TARGET_PROFILE["name"],
            TARGET_PROFILE["name"],
        )

        
        # EN : We write the profile into the shared context. The attack_generator
        #      will use it to personalise payloads if needed.
        context["target_profile"] = TARGET_PROFILE

        self.logger.info(
            "Garde-fous detectes / Guardrails detected: %s",
            ", ".join(TARGET_PROFILE["guardrails"]),
        )
        return context
