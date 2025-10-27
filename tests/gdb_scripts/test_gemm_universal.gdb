# Test script for tile_example_gemm_universal
# Tests tuple types with nested tensor_view and tile_window types

python
import sys
sys.path.insert(0, '/home/aghamari/ck-pretty-printers')
end

source /home/aghamari/ck-pretty-printers/gdbinit_ck_tile.py

set breakpoint pending on
set confirm off
set pagination off

file /data0/aghamari/composable_kernel/build/bin/tile_example_gemm_universal

# Test 1: as_pad_view and ds_pad_view - Line 820 (after both are created)
break universal_gemm_kernel.hpp:820
run
continue

echo \n=== TEST 1: as_pad_view (tuple<tensor_view>) ===\n
print as_pad_view

echo \n\n=== TEST 2: ds_pad_view (empty tuple) ===\n
print ds_pad_view

# Test 3: as_block_window and bs_block_window - Line 937 (all windows in scope)
delete breakpoints
break universal_gemm_kernel.hpp:937
run
continue

echo \n\n=== TEST 3: as_block_window (tuple<tile_window>) ===\n
print as_block_window

echo \n\n=== TEST 4: bs_block_window (tuple<tile_window>) ===\n
print bs_block_window

quit
