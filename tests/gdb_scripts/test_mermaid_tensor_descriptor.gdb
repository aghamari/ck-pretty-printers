# Test Mermaid diagram generation for tensor_descriptor types
# This test ensures Mermaid diagrams are correctly generated for various tensor_descriptor instances

file /data0/aghamari/composable_kernel/build/bin/basic_gemm
set print thread-events off
set print inferior-events off

# Set breakpoint where tensor_descriptors are available
break block_gemm_pipeline_agmem_bgmem_creg.hpp:321
run
continue

# Load pretty printers
source /home/aghamari/ck-pretty-printers/gdbinit_ck_tile.py

echo \n=== TEST 1: Mermaid for a_lds_block_desc (tensor_descriptor) ===\n
mermaid a_lds_block_desc

echo \n=== TEST 2: Pretty printer output for comparison ===\n
p a_lds_block_desc

quit