#!/bin/bash
# Run all CK-Tile pretty printer regression tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GDB_SCRIPTS_DIR="${SCRIPT_DIR}/gdb_scripts"
GOLDEN_DIR="${SCRIPT_DIR}/golden_outputs"
TEMP_DIR="${SCRIPT_DIR}/temp_outputs"
COMPARE_SCRIPT="${SCRIPT_DIR}/compare_outputs.py"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create temp directory for test outputs
mkdir -p "${TEMP_DIR}"

echo "========================================"
echo "CK-Tile Pretty Printer Regression Tests"
echo "========================================"
echo

# Check if composable_kernel is built
CK_BUILD_DIR="/data0/aghamari/composable_kernel/build"
if [ ! -d "${CK_BUILD_DIR}/bin" ]; then
    echo -e "${RED}Error: Composable Kernel build directory not found${NC}"
    echo "Expected: ${CK_BUILD_DIR}/bin"
    exit 1
fi

# Track test results
total_tests=0
passed_tests=0
failed_tests=0

# Function to run a single test
run_test() {
    local test_name="$1"
    local gdb_script="${GDB_SCRIPTS_DIR}/${test_name}.gdb"
    local golden_output="${GOLDEN_DIR}/${test_name}_baseline.txt"
    local test_output="${TEMP_DIR}/${test_name}_current.txt"

    if [ ! -f "${gdb_script}" ]; then
        echo -e "${YELLOW}⚠️  Skipping ${test_name}: GDB script not found${NC}"
        return
    fi

    if [ ! -f "${golden_output}" ]; then
        echo -e "${YELLOW}⚠️  Skipping ${test_name}: Golden output not found${NC}"
        echo "     Run 'capture_baseline.sh' first to generate golden outputs"
        return
    fi

    echo "Running test: ${test_name}"
    total_tests=$((total_tests + 1))

    # Run the test (suppress most GDB output except our test results)
    cd "${CK_BUILD_DIR}/.." || exit 1
    if timeout 90 rocgdb --batch -x "${gdb_script}" > "${test_output}" 2>&1; then
        # Compare outputs
        if python3 "${COMPARE_SCRIPT}" "${golden_output}" "${test_output}" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${test_name} PASSED${NC}"
            passed_tests=$((passed_tests + 1))
        else
            echo -e "${RED}❌ ${test_name} FAILED${NC}"
            echo "     Run: python3 ${COMPARE_SCRIPT} ${golden_output} ${test_output}"
            echo "     to see detailed differences"
            failed_tests=$((failed_tests + 1))
        fi
    else
        echo -e "${RED}❌ ${test_name} FAILED (GDB execution error)${NC}"
        failed_tests=$((failed_tests + 1))
    fi
    echo
}

# Run all tests
echo "Discovering tests..."
test_files=$(find "${GDB_SCRIPTS_DIR}" -name "*.gdb" -type f)

if [ -z "$test_files" ]; then
    echo -e "${RED}No test scripts found in ${GDB_SCRIPTS_DIR}${NC}"
    exit 1
fi

echo "Found $(echo "$test_files" | wc -l) test script(s)"
echo

for test_file in $test_files; do
    test_name=$(basename "${test_file}" .gdb)
    run_test "${test_name}"
done

# Print summary
echo "========================================"
echo "Test Summary"
echo "========================================"
echo "Total tests:  ${total_tests}"
echo -e "Passed:       ${GREEN}${passed_tests}${NC}"
echo -e "Failed:       ${RED}${failed_tests}${NC}"
echo

if [ ${failed_tests} -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo
    echo "Test outputs saved in: ${TEMP_DIR}"
    echo "To see detailed differences, run:"
    echo "  python3 ${COMPARE_SCRIPT} <golden_file> <test_file>"
    exit 1
fi
