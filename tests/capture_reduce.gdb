# GDB capture script for tile_example_reduce binary
# Captures descriptors with various reduction transforms

source gdbinit_ck_tile_fixed_transforms.py

set breakpoint pending on
set confirm off
set print pretty on
set print elements 100
set pagination off

file build/bin/tile_example_reduce

# Set breakpoint in reduce logic
break reduce.cpp:100

run

# Capture types when available
continue

quit
