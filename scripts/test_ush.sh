#!/bin/bash
# Test Universal Semantic Hierarchy (USH) Integration

# Activate virtual environment if it exists
if [ -d "aqea-venv" ]; then
    echo "Activating virtual environment..."
    source aqea-venv/bin/activate
fi

# Ensure examples output directory exists
mkdir -p examples/output

# Set Python path to include project directory
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run USH demo
echo "Running USH demo..."
python examples/ush_demo.py

# Run USH integration tests
echo -e "\nRunning USH integration tests..."
python -m unittest tests/test_ush_integration.py

# Show results
echo -e "\nTest Results:"
if [ -f "examples/output/ush_demo_results.json" ]; then
    echo "✅ USH demo completed successfully!"
    echo "Results saved to examples/output/ush_demo_results.json"
else
    echo "❌ USH demo failed!"
fi

echo -e "\nUSH Integration Test Complete!" 