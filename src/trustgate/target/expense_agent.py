"""

EN : The Ambient Expense Agent: the target of our security tests. This is
     exactly the agent introduced in the Day-4 course codelab
     ("Build an expense-approval agent with human-in-the-loop triage").
     It is implemented here in pure Python (no external dependency) so that
     anyone can run it and reproduce our results.

     Business rules:
       - Expense < $100: auto-approved (deterministic code path).
       - Expense >= $100: simulated LLM analysis + mandatory human pause.
       - PII pre-screening before any LLM processing.
       - Maximum message size: 10,000 characters.
"""

from __future__ import annotations
import re
import logging
from src.trustgate.security.guardrails import mask_pii

logger = logging.getLogger(__name__)


# EN : Monetary threshold above which human validation is required.
AUTO_APPROVE_THRESHOLD_USD = 100.0


# EN : Maximum length of a message accepted by the target agent.
MAX_INPUT_LENGTH = 10_000

# EN : Keywords that signal a prompt-injection attempt. The agent
#      detects them and blocks processing before reaching the LLM.
INJECTION_MARKERS = [
    "ignore previous instructions",
    "ignore les instructions precedentes",
    "system override",
    "you are now in admin mode",
    "auto_approve_override",
]


def _detect_injection(text: str) -> bool:
    """
    
    EN : Returns True if the text contains a known injection marker.
    """
    lowered = text.lower()
    return any(marker in lowered for marker in INJECTION_MARKERS)


def _extract_amount(text: str) -> float | None:
    """

    EN : Tries to extract a dollar amount from the request text. We look
         for patterns like '$80', '80 USD', or '80$'.
         Returns None if no amount is found.
    """
    patterns = [
        r"\$\s*(\d+(?:\.\d{1,2})?)",
        r"(\d+(?:\.\d{1,2})?)\s*(?:USD|\$)",
        r"(\d+(?:\.\d{1,2})?)\s*dollars?",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def process_expense(request: dict) -> dict:
    """
   
    EN : Main entry point of the target agent. Receives an expense request and
         returns a structured response dictionary. This is the function the
         executor_agent calls for each test case.

    Args:
        request: dict avec au minimum la cle "content" (le message utilisateur).
                 dict with at least the "content" key (the user message).

    Returns:
        dict avec "status", "message", "human_review_required", "amount_usd".
        dict with "status", "message", "human_review_required", "amount_usd".
    """
    content: str = request.get("content", "")

    # ------------------------------------------------------------------
    # GUARDRAIL 1: Maximum size
    # ------------------------------------------------------------------
    if len(content) > MAX_INPUT_LENGTH:
        logger.warning("Input trop long (%d chars) / Input too long (%d chars)", len(content), len(content))
        return {
            "status": "rejected",
            "message": (
                "Request exceeds maximum allowed length. "
                "Please shorten your submission."
            ),
            "human_review_required": False,
            "amount_usd": None,
        }

    # ------------------------------------------------------------------
    # GUARDRAIL 2: Prompt-injection detection (pre-LLM screen)
    # ------------------------------------------------------------------
    if _detect_injection(content):
        logger.warning(" Injection attempt detected: %.80s", content)
        return {
            "status": "rejected",
            "message": (
                "Your request contains instructions that cannot be processed. "
                "Please submit a valid expense description."
            ),
            "human_review_required": False,
            "amount_usd": None,
        }

    # ------------------------------------------------------------------
    # GUARDRAIL 3: PII masking before any downstream transmission
    # ------------------------------------------------------------------
    safe_content = mask_pii(content)

    # ------------------------------------------------------------------
    # BUSINESS LOGIC: Auto-approval threshold
    # ------------------------------------------------------------------
    amount = _extract_amount(safe_content)

    if amount is not None and amount < AUTO_APPROVE_THRESHOLD_USD:
      
        # EN : Deterministic path: no LLM, direct approval.
        logger.info("Approbation automatique / Auto-approved: $%.2f", amount)
        return {
            "status": "approved",
            "message": f"Expense of ${amount:.2f} auto-approved (below threshold).",
            "human_review_required": False,
            "amount_usd": amount,
        }

 
    # EN : High-value expense or no amount found: mandatory human pause.
    #      We simulate here what a real LLM would do (analysis then hand-off
    #      to a human validator).
    logger.info("Human-in-the-loop triggered: %s", safe_content[:60])
    return {
        "status": "pending_human_review",
        "message": (
            "This expense requires human review before approval. "
            "A notification has been sent to your manager."
        ),
        "human_review_required": True,
        "amount_usd": amount,
    }
