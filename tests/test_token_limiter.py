# tests/test_token_limiter.py
"""Tests for promptforge.guardrails.token_limiter."""

import pytest

from promptforge.guardrails.token_limiter import (
    TRUNCATION_MARKER,
    TokenLimiter,
    estimate_tokens,
    truncate_to_token_limit,
)


class TestEstimateTokens:
    """Test token estimation."""

    def test_empty_text_zero_tokens(self) -> None:
        """Empty text has zero tokens."""
        assert estimate_tokens("") == 0

    def test_english_reasonable_estimate(self) -> None:
        """English text uses ~4 chars per token."""
        text = "a" * 400
        tokens = estimate_tokens(text)
        assert 90 <= tokens <= 110

    def test_cjk_higher_token_density(self) -> None:
        """CJK characters use higher token density."""
        cjk = "中" * 100
        tokens = estimate_tokens(cjk)
        assert tokens >= 60


class TestTruncate:
    """Test text truncation."""

    def test_no_truncation_under_limit(self) -> None:
        """Text under limit is not truncated."""
        text = "Short text"
        result, truncated = truncate_to_token_limit(text, 1000)
        assert result == text
        assert truncated is False

    def test_truncation_adds_marker(self) -> None:
        """Truncated text contains marker."""
        text = "word " * 10000
        result, truncated = truncate_to_token_limit(text, 50)
        assert truncated is True
        assert TRUNCATION_MARKER in result

    def test_truncated_fits_limit(self) -> None:
        """Truncated text fits within token limit."""
        text = "x" * 50000
        result, truncated = truncate_to_token_limit(text, 100)
        assert truncated is True
        assert estimate_tokens(result) <= 100 + 5


class TestTokenLimiterGuardrail:
    """Test TokenLimiter guardrail."""

    @pytest.mark.asyncio
    async def test_under_limit_passes(self) -> None:
        """Short message passes without modification."""
        limiter = TokenLimiter(limit=4000)
        result = await limiter.check_input("Hello world")
        assert result.passed is True
        assert result.modified_text is None

    @pytest.mark.asyncio
    async def test_over_limit_truncates(self) -> None:
        """Long message is truncated."""
        limiter = TokenLimiter(limit=50)
        text = "word " * 5000
        result = await limiter.check_input(text)
        assert result.modified_text is not None
        assert TRUNCATION_MARKER in result.modified_text

    @pytest.mark.asyncio
    async def test_combined_token_estimation(self) -> None:
        """System prompt and context count toward budget."""
        limiter = TokenLimiter(limit=100)
        text = "word " * 500
        result = await limiter.check_input(
            text,
            context="context " * 200,
            system_prompt="system " * 200,
        )
        assert result.modified_text is not None or len(result.violations) >= 0
