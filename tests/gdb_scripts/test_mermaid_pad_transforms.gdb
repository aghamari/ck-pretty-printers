# Test Mermaid diagram generation for pad transforms
# This test ensures pad, right_pad, left_pad transforms are properly visualized

file /data0/aghamari/composable_kernel/build/bin/tile_example_gemm_universal
set print thread-events off
set print inferior-events off

# Set breakpoint where pad views are created
break universal_gemm_kernel.hpp:820
run

# Load pretty printers
source /home/aghamari/ck-pretty-printers/gdbinit_ck_tile.py

echo \n=== TEST 1: Pretty printer for as_pad_view ===\n
p as_pad_view

echo \n=== TEST 2: Mermaid for as_pad_view (should show pad transform) ===\n
# Note: as_pad_view is a tuple, so we need to access its element
# First check what's inside
p as_pad_view

echo \n=== TEST 3: Pretty printer for ds_pad_view ===\n
p ds_pad_view

# Continue to next breakpoint
break universal_gemm_kernel.hpp:937
continue

echo \n=== TEST 4: Check for more pad-related variables ===\n
# Look for any tensor with pad transforms
info locals

quit