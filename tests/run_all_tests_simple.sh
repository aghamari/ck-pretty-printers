#!/bin/bash

echo "============================================"
echo "CK-Pretty-Printers Test Suite"
echo "============================================"
echo

# Test 1: Python unit tests
echo "Running Python unit tests..."
python3 test_mermaid_simple.py

echo
echo "----------------------------------------"
echo

# Test 2: Parser test
echo "Running parser test..."
python3 test_parser_descriptor.py

echo
echo "----------------------------------------"
echo

# Test 3: GDB mock tests
echo "Running GDB mock tests..."
echo "Testing 15-transform descriptor..."
rocgdb -batch -x test_15_transforms.gdb 2>&1 | tail -5

echo
echo "Testing 5-transform adaptor..."
rocgdb -batch -x test_bottom_fix.gdb 2>&1 | grep "Bottom\[1\]"

echo
echo "============================================"
echo "Test suite complete!"
echo "============================================"