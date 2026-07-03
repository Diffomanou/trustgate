"""

EN : TrustGate's MCP server. It exposes the STRIDE test-case library as a set
     of tools callable by any ADK-compatible MCP agent. This directly addresses
     Day 2 of the course ("Agent Tools & Interoperability"): the idea is that
     another project, another team, could connect their own agent to this server
     and obtain STRIDE test cases without copying our code.

     We use FastMCP, the high-level layer of the official Python MCP SDK.
"""

from __future__ import annotations
import json
import logging
from mcp.server.fastmcp import FastMCP
from src.trustgate.security.payloads import get_all_test_cases, get_cases_for_pillar
from src.trustgate.report.models import StridePillar

logger = logging.getLogger(__name__)


# EN : We create the server instance with a human-readable name. This name
#      appears in the Antigravity UI when the server is connected.
mcp = FastMCP("TrustGate Attack Library")


@mcp.tool()
def list_all_test_cases() -> str:
    """

    EN : Returns all test cases from the STRIDE library as JSON.
         Used by the attack_generator_agent to load the full set of available
         probes.
    """
    cases = get_all_test_cases()
    result = [
        {
            "test_id":                tc.test_id,
            "pillar":                 tc.pillar.value,
            "name":                   tc.name,
            "payload":                tc.payload,
            "expected_safe_behavior": tc.expected_safe_behavior,
        }
        for tc in cases
    ]
    logger.info("MCP list_all_test_cases : %d  cases returned", len(result))
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_test_cases_for_pillar(pillar_name: str) -> str:
    """
    EN : Returns only the test cases for the requested STRIDE pillar.
         Useful when an agent wants to focus on a single threat family
         (e.g., injection / spoofing tests only).

    Args:
        pillar_name: Valeur exacte de l'enum StridePillar (ex: "spoofing").
                     Exact StridePillar enum value (e.g., "spoofing").
    """
    try:
        pillar = StridePillar(pillar_name.lower())
    except ValueError:
        valid = [p.value for p in StridePillar]
        return json.dumps(
            {"error": f"Unknown pillar '{pillar_name}'. Valid values: {valid}"},
            ensure_ascii=False,
        )

    cases = get_cases_for_pillar(pillar)
    result = [
        {
            "test_id":                tc.test_id,
            "pillar":                 tc.pillar.value,
            "name":                   tc.name,
            "payload":                tc.payload,
            "expected_safe_behavior": tc.expected_safe_behavior,
        }
        for tc in cases
    ]
    logger.info(
        "MCP list_test_cases_for_pillar('%s') : %d cas / cases", pillar_name, len(result)
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def get_stride_summary() -> str:
    """
    EN : Returns a summary of the STRIDE model: how many test cases per pillar
         are available in the library. Useful for the recon_agent.
    """
    all_cases = get_all_test_cases()
    summary = {}
    for pillar in StridePillar:
        count = sum(1 for tc in all_cases if tc.pillar == pillar)
        summary[pillar.value] = count

    logger.info("MCP get_stride_summary appelee / called")
    return json.dumps(
        {"total": len(all_cases), "by_pillar": summary},
        ensure_ascii=False,
        indent=2,
    )


def run_server() -> None:
    """
    EN : Starts the MCP server in stdio mode (standard for Antigravity
         integration and local ADK agents).
    """
    logger.info(" Starting TrustGate MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()
