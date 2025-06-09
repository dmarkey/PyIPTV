#!/usr/bin/env python3
"""
Development utility script for PyIPTV.

This script provides common development tasks like running tests,
formatting code, type checking, and more.
"""
import argparse
import subprocess
import sys
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list, description: str = None) -> int:
    """Run a command and return its exit code."""
    if description:
        print(f"🔄 {description}")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print(f"✅ Success")
    else:
        print(f"❌ Failed with exit code {result.returncode}")

    return result.returncode


def install_deps():
    """Install development dependencies."""
    return run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Installing development dependencies",
    )


def format_code():
    """Format code with black and isort."""
    exit_code = 0

    exit_code |= run_command(
        [sys.executable, "-m", "black", "pyiptv/", "tests/", "scripts/"],
        "Formatting code with black",
    )

    exit_code |= run_command(
        [sys.executable, "-m", "isort", "pyiptv/", "tests/", "scripts/"],
        "Sorting imports with isort",
    )

    return exit_code


def lint_code():
    """Lint code with flake8."""
    return run_command(
        [sys.executable, "-m", "flake8", "pyiptv/", "tests/"],
        "Linting code with flake8",
    )


def type_check():
    """Type check code with mypy."""
    return run_command(
        [sys.executable, "-m", "mypy", "pyiptv/", "--ignore-missing-imports"],
        "Type checking with mypy",
    )


def run_tests(args=None):
    """Run tests with pytest."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]

    if args:
        if args.coverage:
            cmd.extend(
                ["--cov=pyiptv", "--cov-report=html", "--cov-report=term-missing"]
            )
        if args.unit:
            cmd.extend(["-m", "unit"])
        if args.integration:
            cmd.extend(["-m", "integration"])
        if args.ui:
            cmd.extend(["-m", "ui"])
        if args.slow:
            cmd.extend(["-m", "slow"])
        elif not any([args.unit, args.integration, args.ui]):
            cmd.extend(["-m", "not slow"])  # Skip slow tests by default

    return run_command(cmd, "Running tests")


def security_check():
    """Run security checks with bandit."""
    return run_command(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "pyiptv/",
            "-f",
            "json",
            "-o",
            "bandit-report.json",
        ],
        "Running security checks with bandit",
    )


def build_package():
    """Build the package."""
    return run_command([sys.executable, "-m", "build"], "Building package")


def clean():
    """Clean build artifacts and cache files."""
    import shutil

    patterns = [
        "build/",
        "dist/",
        "*.egg-info/",
        "__pycache__/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        ".mypy_cache/",
        "bandit-report.json",
    ]

    for pattern in patterns:
        for path in PROJECT_ROOT.rglob(pattern):
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"Removed directory: {path}")
                else:
                    path.unlink()
                    print(f"Removed file: {path}")


def setup_pre_commit():
    """Set up pre-commit hooks."""
    exit_code = run_command(
        [sys.executable, "-m", "pip", "install", "pre-commit"], "Installing pre-commit"
    )

    if exit_code == 0:
        exit_code = run_command(
            ["pre-commit", "install"], "Installing pre-commit hooks"
        )

    return exit_code


def check_all():
    """Run all checks (format, lint, type check, test)."""
    exit_code = 0

    exit_code |= format_code()
    exit_code |= lint_code()
    exit_code |= type_check()
    exit_code |= run_tests()
    exit_code |= security_check()

    if exit_code == 0:
        print("\n🎉 All checks passed!")
    else:
        print("\n💥 Some checks failed!")

    return exit_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PyIPTV development utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    subparsers.add_parser("install", help="Install development dependencies")

    # Format command
    subparsers.add_parser("format", help="Format code with black and isort")

    # Lint command
    subparsers.add_parser("lint", help="Lint code with flake8")

    # Type check command
    subparsers.add_parser("typecheck", help="Type check code with mypy")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage"
    )
    test_parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    test_parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    test_parser.add_argument("--ui", action="store_true", help="Run only UI tests")
    test_parser.add_argument("--slow", action="store_true", help="Include slow tests")

    # Security command
    subparsers.add_parser("security", help="Run security checks")

    # Build command
    subparsers.add_parser("build", help="Build the package")

    # Clean command
    subparsers.add_parser("clean", help="Clean build artifacts")

    # Pre-commit command
    subparsers.add_parser("pre-commit", help="Set up pre-commit hooks")

    # Check all command
    subparsers.add_parser("check", help="Run all checks")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Command mapping
    commands = {
        "install": install_deps,
        "format": format_code,
        "lint": lint_code,
        "typecheck": type_check,
        "test": lambda: run_tests(args),
        "security": security_check,
        "build": build_package,
        "clean": clean,
        "pre-commit": setup_pre_commit,
        "check": check_all,
    }

    if args.command in commands:
        return commands[args.command]()
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
