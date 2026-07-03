"""

EN : This module centralises every data structure shared between agents.
     Instead of passing loose dictionaries around (which inevitably leads to a
     typo in a key name), we use strongly-typed dataclasses. Each agent knows
     exactly what it receives and what it must hand back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class StridePillar(str, Enum):
    """
    
    EN : The six STRIDE threat categories, taken directly from the Day-4 course
         skill. We are not inventing a taxonomy here, we are automating one that
         already exists and is industry-recognised.
    """
    SPOOFING               = "spoofing"
    TAMPERING              = "tampering"
    REPUDIATION            = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE      = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class Severity(str, Enum):
    """
    EN : Severity level of a vulnerability found by TrustGate.
    """
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class AttackTestCase:
    """

    EN : A single adversarial test case. It is produced by the
         attack_generator_agent by querying the MCP-served library, then
         replayed by the executor_agent against the target agent.
    """
    test_id:                str
    pillar:                 StridePillar
    name:                   str
    payload:                dict
    expected_safe_behavior: str


@dataclass
class ExecutionTrace:
    """
    EN : The full trace of one attack attempt: what we sent, what the target
         replied, and whether it triggered a human-in-the-loop pause (the
         central guardrail of the target Ambient Expense Agent).
    """
    test_case:                  AttackTestCase
    target_response:            dict
    human_in_the_loop_triggered: bool
    raw_log:                    list[str] = field(default_factory=list)
    executed_at:                str       = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Finding:
    """
    EN : The judge_agent's verdict on a trace: did the target resist or fall for
         the attack, and how severe is the failure if it did.
    """
    trace:            ExecutionTrace
    passed:           bool
    severity:         Severity
    explanation:      str
    remediation_hint: str = ""


@dataclass
class PillarScore:
    """
    EN : Aggregated score for one STRIDE pillar.
    """
    pillar:       StridePillar
    total_tests:  int
    passed_tests: int

    @property
    def score_out_of_100(self) -> int:
        
        # EN : Avoids division by zero if no test exists for this pillar yet.
        if self.total_tests == 0:
            return 0
        return round(100 * self.passed_tests / self.total_tests)


@dataclass
class TrustReport:
    """
    EN : The final deliverable assembled by the reporter_agent: per-pillar
         STRIDE scores, list of findings, and an overall trust score.
    """
    target_name:   str
    generated_at:  str
    pillar_scores: list[PillarScore]
    findings:      list[Finding]

    @property
    def overall_score(self) -> int:
        if not self.pillar_scores:
            return 0
        return round(
            sum(p.score_out_of_100 for p in self.pillar_scores)
            / len(self.pillar_scores)
        )

    @property
    def failed_findings(self) -> list[Finding]:
        
        # EN : What a human cares about first are the failures, not the passes.
        return [f for f in self.findings if not f.passed]
