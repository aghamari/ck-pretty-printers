# GDB capture script for testing refactored pretty printer
# Uses gdbinit_ck_tile_refactored.py instead of the original

source gdbinit_ck_tile_refactored.py

set breakpoint pending on
set confirm off
set style address foreground cyan
set print pretty on
set print elements 100
set pagination off

file build/bin/basic_gemm

# Set breakpoint where we have interesting tensor types
tb BlockGemmPipelineAGmemBGmemCReg::operator()
b block_gemm_pipeline_agmem_bgmem_creg.hpp:321

run

# Continue to the breakpoint
continue

# Capture tensor_descriptor only (the refactored printer)
set logging file /tmp/refactored_test_descriptor.txt
set logging overwrite on
set logging on
print a_lds_block.desc_
set logging off

quit
