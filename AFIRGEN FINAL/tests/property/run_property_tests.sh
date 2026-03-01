#!/bin/bash
# Run property-based tests for AFIRGen Bedrock Migration

echo "Running Property-Based Tests..."
echo "================================"
echo ""

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run tests with different profiles
if [ "$1" == "quick" ]; then
    echo "Running quick tests (20 examples per test)..."
    HYPOTHESIS_PROFILE=dev pytest tests/property/ -v --tb=short
elif [ "$1" == "ci" ]; then
    echo "Running CI tests (100 examples per test)..."
    HYPOTHESIS_PROFILE=ci pytest tests/property/ -v --tb=short --hypothesis-show-statistics
elif [ "$1" == "debug" ]; then
    echo "Running debug tests (10 examples per test, verbose)..."
    HYPOTHESIS_PROFILE=debug pytest tests/property/ -v --tb=long
else
    echo "Running default tests (50 examples per test)..."
    pytest tests/property/ -v --tb=short
fi

echo ""
echo "================================"
echo "Property tests completed!"
