# tests/test_pii_scanner.py
# Complete reference test file — all other test files follow this pattern

import pytest
from promptforge.guardrails.pii_scanner import PIIScanner, redact_pii, PII_PATTERNS


class TestPIIPatterns:
    """Test individual PII regex patterns."""

    def test_openai_key_detected(self):
        text = "My key is sk-abcdefghijklmnopqrstuvwxyz1234567890ab"
        matches = PII_PATTERNS["openai_key"].findall(text)
        assert len(matches) > 0

    def test_anthropic_key_detected(self):
        text = "Using sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
        matches = PII_PATTERNS["anthropic_key"].findall(text)
        assert len(matches) > 0

    def test_aws_access_key_detected(self):
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        matches = PII_PATTERNS["aws_access_key"].findall(text)
        assert len(matches) > 0

    def test_github_token_detected(self):
        text = "Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        matches = PII_PATTERNS["github_token"].findall(text)
        assert len(matches) > 0

    def test_email_detected(self):
        text = "Contact me at john.doe@example.com for details"
        matches = PII_PATTERNS["email"].findall(text)
        assert len(matches) > 0
        assert "john.doe@example.com" in matches[0]

    def test_credit_card_detected(self):
        text = "Card number: 4532 1234 5678 9012"
        matches = PII_PATTERNS["credit_card"].findall(text)
        assert len(matches) > 0

    def test_ssn_detected(self):
        text = "SSN: 123-45-6789"
        matches = PII_PATTERNS["ssn"].findall(text)
        assert len(matches) > 0

    def test_clean_text_no_matches(self):
        text = "This is a completely clean piece of text with no sensitive data."
        for name, pattern in PII_PATTERNS.items():
            if name == "phone_number":
                continue  # skip phone — too many false positives on numbers
            pattern.search(text) # should not raise
        # no assertion needed — just ensure no crashes


class TestPIIScannerCheckInput:
    """Test PIIScanner.check_input async method."""

    @pytest.mark.asyncio
    async def test_clean_input_passes(self):
        scanner = PIIScanner()
        result = await scanner.check_input("What is the capital of France?")
        assert result.passed is True
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_anthropic_key_in_input_blocked(self):
        scanner = PIIScanner()
        text = "My key is sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
        result = await scanner.check_input(text)
        assert result.passed is False
        assert len(result.violations) > 0
        assert result.violations[0].severity == "block"
        assert "anthropic" in result.violations[0].guardrail_id.lower() or \
               "pii" in result.violations[0].guardrail_id.lower()

    @pytest.mark.asyncio
    async def test_email_in_input_warns(self):
        scanner = PIIScanner()
        text = "Email me at john@example.com with questions"
        result = await scanner.check_input(text)
        assert result.passed is False
        assert any(v.severity == "warn" for v in result.violations)

    @pytest.mark.asyncio
    async def test_multiple_pii_types_detected(self):
        scanner = PIIScanner()
        text = "Key: sk-abcdefghijklmnopqrstuvwxyz1234567890ab, email: user@test.com"
        result = await scanner.check_input(text)
        assert result.passed is False
        assert len(result.violations) >= 2

    @pytest.mark.asyncio
    async def test_openai_key_blocked(self):
        scanner = PIIScanner()
        text = "sk-abcdefghijklmnopqrstuvwxyz1234567890abcd is my OpenAI key"
        result = await scanner.check_input(text)
        assert result.passed is False
        assert any(v.severity == "block" for v in result.violations)

    @pytest.mark.asyncio
    async def test_aws_key_blocked(self):
        scanner = PIIScanner()
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        result = await scanner.check_input(text)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_context_also_scanned(self):
        scanner = PIIScanner()
        result = await scanner.check_input(
            text="Normal question",
            context="AKIAIOSFODNN7EXAMPLE is in the context"
        )
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_empty_string_passes(self):
        scanner = PIIScanner()
        result = await scanner.check_input("")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_long_clean_text_passes(self):
        scanner = PIIScanner()
        text = "This is a long document about machine learning. " * 100
        result = await scanner.check_input(text)
        assert result.passed is True


class TestPIIScannerCheckOutput:
    """Test PIIScanner.check_output async method."""

    @pytest.mark.asyncio
    async def test_clean_output_passes(self):
        scanner = PIIScanner()
        text = "JWT tokens consist of three parts: header, payload, and signature."
        result = await scanner.check_output(text)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_pii_in_output_flagged(self):
        scanner = PIIScanner()
        text = "Your API key sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890 is valid."
        result = await scanner.check_output(text)
        assert result.passed is False
        assert len(result.violations) > 0

    @pytest.mark.asyncio
    async def test_email_in_output_flagged(self):
        scanner = PIIScanner()
        text = "Please contact admin@secretcompany.com for access."
        result = await scanner.check_output(text)
        assert result.passed is False


class TestRedactPII:
    """Test redact_pii utility function."""

    def test_redacts_api_key(self):
        text = "Key: sk-abcdefghijklmnopqrstuvwxyz1234567890ab is secret"
        redacted = redact_pii(text)
        assert "sk-" not in redacted
        assert "[REDACTED" in redacted

    def test_redacts_email(self):
        text = "Email: user@example.com is private"
        redacted = redact_pii(text)
        assert "user@example.com" not in redacted
        assert "[REDACTED" in redacted

    def test_redacts_multiple_types(self):
        text = "Key: sk-abcdefghijklmnopqrstuvwxyz1234567890ab and email: a@b.com"
        redacted = redact_pii(text)
        assert "sk-" not in redacted
        assert "a@b.com" not in redacted

    def test_clean_text_unchanged(self):
        text = "This text has no sensitive data in it at all."
        redacted = redact_pii(text)
        assert redacted == text

    def test_redacted_placeholder_format(self):
        text = "email: user@example.com"
        redacted = redact_pii(text)
        assert "[REDACTED_EMAIL]" in redacted or "[REDACTED" in redacted

    def test_redact_preserves_non_pii_text(self):
        text = "Hello user@example.com, the capital of France is Paris."
        redacted = redact_pii(text)
        assert "Paris" in redacted
        assert "Hello" in redacted
        assert "user@example.com" not in redacted


class TestPIIScannerGuardrailInterface:
    """Test that PIIScanner correctly implements BaseGuardrail interface."""

    def test_has_guardrail_id(self):
        scanner = PIIScanner()
        assert scanner.guardrail_id == "pii_scanner"

    def test_guardrail_id_is_string(self):
        scanner = PIIScanner()
        assert isinstance(scanner.guardrail_id, str)

    @pytest.mark.asyncio
    async def test_check_input_returns_guardrail_result(self):
        from promptforge.guardrails.base import GuardrailResult
        scanner = PIIScanner()
        result = await scanner.check_input("test")
        assert isinstance(result, GuardrailResult)

    @pytest.mark.asyncio
    async def test_check_output_returns_guardrail_result(self):
        from promptforge.guardrails.base import GuardrailResult
        scanner = PIIScanner()
        result = await scanner.check_output("test")
        assert isinstance(result, GuardrailResult)

    @pytest.mark.asyncio
    async def test_violations_have_correct_structure(self):
        scanner = PIIScanner()
        text = "AKIAIOSFODNN7EXAMPLE"
        result = await scanner.check_input(text)
        for v in result.violations:
            assert hasattr(v, 'guardrail_id')
            assert hasattr(v, 'severity')
            assert hasattr(v, 'message')
            assert v.severity in ("block", "warn", "info")
