# CK-Tile Pretty Printer Regression Tests

This directory contains regression tests for the CK-Tile GDB pretty printers.

## Overview

The test suite ensures that changes to the pretty printers don't break existing functionality. Tests capture the output of pretty printers at specific breakpoints in CK-Tile example binaries and compare them against golden (baseline) outputs.

## Directory Structure

```
tests/
├── README.md                    # This file
├── gdb_scripts/                 # GDB test scripts
│   └── test_gemm_universal.gdb  # Tests for GEMM universal kernel
├── golden_outputs/              # Baseline outputs (expected results)
│   └── gemm_universal_baseline.txt
├── temp_outputs/                # Temporary test outputs (gitignored)
├── run_all_tests.sh             # Main test runner
└── compare_outputs.py           # Output comparison tool
```

## Test Cases

### test_gemm_universal.gdb

Tests container pretty printers using the `tile_example_gemm_universal` binary:

| Test | Breakpoint | Variable | Type | Description |
|------|------------|----------|------|-------------|
| TEST 1 | universal_gemm_kernel.hpp:820 | `as_pad_view` | `tuple<tensor_view>` | Single-element tuple containing a tensor_view |
| TEST 2 | universal_gemm_kernel.hpp:820 | `ds_pad_view` | `tuple<>` | Empty tuple (0 elements) |
| TEST 3 | universal_gemm_kernel.hpp:937 | `as_block_window` | `tuple<tile_window_with_static_lengths>` | Tuple with tile_window containing nested tensor_view and tensor_descriptor |
| TEST 4 | universal_gemm_kernel.hpp:937 | `bs_block_window` | `tuple<tile_window_with_static_lengths>` | Another tile_window tuple |

### Coverage

These tests verify:
- ✅ TuplePrinter with 0, 1, and nested elements
- ✅ Recursive dispatch: tile_window → tensor_view → tensor_descriptor
- ✅ Proper handling of const references
- ✅ Empty containers
- ✅ Nested type resolution

## Running Tests

### Run All Tests

```bash
cd /home/aghamari/ck-pretty-printers/tests
./run_all_tests.sh
```

This will:
1. Run all GDB test scripts
2. Compare outputs with golden baselines
3. Report pass/fail for each test
4. Print a summary

### Run a Single Test

```bash
cd /data0/aghamari/composable_kernel
rocgdb --batch -x /home/aghamari/ck-pretty-printers/tests/gdb_scripts/test_gemm_universal.gdb
```

### Compare Outputs Manually

```bash
python3 compare_outputs.py \
    golden_outputs/gemm_universal_baseline.txt \
    temp_outputs/gemm_universal_current.txt
```

## Comparison Logic

The `compare_outputs.py` tool performs **structural comparison** rather than exact string matching. It:

1. Extracts individual test sections from the output
2. Identifies key structural features:
   - Container types and element counts
   - Nested type names
   - Transform types
   - Key numeric fields (ntransform, ndim_*, etc.)
3. Compares structures, allowing for minor formatting differences

This approach makes tests resilient to:
- Whitespace changes
- Indentation adjustments
- Minor formatting tweaks

But catches real regressions like:
- Wrong container type
- Incorrect element count
- Missing nested types
- Wrong transform count or types

## Adding New Tests

### 1. Create a GDB Script

Create a new file in `gdb_scripts/`, for example `test_reduce.gdb`:

```gdb
python
import sys
sys.path.insert(0, '/home/aghamari/ck-pretty-printers')
end

source /home/aghamari/ck-pretty-printers/gdbinit_ck_tile.py

set breakpoint pending on
set confirm off
set pagination off

file /data0/aghamari/composable_kernel/build/bin/tile_example_reduce

# Set breakpoint where test variables are in scope
break reduce_kernel.hpp:123
run
continue

echo \n=== TEST 1: some_variable ===\n
print some_variable

quit
```

### 2. Capture Baseline

Run the test once and save as golden output:

```bash
cd /data0/aghamari/composable_kernel
rocgdb --batch -x /home/aghamari/ck-pretty-printers/tests/gdb_scripts/test_reduce.gdb \
    > /home/aghamari/ck-pretty-printers/tests/golden_outputs/test_reduce_baseline.txt 2>&1
```

### 3. Verify

The test will now run automatically with `./run_all_tests.sh`.

## Updating Baselines

If you make intentional changes to printer output format, update the golden outputs:

```bash
# Re-capture baselines
cd /data0/aghamari/composable_kernel
for script in /home/aghamari/ck-pretty-printers/tests/gdb_scripts/*.gdb; do
    name=$(basename "$script" .gdb)
    rocgdb --batch -x "$script" \
        > "/home/aghamari/ck-pretty-printers/tests/golden_outputs/${name}_baseline.txt" 2>&1
done
```

⚠️ **Important**: Only update baselines when you've intentionally changed the output format. Review diffs carefully!

## Troubleshooting

### Test hangs

- GDB tests have a 90-second timeout
- If tests consistently timeout, check if the binary runs correctly
- Verify breakpoint locations are valid

### No tests found

- Ensure `.gdb` files exist in `gdb_scripts/`
- Check that files have correct extension

### Comparison failures

- Run comparison tool manually to see detailed differences:
  ```bash
  python3 compare_outputs.py golden_outputs/X_baseline.txt temp_outputs/X_current.txt
  ```
- Check if differences are structural (real regression) or just formatting

### GDB can't find symbols

- Verify the binary was built with debug symbols: `-DCMAKE_BUILD_TYPE=Debug`
- Check that breakpoint file path matches your source tree

## Known Issues

1. Some `tensor_view` elements show `[error: There is no member or method named desc_.]`
   - This is a separate issue from TuplePrinter functionality
   - Tests focus on container structure, not nested element details

2. GPU memory addresses may not be accessible
   - Tests rely on type information from template parameters
   - Runtime values may be inaccessible, but structure should be correct
