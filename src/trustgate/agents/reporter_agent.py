"""

EN : The reporter agent. It collects all Findings produced by the judge_agent,
     computes the per-pillar and overall trust score, then generates a full
     report in two formats:
       - A timestamped JSON file in /reports/ (for logging and tracking).
       - A human-readable console display (for the demo and the video).
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.trustgate.agents.base_agent import BaseAgent
from src.trustgate.report.models import (
    Finding, PillarScore, StridePillar, TrustReport
)

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "reports"


def _compute_pillar_scores(findings: list[Finding]) -> list[PillarScore]:
    """
   

    EN : Computes the score out of 100 for each STRIDE pillar by counting
         the passed tests vs the total.
    """
    scores = []
    for pillar in StridePillar:
        pillar_findings = [f for f in findings if f.trace.test_case.pillar == pillar]
        total  = len(pillar_findings)
        passed = sum(1 for f in pillar_findings if f.passed)
        scores.append(PillarScore(pillar=pillar, total_tests=total, passed_tests=passed))
    return scores


def _render_console(report: TrustReport) -> None:
    """

    EN : Displays the report in the console in a readable form.
         This is what will be visible in the demonstration video.
    """
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  TRUSTGATE — RAPPORT DE CONFIANCE / TRUST REPORT")
    print(f"   Target : {report.target_name}")
    print(f"  Generated : {report.generated_at}")
    print(bar)

    print(f"\n  OVERALL SCORE : {report.overall_score}/100\n")

    print("  PER-PILLAR SCORES")
    print(f"  {' Pillar':<30} {'Score':>8}  {'Tests'}")
    print("  " + "-" * 50)
    for ps in report.pillar_scores:
        if ps.total_tests == 0:
            continue
        bar_fill = "█" * (ps.score_out_of_100 // 10)
        print(
            f"  {ps.pillar.value:<30} {ps.score_out_of_100:>6}/100  "
            f"({ps.passed_tests}/{ps.total_tests})  {bar_fill}"
        )

    failed = report.failed_findings
    print(f"\n VULNERABILITIES FOUND : {len(failed)}")
    if failed:
        print()
        for f in failed:
            print(f"  [{f.severity.value.upper()}] {f.trace.test_case.test_id} — {f.trace.test_case.name}")
            print(f"    → {f.explanation}")
            if f.remediation_hint:
                print(f"    ✔ Remediation : {f.remediation_hint}")
            print()
    else:
        print("\n   No critical vulnerability detected.\n")

    print(bar + "\n")


class ReporterAgent(BaseAgent):
    """

    EN : Assembles the final report, writes it to disk as JSON, and displays
         it in the console.
    """

    def __init__(self) -> None:
        super().__init__(name="reporter_agent")

    def run(self, context: dict) -> dict:
        findings: list[Finding] = context.get("findings", [])
        target_name: str = context.get(
            "target_profile", {}
        ).get("name", "Unknown Target")

        pillar_scores = _compute_pillar_scores(findings)
        now = datetime.now(timezone.utc).isoformat()

        report = TrustReport(
            target_name=target_name,
            generated_at=now,
            pillar_scores=pillar_scores,
            findings=findings,
        )

    
        # EN : Console display for the demo.
        _render_console(report)

    
        # EN : JSON save for logs and temporal tracking.
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"trust_report_{ts}.json"

        report_dict = {
            "target_name":   report.target_name,
            "generated_at":  report.generated_at,
            "overall_score": report.overall_score,
            "pillar_scores": [
                {
                    "pillar":       ps.pillar.value,
                    "total_tests":  ps.total_tests,
                    "passed_tests": ps.passed_tests,
                    "score":        ps.score_out_of_100,
                }
                for ps in report.pillar_scores
                if ps.total_tests > 0
            ],
            "findings": [
                {
                    "test_id":          f.trace.test_case.test_id,
                    "name":             f.trace.test_case.name,
                    "pillar":           f.trace.test_case.pillar.value,
                    "passed":           f.passed,
                    "severity":         f.severity.value,
                    "explanation":      f.explanation,
                    "remediation_hint": f.remediation_hint,
                    "executed_at":      f.trace.executed_at,
                }
                for f in report.findings
            ],
        }

        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report_dict, fh, ensure_ascii=False, indent=2)

        self.logger.info(
            " Report saved : %s", report_path
        )

        context["trust_report"] = report
        context["report_path"]  = str(report_path)
        return context
