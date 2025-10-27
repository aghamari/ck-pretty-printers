"""
CK-Tile GDB Pretty Printers
Main entry point for registering all pretty printers.

This is the refactored, modular version of the CK-Tile pretty printers.
"""

import gdb
import gdb.printing
import sys
import os

# Add the package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all printer classes
from gdbinit_ck_tile.printers.tensor_descriptor import TensorDescriptorPrinter
from gdbinit_ck_tile.printers.tensor_adaptor import TensorAdaptorPrinter
from gdbinit_ck_tile.printers.tensor_coordinate import (
    TensorCoordinatePrinter,
    TensorAdaptorCoordinatePrinter,
)
from gdbinit_ck_tile.printers.tensor_view import TensorViewPrinter
from gdbinit_ck_tile.printers.tile_distribution import (
    TileDistributionPrinter,
    TileDistributionEncodingPrinter,
    TileWindowPrinter,
    StaticDistributedTensorPrinter,
)
from gdbinit_ck_tile.printers.containers import (
    TuplePrinter,
    ArrayPrinter,
    ThreadBufferPrinter,
)


def build_pretty_printer():
    """Build and return the pretty printer collection."""
    pp = gdb.printing.RegexpCollectionPrettyPrinter("ck_tile")

    # Register all printers
    pp.add_printer(
        'tensor_descriptor',
        '^ck_tile::tensor_descriptor<.*>$',
        TensorDescriptorPrinter
    )
    pp.add_printer(
        'tensor_adaptor',
        '^ck_tile::tensor_adaptor<.*>$',
        TensorAdaptorPrinter
    )
    pp.add_printer(
        'tensor_adaptor_coordinate',
        '^ck_tile::tensor_adaptor_coordinate<.*>$',
        TensorAdaptorCoordinatePrinter
    )
    pp.add_printer(
        'tensor_coordinate',
        '^ck_tile::tensor_coordinate<.*>$',
        TensorCoordinatePrinter
    )
    pp.add_printer(
        'tensor_view',
        '^ck_tile::tensor_view<.*>$',
        TensorViewPrinter
    )
    pp.add_printer(
        'tile_distribution',
        '^ck_tile::tile_distribution<.*>$',
        TileDistributionPrinter
    )
    pp.add_printer(
        'tile_distribution_encoding',
        '^ck_tile::tile_distribution_encoding<.*>$',
        TileDistributionEncodingPrinter
    )
    pp.add_printer(
        'tile_window_with_static_distribution',
        '^ck_tile::tile_window_with_static_distribution<.*>$',
        TileWindowPrinter
    )
    pp.add_printer(
        'tile_window_with_static_lengths',
        '^ck_tile::tile_window_with_static_lengths<.*>$',
        TileWindowPrinter
    )
    pp.add_printer(
        'tile_window',
        '^ck_tile::tile_window<.*>$',
        TileWindowPrinter
    )
    pp.add_printer(
        'static_distributed_tensor',
        '^ck_tile::static_distributed_tensor<.*>$',
        StaticDistributedTensorPrinter
    )

    # Core container printers
    # Patterns need to handle const/volatile qualifiers and references
    pp.add_printer(
        'tuple',
        '(^|.*\s)ck_tile::tuple<.*>',
        TuplePrinter
    )
    pp.add_printer(
        'array',
        '(^|.*\s)ck_tile::array<.*>',
        ArrayPrinter
    )
    pp.add_printer(
        'multi_index',
        '(^|.*\s)ck_tile::multi_index<.*>',
        ArrayPrinter  # multi_index is just an alias for array
    )
    pp.add_printer(
        'thread_buffer',
        '(^|.*\s)ck_tile::thread_buffer<.*>',
        ThreadBufferPrinter
    )

    return pp


def register_printers(obj):
    """Register the pretty printers with GDB."""
    gdb.printing.register_pretty_printer(obj, build_pretty_printer(), replace=True)


# Register the printers when this module is loaded
try:
    register_printers(None)
    print("CK-Tile pretty printers registered successfully")
    print("Registered printers for:")
    print("  Tensors: tensor_descriptor, tensor_adaptor, tensor_view, tensor_coordinate")
    print("  Distributions: tile_distribution, tile_window, static_distributed_tensor")
    print("  Containers: tuple, array, multi_index, thread_buffer")
except Exception as e:
    print(f"Failed to register pretty printers: {e}")
    import traceback
    traceback.print_exc()
