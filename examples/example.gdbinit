# Example .gdbinit configuration for CK-Tile pretty printers
# Copy this to your ~/.gdbinit and adjust paths

set pagination off
set print pretty on

python
import sys
import os

# Path to CK-Tile pretty printers (CHANGE THIS to your path)
ck_tile_printers_path = '/path/to/ck-tile-gdb-printers'

# Optional: Load libstdc++ pretty printers
sys.path.insert(0, '/usr/share/gcc/python')
try:
    from libstdcxx.v6.printers import register_libstdcxx_printers
    from libstdcxx.v6.xmethods import register_libstdcxx_xmethods
    register_libstdcxx_printers(None)
    register_libstdcxx_xmethods(gdb.current_objfile())
except ImportError:
    print("Warning: libstdc++ pretty printers not found")

# Load CK-Tile pretty printers
if os.path.exists(os.path.join(ck_tile_printers_path, 'gdbinit_ck_tile.py')):
    sys.path.insert(0, ck_tile_printers_path)
    gdb.execute(f'source {ck_tile_printers_path}/gdbinit_ck_tile.py')
else:
    print(f"Warning: CK-Tile pretty printers not found at {ck_tile_printers_path}")
end
