# tests/test_config.py
"""Tests for promptforge.config.Settings."""

import pytest

from promptforge.config import Settings, get_settings


class TestSettingsDefaults:
    """Verify default field values match the specification."""

    def test_app_defaults(self) -> None:
        """Default app settings should match PromptForge spec."""
        settings = Settings()
        assert settings.app_name == "PromptForge"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000

    def test_provider_defaults(self) -> None:
        """Optional provider keys default to None; Ollama has sensible defaults."""
        settings = Settings()
        assert settings.anthropic_api_key is None
        assert settings.openai_api_key is None
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_default_model == "llama3.2"
        assert settings.custom_endpoint_url is None
        assert settings.custom_endpoint_key is None
        assert settings.custom_endpoint_model is None

    def test_guardrail_defaults(self) -> None:
        """Guardrail toggles and token limit use spec defaults."""
        settings = Settings()
        assert settings.default_token_limit == 4000
        assert settings.enable_pii_scan is True
        assert settings.enable_injection_guard is True
        assert settings.enable_hallucination_guard is True

    def test_storage_defaults(self) -> None:
        """Storage path defaults to ./prompts; GitHub token is optional."""
        settings = Settings()
        assert settings.local_storage_path == "./prompts"
        assert settings.github_token is None


class TestSettingsConstructor:
    """Test explicit constructor overrides."""

    def test_custom_values(self) -> None:
        """Constructor kwargs override defaults."""
        settings = Settings(
            app_name="CustomForge",
            debug=True,
            port=9000,
            anthropic_api_key="sk-ant-custom",
        )
        assert settings.app_name == "CustomForge"
        assert settings.debug is True
        assert settings.port == 9000
        assert settings.anthropic_api_key == "sk-ant-custom"


class TestSettingsFromEnv:
    """Test environment variable loading."""

    def test_anthropic_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ANTHROPIC_API_KEY env var maps to anthropic_api_key field."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
        settings = Settings()
        assert settings.anthropic_api_key == "sk-ant-from-env"

    def test_debug_bool_coercion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DEBUG=true should coerce to boolean True."""
        monkeypatch.setenv("DEBUG", "true")
        settings = Settings()
        assert settings.debug is True

    def test_port_int_coercion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PORT env var should coerce to integer."""
        monkeypatch.setenv("PORT", "3000")
        settings = Settings()
        assert settings.port == 3000

    def test_ollama_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OLLAMA_BASE_URL env var loads correctly."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
        settings = Settings()
        assert settings.ollama_base_url == "http://ollama:11434"


class TestSettingsFromEnvFile:
    """Test loading settings from a .env file."""

    def test_env_file_loading(self, tmp_path) -> None:
        """Settings loads values from a .env file on disk."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ANTHROPIC_API_KEY=sk-ant-file-key\n"
            "DEBUG=true\n"
            "LOCAL_STORAGE_PATH=/data/prompts\n"
        )
        settings = Settings(
            _env_file=str(env_file),
        )
        assert settings.anthropic_api_key == "sk-ant-file-key"
        assert settings.debug is True
        assert settings.local_storage_path == "/data/prompts"


class TestGetSettings:
    """Test cached settings singleton."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """get_settings returns a Settings instance."""
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """Repeated calls return the same cached object."""
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
        assert first is second
