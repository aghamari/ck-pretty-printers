"""
Data-driven printer dispatcher for CK-Tile types.

This module provides a reusable, data-driven approach to dispatching pretty printers
based on type strings. It eliminates code duplication and makes adding new printer
types much easier.
"""

from typing import Optional, Any


# Printer type mapping
# Format: (type_pattern, printer_module, printer_class)
# IMPORTANT: Order matters! More specific types must come before less specific ones.
# For example, tile_window_with_static_lengths contains tensor_view, so it must be
# checked before tensor_view.

PRINTER_TYPE_MAP = [
    # Tile window types (most specific - contain tensor_view)
    ('tile_window_with_static_distribution<', 'tile_distribution', 'TileWindowPrinter'),
    ('tile_window_with_static_lengths<', 'tile_distribution', 'TileWindowPrinter'),
    ('tile_window<', 'tile_distribution', 'TileWindowPrinter'),

    # Static distributed tensor (contains tensor_adaptor/view)
    ('static_distributed_tensor<', 'tile_distribution', 'StaticDistributedTensorPrinter'),

    # Tensor view/adaptor (contain tensor_descriptor)
    ('tensor_view<', 'tensor_view', 'TensorViewPrinter'),
    ('tensor_adaptor<', 'tensor_adaptor', 'TensorAdaptorPrinter'),

    # Tensor descriptor (least specific - contained by many types)
    ('tensor_descriptor<', 'tensor_descriptor', 'TensorDescriptorPrinter'),

    # Distribution types
    ('tile_distribution<', 'tile_distribution', 'TileDistributionPrinter'),

    # Coordinate types
    ('tensor_adaptor_coordinate<', 'tensor_coordinate', 'TensorAdaptorCoordinatePrinter'),
    ('tensor_coordinate<', 'tensor_coordinate', 'TensorCoordinatePrinter'),

    # Container types
    ('array<', 'containers', 'ArrayPrinter'),
    ('tuple<', 'containers', 'TuplePrinter'),
    ('multi_index<', 'containers', 'ArrayPrinter'),  # multi_index is an alias for array
    ('thread_buffer<', 'containers', 'ThreadBufferPrinter'),
]


def get_printer_for_type(val: Any, type_str: str) -> Optional[Any]:
    """
    Get the appropriate pretty printer for a given GDB value and type string.

    This function uses a data-driven approach to dispatch printers based on type
    patterns. It checks patterns in order, returning the first match.

    Args:
        val: The GDB value to print
        type_str: The type string (from str(val.type))

    Returns:
        Printer instance if a match is found, None otherwise

    Example:
        >>> val = gdb.parse_and_eval("my_tuple")
        >>> type_str = str(val.type)
        >>> printer = get_printer_for_type(val, type_str)
        >>> if printer:
        ...     print(printer.to_string())
    """
    for pattern, module_name, class_name in PRINTER_TYPE_MAP:
        if pattern in type_str:
            try:
                # Import the printer module dynamically
                if module_name == 'containers':
                    from ..printers.containers import (
                        TuplePrinter, ArrayPrinter, ThreadBufferPrinter
                    )
                    printer_class = locals()[class_name]
                elif module_name == 'tile_distribution':
                    from ..printers.tile_distribution import (
                        TileWindowPrinter,
                        StaticDistributedTensorPrinter,
                        TileDistributionPrinter
                    )
                    printer_class = locals()[class_name]
                elif module_name == 'tensor_view':
                    from ..printers.tensor_view import TensorViewPrinter
                    printer_class = locals()[class_name]
                elif module_name == 'tensor_adaptor':
                    from ..printers.tensor_adaptor import TensorAdaptorPrinter
                    printer_class = locals()[class_name]
                elif module_name == 'tensor_descriptor':
                    from ..printers.tensor_descriptor import TensorDescriptorPrinter
                    printer_class = locals()[class_name]
                elif module_name == 'tensor_coordinate':
                    from ..printers.tensor_coordinate import (
                        TensorCoordinatePrinter,
                        TensorAdaptorCoordinatePrinter
                    )
                    printer_class = locals()[class_name]
                else:
                    continue

                return printer_class(val)

            except (ImportError, AttributeError, KeyError):
                # If we can't import the printer, continue to next pattern
                continue

    # No match found
    return None


def format_type_list():
    """
    Format the printer type map as a human-readable string.

    Useful for debugging and documentation.

    Returns:
        String representation of supported types
    """
    lines = ["Supported printer types (in dispatch order):"]
    for pattern, module, cls in PRINTER_TYPE_MAP:
        lines.append(f"  {pattern:50s} -> {module}.{cls}")
    return "\n".join(lines)
