# Test Mermaid diagram generation for tensor_adaptor types
# This test is critical as it includes ps_ys_to_xs_ which requires special handling

file /data0/aghamari/composable_kernel/build/bin/basic_gemm
set print thread-events off
set print inferior-events off

# Set breakpoint where tensor_adaptors are available
break gemm_basic_xdl_kernel.cpp:25
run

# Load pretty printers
source /home/aghamari/ck-pretty-printers/gdbinit_ck_tile.py

echo \n=== TEST 1: Mermaid for ps_ys_to_xs_ (critical special case) ===\n
mermaid a_copy_dram_window.tile_dstr_.ps_ys_to_xs_

echo \n=== TEST 2: Pretty printer output for ps_ys_to_xs_ ===\n
p a_copy_dram_window.tile_dstr_.ps_ys_to_xs_

quit