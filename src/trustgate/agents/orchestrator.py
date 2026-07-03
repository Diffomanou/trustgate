"""

EN : The orchestrator: TrustGate's brain. It chains the five agents in the
     correct order by passing a "context" dictionary from one to the next.
     This is exactly the "graph workflow" model described in the ADK course
     (Day 3): each graph node is an agent, and the edges are context
     transitions.

     Execution graph:
       ReconAgent
           ↓
       AttackGeneratorAgent  (loads test cases from MCP or locally)
           ↓
       ExecutorAgent          (sends attacks to the target)
           ↓
       JudgeAgent             (evaluates each trace)
           ↓
       ReporterAgent          (computes scores and produces the report)
"""

from __future__ import annotations
import logging
import time
from src.trustgate.agents.recon_agent        import ReconAgent
from src.trustgate.agents.attack_generator   import AttackGeneratorAgent
from src.trustgate.agents.executor_agent     import ExecutorAgent
from src.trustgate.agents.judge_agent        import JudgeAgent
from src.trustgate.agents.reporter_agent     import ReporterAgent

logger = logging.getLogger(__name__)


class TrustGateOrchestrator:
    """
     EN : Runs the full pipeline and returns the final context enriched by
         all agents. The context notably contains:
           - "trust_report" : the full TrustReport object.
           - "report_path"  : path to the generated JSON file.
    """

    def __init__(self, use_mcp: bool = False, max_rps: float = 2.0) -> None:
        
        # EN : We instantiate all agents once and reuse them.
        self._pipeline = [
            ReconAgent(),
            AttackGeneratorAgent(use_mcp=use_mcp),
            ExecutorAgent(max_rps=max_rps),
            JudgeAgent(),
            ReporterAgent(),
        ]

    def run(self) -> dict:
        """
        
        EN : Executes the pipeline end to end and returns the final context.
        """
        context: dict = {}
        start = time.monotonic()

        for agent in self._pipeline:
            logger.info(
                ">>> Active agent : %s", agent.name
            )
            context = agent.run(context)

        elapsed = time.monotonic() - start
        logger.info(
            "Pipeline completed in %.2fs", elapsed
        )
        context["elapsed_seconds"] = round(elapsed, 2)
        return context
