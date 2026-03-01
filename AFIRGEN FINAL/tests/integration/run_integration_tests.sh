#!/bin/bash
# Script to run integration tests with proper environment setup

set -e

echo "=========================================="
echo "AFIRGen Integration Tests"
echo "=========================================="
echo ""

# Check if --integration flag is needed
if [ "$1" != "--skip-check" ]; then
    echo "⚠️  WARNING: Integration tests will call real AWS services and incur costs!"
    echo ""
    echo "Estimated cost per test run: \$0.50 - \$2.00"
    echo ""
    read -p "Do you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Integration tests cancelled."
        exit 0
    fi
fi

echo ""
echo "Checking environment variables..."
echo ""

# Check required environment variables
required_vars=(
    "AWS_REGION"
    "S3_BUCKET_NAME"
    "VECTOR_DB_TYPE"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    else
        echo "✓ $var is set"
    fi
done

# Check vector DB specific variables
if [ "$VECTOR_DB_TYPE" = "opensearch" ]; then
    if [ -z "$OPENSEARCH_ENDPOINT" ]; then
        missing_vars+=("OPENSEARCH_ENDPOINT")
    else
        echo "✓ OPENSEARCH_ENDPOINT is set"
    fi
elif [ "$VECTOR_DB_TYPE" = "aurora_pgvector" ]; then
    aurora_vars=("AURORA_HOST" "AURORA_DATABASE" "AURORA_USER" "AURORA_PASSWORD")
    for var in "${aurora_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        else
            echo "✓ $var is set"
        fi
    done
fi

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo ""
    echo "❌ Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please set these variables and try again."
    exit 1
fi

echo ""
echo "✓ All required environment variables are set"
echo ""

# Check AWS credentials
echo "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✓ AWS credentials are valid"
    aws sts get-caller-identity --query 'Account' --output text | xargs echo "  Account:"
else
    echo "❌ AWS credentials are not configured or invalid"
    exit 1
fi

echo ""
echo "Installing test dependencies..."
pip install -q -r tests/requirements-test.txt

echo ""
echo "Running integration tests..."
echo ""

# Run pytest with integration marker
pytest tests/integration/ \
    --integration \
    -v \
    --tb=short \
    --color=yes \
    "$@"

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "=========================================="
    echo "✓ All integration tests passed!"
    echo "=========================================="
else
    echo "=========================================="
    echo "❌ Some integration tests failed"
    echo "=========================================="
fi

exit $exit_code
