"""

EN : TrustGate's main entry point. Launches the full pipeline end to end
     with a few command-line options. This is the script we run for the
     demonstration and for the competition video.

Usage:
    python main.py                   
    python main.py --mcp             
    python main.py --rps 1.0         
    python main.py --help
"""

from __future__ import annotations
import argparse
import logging
import sys


# EN : We ensure the src/ package is found without a pip install.
sys.path.insert(0, ".")

from src.trustgate.agents.orchestrator import TrustGateOrchestrator


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-40s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "TrustGate — Continuous adversarial red-teaming pipeline for AI agents.\n"
           
        )
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        default=False,
        help=" Load payloads via MCP server",
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=2.0,
        help=" Attack rate limit per second (default: 2)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help=" Verbose mode",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _configure_logging(args.verbose)

    logger = logging.getLogger("trustgate.main")
    logger.info("=" * 60)
    logger.info("TrustGate — Red-Teaming Pipeline")
    logger.info("=" * 60)

    orchestrator = TrustGateOrchestrator(use_mcp=args.mcp, max_rps=args.rps)
    context = orchestrator.run()

    report = context.get("trust_report")
    if report is None:
        logger.error("Pipeline produced no report.")
        return 1

    logger.info(
        " Overall score: %d/100 | Fichier / File: %s",
        report.overall_score,
        context.get("report_path", "N/A"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
