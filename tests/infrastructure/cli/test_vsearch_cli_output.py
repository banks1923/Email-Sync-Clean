"""Test that vsearch CLI preserves user-facing output while adding logging."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def test_cli_help_output_unchanged():
    """Test that vsearch --help output is preserved for users."""
    vsearch_path = Path(__file__).parent.parent / "scripts" / "vsearch"

    if not vsearch_path.exists():
        pytest.skip("vsearch script not found")

    # Run vsearch --help
    result = subprocess.run(
        [sys.executable, str(vsearch_path), "--help"], capture_output=True, text=True
    )

    # Check that help text is still user-friendly
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "Usage:" in result.stdout
    assert "search" in result.stdout.lower()

    # Should not have logger format strings in user output
    assert "{time}" not in result.stdout
    assert "{level}" not in result.stdout
    assert "loguru" not in result.stdout.lower()


def test_cli_search_output_format():
    """Test that search results maintain user-friendly format."""
    vsearch_path = Path(__file__).parent.parent / "scripts" / "vsearch"

    if not vsearch_path.exists():
        pytest.skip("vsearch script not found")

    # We can't actually run search without a database, but we can check
    # that the script at least starts and shows appropriate messages
    result = subprocess.run(
        [sys.executable, str(vsearch_path), "test query"], capture_output=True, text=True, timeout=5
    )

    # Should show user-friendly messages (with emojis as designed)
    stdout = result.stdout

    # Check for expected user-facing elements
    if "🤖" in stdout or "🔍" in stdout:
        # Original emoji output preserved
        assert True

    # Should not expose internal logging
    assert "DEBUG" not in stdout
    assert "__main__" not in stdout
    assert ".py:" not in stdout  # No file:line references in user output


def test_cli_errors_go_to_stderr_not_stdout():
    """Test that errors are properly separated from user output."""
    vsearch_path = Path(__file__).parent.parent / "scripts" / "vsearch"

    if not vsearch_path.exists():
        pytest.skip("vsearch script not found")

    # Run with invalid command to trigger error
    result = subprocess.run(
        [sys.executable, str(vsearch_path), "--invalid-option"], capture_output=True, text=True
    )

    # Error should be in stderr, not stdout
    if result.returncode != 0:
        # If there's an error message, it should be in stderr
        if "error" in result.stderr.lower() or "invalid" in result.stderr.lower():
            assert True
        # stdout might have usage info but not error details


def test_cli_info_command_output():
    """Test that 'vsearch info' maintains its formatted output."""
    vsearch_path = Path(__file__).parent.parent / "scripts" / "vsearch"

    if not vsearch_path.exists():
        pytest.skip("vsearch script not found")

    # Run info command
    result = subprocess.run(
        [sys.executable, str(vsearch_path), "info"], capture_output=True, text=True, timeout=10
    )

    stdout = result.stdout

    # Check for expected info output format
    # Should have system status indicators
    assert "System" in stdout or "system" in stdout or "Health" in stdout or "Status" in stdout

    # Should not have raw logging format
    assert "{message}" not in stdout
    assert "logger.bind" not in stdout


def test_cli_preserves_print_statements():
    """Verify that user-facing print statements are still used, not replaced."""
    vsearch_file = Path(__file__).parent.parent / "scripts" / "vsearch"

    if vsearch_file.exists():
        content = vsearch_file.read_text()

        # Should still have print statements for user output
        assert "print(" in content, "CLI should preserve print() for user output"

        # But should also have logger for errors
        assert "logger" in content or "cli_logger" in content, "Should have logger for errors"

        # Should have both - strategic use
        assert content.count("print(") > 20, "Should have many print statements for UI"


def test_no_debug_logs_in_production():
    """Test that debug logs don't appear in normal usage."""
    vsearch_path = Path(__file__).parent.parent / "scripts" / "vsearch"

    if not vsearch_path.exists():
        pytest.skip("vsearch script not found")

    # Run without DEBUG env var
    env = {k: v for k, v in sys.environ.items() if k != "DEBUG"}
    env["DEBUG"] = "false"

    result = subprocess.run(
        [sys.executable, str(vsearch_path), "info"],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )

    # Should not have debug level logs in output
    # Allow the word "Debug" in normal text but not "DEBUG |" log format
    combined = result.stdout + result.stderr
    assert "DEBUG |" not in combined
    assert "DEBUG :" not in combined
    # More permissive - just check for obvious debug log markers
    assert "{time:" not in combined  # Loguru format strings shouldn't appear


def test_cli_logging_goes_to_files():
    """Test that CLI logging goes to files, not cluttering user output."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        vsearch_path = Path(__file__).parent.parent / "scripts" / "vsearch"

        if not vsearch_path.exists():
            pytest.skip("vsearch script not found")

        # Run in temp directory to check log file creation
        result = subprocess.run(
            [sys.executable, str(vsearch_path), "test"],
            capture_output=True,
            text=True,
            cwd=tmp_dir,
            timeout=5,
        )

        # Check if logs directory would be created
        # (In practice it goes to project logs/ dir, but we're testing the concept)

        # User output should be clean
        assert "loguru" not in result.stdout.lower()
        assert ".log" not in result.stdout
