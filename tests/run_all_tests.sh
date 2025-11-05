#!/bin/bash

echo "============================================"
echo "CK-Pretty-Printers Comprehensive Test Suite"
echo "============================================"
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2

    echo -n "Testing $test_name... "
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo "1. Python Unit Tests"
echo "===================="

# Test PrettyPrinterOutputParser
run_test "PrettyPrinterOutputParser" "python3 -c '
from gdbinit_ck_tile.utils.pretty_printer_parser import PrettyPrinterOutputParser
output = \"\"\"tensor_adaptor:
  ntransform: 5
  bottom_dimension_ids: [0, 1]
  top_dimension_ids: [8, 9, 3, 7]
\"\"\"
parsed = PrettyPrinterOutputParser.parse_complete(output)
assert parsed[\"ntransform\"] == 5
assert parsed[\"bottom_dims\"] == [0, 1]
assert parsed[\"top_dims\"] == [8, 9, 3, 7]
'"

# Test MermaidDiagramBuilder
run_test "MermaidDiagramBuilder" "python3 -c '
from gdbinit_ck_tile.utils.mermaid_builder import MermaidDiagramBuilder
builder = MermaidDiagramBuilder()
result = builder.build(
    transforms=[\"replicate\", \"unmerge\"],
    lower_dims=[[], [0]],
    upper_dims=[[2], [3, 4]],
    bottom_dims=[0, 1],
    top_dims=[2, 3, 4],
    title=\"Test\"
)
assert \"```mermaid\" in result
assert \"Bottom[0]\" in result
assert \"Bottom[1]\" in result
'"

# Test ValueAccessStrategy
run_test "ValueAccessStrategy" "python3 -c '
from gdbinit_ck_tile.utils.value_access import ValueAccessStrategy
# Just test import and basic functionality
assert ValueAccessStrategy is not None
'"

echo
echo "2. Parser Tests"
echo "==============="

# Test parsing tensor_descriptor output
run_test "Parse tensor_descriptor" "python3 test_parser_descriptor.py 2>/dev/null | grep -q \"Successfully generated\""

# Test parsing with empty dimensions
run_test "Parse empty dimensions" "python3 -c '
from gdbinit_ck_tile.utils.pretty_printer_parser import PrettyPrinterOutputParser
output = \"\"\"[0] replicate
    upper: [2]
[1] unmerge
    lower: [0]
    upper: [3, 4, 5]\"\"\"
transforms = PrettyPrinterOutputParser.parse_transforms(output)
assert len(transforms) == 2
assert transforms[0][\"lower\"] == []
assert transforms[0][\"upper\"] == [2]
'"

echo
echo "3. Integration Tests"
echo "===================="

# Test complete mermaid generation
run_test "Integration test" "python3 test_mermaid_simple.py 2>/dev/null | grep -q \"All tests passed\""

# Test dimension flow
run_test "Dimension flow" "python3 debug_mermaid.py 2>/dev/null | grep -q \"Top dimension connections\""

echo
echo "4. GDB Mock Tests"
echo "=================="

# Test with mock GDB for tensor_descriptor
run_test "Mock tensor_descriptor (15 transforms)" "rocgdb -batch -x test_15_transforms.gdb 2>&1 | grep -q \"All 15 transforms processed successfully\""

# Test with mock GDB for tensor_adaptor
run_test "Mock tensor_adaptor (5 transforms)" "rocgdb -batch -x test_bottom_fix.gdb 2>&1 | grep -q \"Bottom\[1\] is now included\""

echo
echo "5. Import Tests"
echo "==============="

# Test all imports work
run_test "Import all modules" "python3 -c '
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(\"gdbinit_ck_tile.py\")))
from gdbinit_ck_tile.commands.mermaid_generator import MermaidGenerator
from gdbinit_ck_tile.utils.pretty_printer_parser import PrettyPrinterOutputParser
from gdbinit_ck_tile.utils.mermaid_builder import MermaidDiagramBuilder
from gdbinit_ck_tile.utils.value_access import ValueAccessStrategy
from gdbinit_ck_tile.core.transform_mixin import TransformMixin
print(\"All imports successful\")
' 2>/dev/null | grep -q \"All imports successful\""

echo
echo "============================================"
echo "Test Results Summary"
echo "============================================"
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo "The refactored code is working correctly."
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed!${NC}"
    echo "Please check the failing tests above."
    exit 1
fi