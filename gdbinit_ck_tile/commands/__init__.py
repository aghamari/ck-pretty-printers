"""
Custom GDB commands for CK-Tile debugging.
"""

from .mermaid_generator import MermaidCommand, mermaid

# Import type-print command when in GDB context
try:
    import gdb
    from .print_type_only import TypePrintCommand
    __all__ = ['MermaidCommand', 'mermaid', 'TypePrintCommand']
except ImportError:
    # Not in GDB context
    __all__ = ['MermaidCommand', 'mermaid']