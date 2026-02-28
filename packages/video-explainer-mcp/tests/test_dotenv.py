"""Tests for dotenv loader."""

from __future__ import annotations

import os

import pytest

from video_explainer_mcp.dotenv import (
    _is_unset_or_placeholder,
    load_dotenv,
    parse_dotenv,
)

pytestmark = pytest.mark.unit


class TestIsUnsetOrPlaceholder:
    """Tests for placeholder detection."""

    def test_none_is_unset(self):
        assert _is_unset_or_placeholder("KEY", None) is True

    def test_empty_string_is_unset(self):
        assert _is_unset_or_placeholder("KEY", "") is True

    def test_whitespace_is_unset(self):
        assert _is_unset_or_placeholder("KEY", "   ") is True

    def test_quoted_empty_is_unset(self):
        assert _is_unset_or_placeholder("KEY", '""') is True
        assert _is_unset_or_placeholder("KEY", "''") is True

    def test_self_reference_dollar(self):
        assert _is_unset_or_placeholder("KEY", "$KEY") is True

    def test_self_reference_braces(self):
        assert _is_unset_or_placeholder("KEY", "${KEY}") is True

    def test_self_reference_with_default(self):
        assert _is_unset_or_placeholder("KEY", "${KEY:-default}") is True

    def test_actual_value_is_not_unset(self):
        assert _is_unset_or_placeholder("KEY", "real-value") is False

    def test_different_var_reference_is_not_unset(self):
        assert _is_unset_or_placeholder("KEY", "${OTHER}") is False


class TestParseDotenv:
    """Tests for .env file parsing."""

    def test_basic_key_value(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        result = parse_dotenv(env_file)
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_comments_and_blanks(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nFOO=bar\n")
        result = parse_dotenv(env_file)
        assert result == {"FOO": "bar"}

    def test_export_prefix(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("export FOO=bar\n")
        result = parse_dotenv(env_file)
        assert result == {"FOO": "bar"}

    def test_quoted_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text('FOO="bar baz"\nQUX=\'hello\'\n')
        result = parse_dotenv(env_file)
        assert result["FOO"] == "bar baz"
        assert result["QUX"] == "hello"

    def test_missing_file(self, tmp_path):
        result = parse_dotenv(tmp_path / "nonexistent.env")
        assert result == {}

    def test_lines_without_equals(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("NOEQUALS\nFOO=bar\n")
        result = parse_dotenv(env_file)
        assert result == {"FOO": "bar"}


class TestLoadDotenv:
    """Tests for load_dotenv env injection."""

    def test_injects_missing_vars(self, tmp_path, monkeypatch):
        """Injects vars not present in os.environ."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_DOTENV_VAR=injected\n")
        monkeypatch.delenv("TEST_DOTENV_VAR", raising=False)
        injected = load_dotenv(env_file)
        assert injected == {"TEST_DOTENV_VAR": "injected"}
        assert os.environ["TEST_DOTENV_VAR"] == "injected"

    def test_does_not_override_existing(self, tmp_path, monkeypatch):
        """Process env vars take precedence."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_DOTENV_VAR=from-file\n")
        monkeypatch.setenv("TEST_DOTENV_VAR", "from-env")
        injected = load_dotenv(env_file)
        assert "TEST_DOTENV_VAR" not in injected
        assert os.environ["TEST_DOTENV_VAR"] == "from-env"

    def test_overrides_placeholder(self, tmp_path, monkeypatch):
        """Overrides unresolved placeholder values."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_DOTENV_VAR=real-value\n")
        monkeypatch.setenv("TEST_DOTENV_VAR", "${TEST_DOTENV_VAR}")
        injected = load_dotenv(env_file)
        assert injected == {"TEST_DOTENV_VAR": "real-value"}
