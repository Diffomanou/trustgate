"""
FR : Tests unitaires pour les garde-fous de securite. On verifie que le
     masquage PII fonctionne correctement et que le rate limiter respecte
     bien la limite configuree.

EN : Unit tests for the security guardrails. We verify that PII masking
     works correctly and that the rate limiter honours its configured limit.
"""
import sys
sys.path.insert(0, "/home/claude/trustgate")

import time
import pytest
from src.trustgate.security.guardrails import mask_pii, AttackRateLimiter, validate_target_response


class TestMaskPii:
    def test_masks_email(self):
        result = mask_pii("Contact me at alice@example.com please.")
        assert "[EMAIL_REDACTED]" in result
        assert "alice@example.com" not in result

    def test_masks_api_key(self):
        result = mask_pii("api_key=sk-abc123XYZ")
        assert "[SECRET_REDACTED]" in result
        assert "sk-abc123XYZ" not in result

    def test_leaves_safe_text_intact(self):
        text = "Please approve my $50 lunch expense."
        assert mask_pii(text) == text

    def test_masks_token(self):
        result = mask_pii("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig")
        assert "[TOKEN_REDACTED]" in result


class TestRateLimiter:
    def test_respects_interval(self):
        limiter = AttackRateLimiter(max_per_second=5.0)
        start = time.monotonic()
        for _ in range(3):
            limiter.throttle()
        elapsed = time.monotonic() - start
        # FR : 3 appels a 5/s = min 0.4s entre eux = au moins 0.4s au total.
        # EN : 3 calls at 5/s = min 0.4s between them = at least 0.4s total.
        assert elapsed >= 0.4


class TestValidateTargetResponse:
    def test_valid_response(self):
        assert validate_target_response({"status": "approved", "message": "ok"}) is True

    def test_missing_status(self):
        assert validate_target_response({"message": "ok"}) is False

    def test_not_a_dict(self):
        assert validate_target_response("not a dict") is False
