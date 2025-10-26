# GDB capture script for tile_example_moe_sorting binary
# Captures tile_distribution and related types

source gdbinit_ck_tile_fixed_transforms.py

set breakpoint pending on
set confirm off
set print pretty on
set print elements 100
set pagination off

file build/bin/tile_example_moe_sorting

# Set a breakpoint in the main sorting logic
break moe_sorting.cpp:200

run

# If we hit the breakpoint, capture relevant types
# (Will need to adjust variable names based on actual code)
continue

quit
