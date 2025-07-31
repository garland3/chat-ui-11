#!/bin/bash
set -e

echo "Starting Test Suite"
echo "===================="
echo "Container: $(hostname)"
echo "Date: $(date)"
echo "Working Directory: $(pwd)"
echo ""

# Default to running all tests unless specific test type is specified
TEST_TYPE=${1:-all}

# Function to run a specific test script
run_test() {
    local test_name=$1
    local script_path="/app/test/${test_name}_tests.sh"
    
    echo "--- Running $test_name tests ---"
    if [ -f "$script_path" ]; then
        chmod +x "$script_path"
        bash "$script_path"
        echo "$test_name tests: PASSED"
    else
        echo "ERROR: Test script not found: $script_path"
        exit 1
    fi
    echo ""
}

# Main test execution
case $TEST_TYPE in
    "backend")
        echo "Running Backend Tests Only"
        run_test "backend"
        ;;
    "frontend") 
        echo "Running Frontend Tests Only"
        run_test "frontend"
        ;;
    "e2e")
        echo "Running E2E Tests Only"
        run_test "e2e"
        ;;
    "all")
        echo "Running All Test Suites"
        run_test "backend"
        run_test "frontend"
        run_test "e2e"
        ;;
    *)
        echo "ERROR: Unknown test type: $TEST_TYPE"
        echo "Usage: $0 [backend|frontend|e2e|all]"
        exit 1
        ;;
esac

echo "===================="
echo "All Tests Completed Successfully!"
echo "Date: $(date)"