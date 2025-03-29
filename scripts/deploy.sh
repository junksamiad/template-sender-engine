#!/bin/bash
# CDK deployment script for AI Multi-Communications Engine

# Ensure we're in the project root
cd "$(dirname "$0")/.." || exit 1

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    source .env
else
    echo "Warning: .env file not found"
fi

# Ensure virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Activating virtual environment"
    source venv/bin/activate
fi

# Set Python path to include project root
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run the CDK command with arguments
echo "Running CDK command: cdk $*"
PYTHONPATH=$(pwd) python -m scripts.cdk_deploy "$@" 