"""


EN : The executor agent — version 2 with multi-target support.
     It now accepts any agent function as a target, which allows testing
     all three agents (Vulnerable / Basic / Secure) without changing
     a single line of code elsewhere in the pipeline.
"""

from __future__ import annotations
from typing import Callable
from src.trustgate.agents.base_agent import BaseAgent
from src.trustgate.report.models import AttackTestCase, ExecutionTrace
from src.trustgate.security.guardrails import AttackRateLimiter, validate_target_response
from src.trustgate.target.expense_agent import process_expense as default_process


class ExecutorAgent(BaseAgent):
    """
   

    EN : Executes test cases one by one against the chosen target agent.
         The target is injected via the constructor (Dependency Injection) —
         no hard import, no tight coupling.
    """

    def __init__(
        self,
        max_rps: float = 2.0,
        target_fn: Callable[[dict], dict] | None = None,
    ) -> None:
        super().__init__(name="executor_agent")
        self._rate_limiter = AttackRateLimiter(max_per_second=max_rps)
        
        # EN : If no target is provided, we use the Secure Agent by default.
        self._target_fn = target_fn or default_process

    def _execute_one(self, test_case: AttackTestCase) -> ExecutionTrace:
        self._rate_limiter.throttle()

        log: list[str] = []
        log.append(f"[SEND] {test_case.test_id} — {test_case.name}")
        log.append(f"[PAYLOAD] {test_case.payload}")

        
        # EN : Call to the injected target function — regardless of which agent it is.
        response = self._target_fn(test_case.payload)
        log.append(f"[RESPONSE] {response}")

        if not validate_target_response(response):
            response = {"status": "invalid_response", "message": "Unstructured response"}
            log.append("[WARN] Invalid response normalised")

        human_triggered = response.get("human_review_required", False) is True

        return ExecutionTrace(
            test_case=test_case,
            target_response=response,
            human_in_the_loop_triggered=human_triggered,
            raw_log=log,
        )

    def run(self, context: dict) -> dict:
        
        # EN : If the context contains a custom target function, we use it.
        if "target_fn" in context:
            self._target_fn = context["target_fn"]

        test_cases: list[AttackTestCase] = context.get("test_cases", [])
        if not test_cases:
            self.logger.warning("No test cases in context")
            context["execution_traces"] = []
            return context

        traces: list[ExecutionTrace] = []
        for tc in test_cases:
            self.logger.info("Executing: %s (%s)", tc.test_id, tc.pillar.value)
            traces.append(self._execute_one(tc))

        context["execution_traces"] = traces
        self.logger.info("%d traces captured", len(traces))
        return context
