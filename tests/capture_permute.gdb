# GDB capture script for tile_example_permute binary
# Captures tensor_adaptor and various transforms

source gdbinit_ck_tile_fixed_transforms.py

set breakpoint pending on
set confirm off
set print pretty on
set print elements 100
set pagination off

file build/bin/tile_example_permute

# Set breakpoint in permute logic
break permute.cpp:100

run

# Capture types when available
continue

quit
