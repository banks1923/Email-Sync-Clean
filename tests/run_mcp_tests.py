#!/usr/bin/env python3
"""
Test runner for MCP functionality tests.

Runs unit and integration tests to validate query expansion and parameter handling.
"""
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all MCP-related tests."""
    test_files = [
        "tests/unit/test_search_intelligence_query_expansion.py",
        "tests/integration/test_mcp_parameter_validation.py"
    ]
    
    print("🧪 Running MCP Functionality Tests...")
    print("=" * 60)
    
    # Run each test file
    all_passed = True
    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")
        
        try:
            # Run pytest on the specific file
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file,
                "-v",  # Verbose output
                "--tb=short",  # Short traceback format
                "--no-header",  # No pytest header
                "--disable-warnings"  # Disable warnings for cleaner output
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print(f"✅ {test_file} - PASSED")
                # Show test results
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if '::' in line and ('PASSED' in line or 'FAILED' in line):
                            print(f"  {line}")
            else:
                print(f"❌ {test_file} - FAILED")
                all_passed = False
                # Show errors
                if result.stdout:
                    print("STDOUT:")
                    print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)
                    
        except Exception as e:
            print(f"❌ Error running {test_file}: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All MCP tests passed! Regression protection is active.")
        return 0
    else:
        print("💥 Some tests failed. Please fix issues before proceeding.")
        return 1


def run_specific_test_category(category):
    """Run tests for a specific category."""
    if category == "unit":
        test_files = ["tests/unit/test_search_intelligence_query_expansion.py"]
    elif category == "integration":
        test_files = ["tests/integration/test_mcp_parameter_validation.py"]
    else:
        print(f"Unknown test category: {category}")
        return 1
    
    print(f"🧪 Running {category} tests...")
    
    for test_file in test_files:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_file, 
            "-v", 
            "--tb=short"
        ], cwd=project_root)
        
        if result.returncode != 0:
            return 1
    
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        category = sys.argv[1]
        exit_code = run_specific_test_category(category)
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)