#!/usr/bin/env python3
"""
Test runner script for CatCare project
"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*50}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True


def main():
    """Main test runner"""
    print("CatCare Project Test Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Install test dependencies
    if not run_command("pip install -r requirements-dev.txt", "Installing test dependencies"):
        sys.exit(1)
    
    # Run code formatting check
    run_command("black --check catcare/ tests/", "Code formatting check")
    
    # Run import sorting check
    run_command("isort --check-only catcare/ tests/", "Import sorting check")
    
    # Run linting
    run_command("flake8 catcare/ tests/ --max-line-length=100 --ignore=E203,W503", "Code linting")
    
    # Run security check
    run_command("bandit -r catcare/ -f json", "Security scanning")
    
    # Run tests with coverage
    if run_command("pytest tests/ -v --cov=catcare --cov-report=html --cov-report=term", "Running tests"):
        print("\n🎉 All tests passed!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("✅ All checks completed successfully!")
    print("📁 Check htmlcov/index.html for detailed coverage report")
    print("="*50)


if __name__ == "__main__":
    main()