"""

EN : The security guardrails of TrustGate itself. Yes, the tool that tests the
     security of other agents must itself be secured. This is consistent with
     the 7th "Effective Trust" pillar from the course: security is cross-cutting
     and applies to the tester as much as to what is being tested.

     This module does three things:
       1. Mask personally identifiable information (PII) before it is sent to
          an external LLM (in case GeminiLLMClient is used).
       2. Rate-limit attack execution to avoid damaging a real target.
       3. Validate the structure of a target response before handing it to
          the judge.
"""

from __future__ import annotations

import re
import time
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. PII MASKING
# ---------------------------------------------------------------------------
# EN : These patterns cover the most common forms of sensitive data.
#      They are masked before any external model call.
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"),                    "[SSN_REDACTED]"),
    (re.compile(r"\b(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"), "[PHONE_REDACTED]"),
    (re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b"),                          "[CARD_REDACTED]"),
    (re.compile(r"\b(?:Bearer|bearer|token)\s+[A-Za-z0-9\-._~+/]+=*\b"), "[TOKEN_REDACTED]"),
    (re.compile(r"(?i)(api[_\-]?key|secret|password)\s*[=:]\s*\S+"),     "[SECRET_REDACTED]"),
]


def mask_pii(text: str) -> str:
    """

    EN : Applies all masking patterns to a piece of text and returns the
         cleaned version. Call this before any external LLM submission.
    """
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class AttackRateLimiter:
    """
  
    EN : Caps the number of test cases executed per second to avoid overwhelming
         a real target (e.g., a production agent running online). This is also
         a courtesy measure: we are running a security audit, not a load test.
    """

    def __init__(self, max_per_second: float = 2.0) -> None:
       
        # EN : Two attacks per second at most by default.
        self._min_interval = 1.0 / max_per_second
        self._last_call: float = 0.0

    def throttle(self) -> None:
        """
       
        EN : Blocks execution until the minimum interval has elapsed.
        """
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()


# ---------------------------------------------------------------------------
# 3. RESPONSE VALIDATOR
# ---------------------------------------------------------------------------

def validate_target_response(response: dict) -> bool:
    """
    
    EN : Checks that a target agent response has a minimal usable structure
         before passing it to the judge_agent. This avoids missing-key errors
         later in the pipeline.
    """
    if not isinstance(response, dict):
        logger.warning("La reponse de la cible n'est pas un dictionnaire / Target response is not a dict.")
        return False
    if "status" not in response:
        logger.warning("Cle 'status' absente de la reponse / 'status' key missing from response.")
        return False
    return True
