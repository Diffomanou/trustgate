"""


EN : AttackGeneratorAgent — v2 with contextual generation via Gemini.
     Decision logic:
       1. If an agent role is provided AND Gemini is available
          → generates contextual STRIDE attacks (10 tailored cases)
       2. Otherwise → loads local payloads (always available)

     This design guarantees TrustGate always works, even without an
     API key, while delivering a much better experience when Gemini
     is available.
"""

from __future__ import annotations
import logging
from src.trustgate.agents.base_agent    import BaseAgent
from src.trustgate.agents.llm_client    import get_llm_client
from src.trustgate.report.models        import AttackTestCase, StridePillar
from src.trustgate.security.payloads    import get_all_test_cases

logger = logging.getLogger(__name__)


def _raw_to_test_case(raw: dict) -> AttackTestCase | None:
    """
   
    EN : Converts a raw dictionary (coming from Gemini) into a typed
         AttackTestCase. Returns None if the structure is invalid.
    """
    try:
        return AttackTestCase(
            test_id=raw["test_id"],
            pillar=StridePillar(raw["pillar"]),
            name=raw["name"],
            payload=raw["payload"],
            expected_safe_behavior=raw["expected_safe_behavior"],
        )
    except (KeyError, ValueError) as exc:
        logger.warning(" Invalid case ignored: %s", exc)
        return None


class AttackGeneratorAgent(BaseAgent):
    """
    EN : Loads or generates STRIDE test cases and places them in the
         shared context for the ExecutorAgent.
    """

    def __init__(self, use_mcp: bool = False) -> None:
        super().__init__(name="attack_generator_agent")
        self.use_mcp = use_mcp

    def run(self, context: dict) -> dict:
        agent_role: str = context.get("agent_role", "").strip()
        test_cases: list[AttackTestCase] = []
        source = "local payloads"

      
        if agent_role:
            self.logger.info(
                "Role detected: '%s' —  calling Gemini", agent_role
            )
            client = get_llm_client()
            raw_cases = client.generate_attacks(agent_role)

            if raw_cases:
                for raw in raw_cases:
                    tc = _raw_to_test_case(raw)
                    if tc:
                        test_cases.append(tc)
                source = f"Gemini contextual generation ({len(test_cases)} cases for: {agent_role[:50]})"
            else:
                self.logger.warning(
                    "Gemini returned no valid cases — falling back to local"
                )

        # ── fallback ou built-in ─────
        if not test_cases:
            test_cases = get_all_test_cases()
            source = "local STRIDE payloads (built-in)"

        context["test_cases"]    = test_cases
        context["attack_source"] = source

        self.logger.info(
            "%d test cases loaded from: %s",
            len(test_cases), len(test_cases), source
        )
        return context
