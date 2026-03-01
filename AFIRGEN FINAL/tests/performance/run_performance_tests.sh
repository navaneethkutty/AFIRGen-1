#!/bin/bash

# Performance Test Runner for AFIRGen Bedrock Migration
# This script runs performance tests and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "AFIRGen Performance Test Runner"
echo "=========================================="
echo ""

# Check if --integration flag should be used
if [ "$1" != "--skip-integration-check" ]; then
    echo -e "${YELLOW}Warning: Performance tests will make real AWS API calls${NC}"
    echo "This will incur costs. Continue? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
fi

# Check required environment variables
echo "Checking environment variables..."
REQUIRED_VARS=("AWS_REGION" "S3_BUCKET_NAME" "VECTOR_DB_TYPE")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# Check vector database specific variables
if [ "$VECTOR_DB_TYPE" = "opensearch" ]; then
    if [ -z "$OPENSEARCH_ENDPOINT" ]; then
        echo -e "${RED}Error: OPENSEARCH_ENDPOINT not set for opensearch database type${NC}"
        exit 1
    fi
elif [ "$VECTOR_DB_TYPE" = "aurora_pgvector" ]; then
    if [ -z "$AURORA_HOST" ]; then
        echo -e "${RED}Error: AURORA_HOST not set for aurora_pgvector database type${NC}"
        exit 1
    fi
else
    echo -e "${RED}Error: Invalid VECTOR_DB_TYPE. Must be 'opensearch' or 'aurora_pgvector'${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables validated${NC}"
echo ""

# Create results directory
RESULTS_DIR="performance_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Run latency tests
echo "=========================================="
echo "Running Latency Tests..."
echo "=========================================="
pytest tests/performance/test_latency.py \
    --integration \
    -v \
    -s \
    --junitxml="$RESULTS_DIR/latency_results.xml" \
    --tb=short \
    2>&1 | tee "$RESULTS_DIR/latency_output.log"

LATENCY_EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Running Concurrency Tests..."
echo "=========================================="
pytest tests/performance/test_concurrency.py \
    --integration \
    -v \
    -s \
    --junitxml="$RESULTS_DIR/concurrency_results.xml" \
    --tb=short \
    2>&1 | tee "$RESULTS_DIR/concurrency_output.log"

CONCURRENCY_EXIT_CODE=$?

# Generate summary report
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="

if [ $LATENCY_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Latency tests: PASSED${NC}"
else
    echo -e "${RED}✗ Latency tests: FAILED${NC}"
fi

if [ $CONCURRENCY_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Concurrency tests: PASSED${NC}"
else
    echo -e "${RED}✗ Concurrency tests: FAILED${NC}"
fi

echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""

# Create summary file
cat > "$RESULTS_DIR/SUMMARY.md" << EOF
# Performance Test Summary

**Date:** $(date)
**AWS Region:** $AWS_REGION
**Vector DB Type:** $VECTOR_DB_TYPE

## Test Results

### Latency Tests
- Exit Code: $LATENCY_EXIT_CODE
- Status: $([ $LATENCY_EXIT_CODE -eq 0 ] && echo "PASSED" || echo "FAILED")
- Log: latency_output.log
- XML Report: latency_results.xml

### Concurrency Tests
- Exit Code: $CONCURRENCY_EXIT_CODE
- Status: $([ $CONCURRENCY_EXIT_CODE -eq 0 ] && echo "PASSED" || echo "FAILED")
- Log: concurrency_output.log
- XML Report: concurrency_results.xml

## Files Generated

- \`latency_output.log\`: Detailed output from latency tests
- \`concurrency_output.log\`: Detailed output from concurrency tests
- \`latency_results.xml\`: JUnit XML report for latency tests
- \`concurrency_results.xml\`: JUnit XML report for concurrency tests

## Next Steps

1. Review the log files for detailed performance metrics
2. Check for any failed tests and investigate root causes
3. Compare results with baseline/previous runs
4. Update performance documentation if needed

## Performance Metrics

Key metrics to review in the logs:
- End-to-end FIR generation latency (P50, P95, P99)
- Component latency breakdown
- Concurrent request success rate
- System behavior under sustained load

EOF

echo "Summary report created: $RESULTS_DIR/SUMMARY.md"
echo ""

# Exit with failure if any tests failed
if [ $LATENCY_EXIT_CODE -ne 0 ] || [ $CONCURRENCY_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Some tests failed. Check the logs for details.${NC}"
    exit 1
else
    echo -e "${GREEN}All performance tests passed!${NC}"
    exit 0
fi
