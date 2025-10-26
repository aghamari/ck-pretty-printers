# GDB capture script for basic_gemm binary
# Captures output from various CK-Tile types for regression testing

source gdbinit_ck_tile.py

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

# Capture tensor_descriptor
set logging file tests/golden/basic_gemm_tensor_descriptor_a_lds.txt
set logging overwrite on
set logging on
print a_lds_block.desc_
set logging off

# Capture tensor_view
set logging file tests/golden/basic_gemm_tensor_view_dram_window.txt
set logging overwrite on
set logging on
print a_copy_dram_window
set logging off

# Capture tensor_coordinate from pre_computed_coords
set logging file tests/golden/basic_gemm_tensor_coordinate.txt
set logging overwrite on
set logging on
print a_copy_dram_window.pre_computed_coords_
set logging off

# Capture the full a_lds_block structure
set logging file tests/golden/basic_gemm_static_distributed_tensor.txt
set logging overwrite on
set logging on
print a_lds_block
set logging off

quit
