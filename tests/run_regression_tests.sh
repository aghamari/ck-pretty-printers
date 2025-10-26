#!/bin/bash
# Regression test runner for CK-Tile pretty printers
# Compares current pretty printer output against golden files

set -e  # Exit on first error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOLDEN_DIR="$SCRIPT_DIR/golden"
TEMP_DIR="/tmp/ck_tile_regression_$$"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

mkdir -p "$TEMP_DIR"

# Track results
total_tests=0
passed_tests=0
failed_tests=0

echo "========================================"
echo "CK-Tile Pretty Printer Regression Tests"
echo "========================================"
echo

# Function to run a single test
run_test() {
    local test_name="$1"
    local test_script="$SCRIPT_DIR/capture_${test_name}.gdb"

    if [ ! -f "$test_script" ]; then
        echo -e "${YELLOW}SKIPPED${NC} $test_name (script not found)"
        return 0
    fi

    echo -n "Testing $test_name... "

    # Create a temp version of the script that writes to temp dir
    local temp_script="$TEMP_DIR/${test_name}.gdb"
    sed "s|tests/golden/|$TEMP_DIR/|g" "$test_script" > "$temp_script"

    # Run GDB script and capture output to temp files
    if ! rocgdb --batch -x "$temp_script" > "$TEMP_DIR/${test_name}_gdb.log" 2>&1; then
        echo -e "${RED}FAILED${NC} (GDB error)"
        echo "  See $TEMP_DIR/${test_name}_gdb.log for details"
        failed_tests=$((failed_tests + 1))
        total_tests=$((total_tests + 1))
        return 1
    fi

    # Compare each golden file for this test
    local test_passed=true
    local files_checked=0
    local differences_found=()

    for golden_file in "$GOLDEN_DIR/${test_name}"_*.txt; do
        if [ ! -f "$golden_file" ]; then
            continue
        fi

        files_checked=$((files_checked + 1))
        local basename=$(basename "$golden_file")
        local temp_file="$TEMP_DIR/$basename"

        if [ ! -f "$temp_file" ]; then
            echo -e "${RED}FAILED${NC}"
            echo "  Output file not generated: $basename"
            test_passed=false
            differences_found+=("  Missing: $basename")
            continue
        fi

        # Compare files using structural comparison (ignores runtime values)
        if ! python3 "$SCRIPT_DIR/compare_structure.py" "$golden_file" "$temp_file" \
            > "$TEMP_DIR/${basename}.diff" 2>&1; then
            test_passed=false
            differences_found+=("  Differs: $basename (see $TEMP_DIR/${basename}.diff)")
        fi
    done

    if [ $files_checked -eq 0 ]; then
        echo -e "${YELLOW}SKIPPED${NC} (no golden files)"
        return 0
    fi

    total_tests=$((total_tests + 1))

    if [ "$test_passed" = true ]; then
        echo -e "${GREEN}PASSED${NC} ($files_checked files)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}FAILED${NC}"
        for diff_msg in "${differences_found[@]}"; do
            echo "$diff_msg"
        done
        failed_tests=$((failed_tests + 1))
    fi
}

# Run tests for each test we have golden files for
run_test "basic_gemm"
run_test "moe_sorting"
run_test "permute"
run_test "reduce"

echo
echo "========================================"
echo "Results: $passed_tests/$total_tests passed"
if [ $failed_tests -gt 0 ]; then
    echo -e "${RED}$failed_tests tests failed${NC}"
    echo "Diff files available in: $TEMP_DIR"
    echo "========================================"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    echo "========================================"
    # Clean up temp directory on success
    rm -rf "$TEMP_DIR"
    exit 0
fi
