"""
FR : Test d'integration du pipeline complet. On fait tourner les cinq agents
     de bout en bout et on verifie que le rapport final est bien genere avec
     un score et des findings. C'est le test le plus important : il prouve
     que tout fonctionne ensemble.

EN : Integration test for the full pipeline. We run all five agents end to
     end and verify that the final report is properly generated with a score
     and findings. This is the most important test: it proves everything
     works together.
"""
import sys
sys.path.insert(0, "/home/claude/trustgate")

import pytest
from src.trustgate.agents.orchestrator import TrustGateOrchestrator
from src.trustgate.report.models import TrustReport


class TestFullPipeline:
    def test_pipeline_runs_and_produces_report(self):
        # FR : On desactive le MCP pour ce test (pas de sous-processus).
        # EN : We disable MCP for this test (no subprocess needed).
        orchestrator = TrustGateOrchestrator(use_mcp=False, max_rps=100.0)
        context = orchestrator.run()

        # FR : Le rapport doit etre present dans le contexte final.
        # EN : The report must be present in the final context.
        assert "trust_report" in context
        report: TrustReport = context["trust_report"]

        # FR : Le rapport doit avoir un score entre 0 et 100.
        # EN : The report must have a score between 0 and 100.
        assert 0 <= report.overall_score <= 100

        # FR : Il doit y avoir au moins un finding par pilier tete.
        # EN : There must be at least one finding per tested pillar.
        assert len(report.findings) > 0

        # FR : Le fichier JSON doit avoir ete cree.
        # EN : The JSON file must have been created.
        assert "report_path" in context

    def test_all_payloads_produce_findings(self):
        orchestrator = TrustGateOrchestrator(use_mcp=False, max_rps=100.0)
        context = orchestrator.run()
        report: TrustReport = context["trust_report"]

        # FR : Autant de findings que de cas de test.
        # EN : As many findings as there are test cases.
        from src.trustgate.security.payloads import get_all_test_cases
        assert len(report.findings) == len(get_all_test_cases())
