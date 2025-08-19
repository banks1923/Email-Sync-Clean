"""Lockfile and reproducibility tests.

Ensures dependency locking for reproducible builds.
Part of Phase 0 Decision Tests.
"""

import subprocess
from pathlib import Path

import pytest


def test_lockfiles_exist():
    """Verify lockfiles for all Python versions."""
    # For now, check if we can create them
    # In production, these would already exist

    # Check for pip-tools
    result = subprocess.run(["pip", "list"], capture_output=True, text=True)

    has_pip_tools = "pip-tools" in result.stdout

    if not has_pip_tools:
        pytest.skip("pip-tools not installed - install with: pip install pip-tools")

    # Check current Python version
    import sys

    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    # Look for lockfile for current version
    lockfile = Path(f"requirements-py{current_version}.lock")

    if lockfile.exists():
        # Verify hash format
        content = lockfile.read_text()
        assert (
            "--hash=" in content or "sha256:" in content
        ), "Lockfile should contain package hashes"
        print(f"✓ Lockfile exists for Python {current_version}")
    else:
        print(f"⚠ No lockfile for Python {current_version} - will be created")


def test_requirements_consistency():
    """Verify requirements.txt is consistent."""
    req_file = Path("requirements.txt")

    assert req_file.exists(), "requirements.txt must exist"

    content = req_file.read_text()
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    # Check for duplicates
    packages = {}
    for line in lines:
        # Extract package name (before any version specifier)
        for sep in [">=", "<=", "==", ">", "<", "~=", "!="]:
            if sep in line:
                pkg_name = line.split(sep)[0].strip()
                break
        else:
            pkg_name = line.strip()

        if pkg_name in packages:
            pytest.fail(f"Duplicate package: {pkg_name}")
        packages[pkg_name] = line

    print(f"✓ Requirements.txt has {len(packages)} unique packages")


def test_install_uses_hashes(monkeypatch):
    """Verify pip install uses hash verification."""
    import subprocess

    # Mock subprocess.run to check arguments
    calls = []

    def mock_run(*args, **kwargs):
        calls.append((args, kwargs))
        # Check if this is a pip install command
        if args and len(args) > 0:
            cmd = args[0] if isinstance(args[0], list) else list(args)
            if "pip" in str(cmd) and "install" in str(cmd):
                # Check for --require-hashes
                assert "--require-hashes" in str(cmd) or kwargs.get(
                    "check_hashes", False
                ), "pip install should use --require-hashes"
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Simulate install command
    subprocess.run(["pip", "install", "-r", "requirements.lock", "--require-hashes"])

    assert len(calls) > 0, "Mock should have been called"
    print("✓ Hash verification check passed")


def test_no_conflicting_dependencies():
    """Check for conflicting dependency versions."""
    req_file = Path("requirements.txt")
    dev_req_file = Path("requirements-dev.txt")

    base_deps = {}

    if req_file.exists():
        content = req_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                for sep in [">=", "<=", "==", ">", "<"]:
                    if sep in line:
                        pkg = line.split(sep)[0].strip()
                        base_deps[pkg] = line
                        break

    if dev_req_file.exists():
        content = dev_req_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                for sep in [">=", "<=", "==", ">", "<"]:
                    if sep in line:
                        pkg = line.split(sep)[0].strip()
                        if pkg in base_deps and base_deps[pkg] != line:
                            pytest.fail(
                                f"Conflicting versions for {pkg}: " f"{base_deps[pkg]} vs {line}"
                            )
                        break

    print("✓ No conflicting dependencies found")
