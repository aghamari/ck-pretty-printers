"""
Base class for all CK-Tile pretty printers.
Provides common utility methods shared across all printers.
"""

import re
from ..utils.constants import MAX_SANE_VALUE


class BaseCKTilePrinter:
    """Base class for CK-Tile pretty printers."""

    def __init__(self, val):
        """
        Initialize the printer.

        Args:
            val: GDB value to print
        """
        self.val = val

    def extract_int_from_field(self, obj, field_name):
        """
        Safely extract integer from a field.

        Handles:
        - ck_tile::constant<N> types
        - Regular integer types
        - Fields with 'value' member

        Args:
            obj: GDB object containing the field
            field_name: Name of the field to extract

        Returns:
            Integer value, or None if extraction fails or value is unreasonable
        """
        try:
            field = obj[field_name]
            field_type_str = str(field.type)

            # Check if it's a constant<> type first
            if 'constant<' in field_type_str:
                # Extract the constant value from the type
                const_match = re.search(r'constant<(\d+)[lL]?>', field_type_str)
                if const_match:
                    val = int(const_match.group(1))
                    if abs(val) > MAX_SANE_VALUE:
                        return None
                    return val

            # Try direct conversion for regular types
            try:
                val = int(field)
                if abs(val) > MAX_SANE_VALUE:
                    return None
                return val
            except:
                # If that fails, try accessing value member
                try:
                    val = int(field['value'])
                    if abs(val) > MAX_SANE_VALUE:
                        return None
                    return val
                except:
                    pass

            return None
        except Exception:
            # Silently return None on any error
            return None

    def safe_extract(self, extraction_func, default=None, error_context=""):
        """
        Safely execute an extraction function with error handling.

        Args:
            extraction_func: Function to execute
            default: Default value to return on error
            error_context: Description of what's being extracted (for debugging)

        Returns:
            Result of extraction_func, or default on error
        """
        try:
            return extraction_func()
        except Exception as e:
            # Could log to GDB here if needed
            # gdb.write(f"Warning: {error_context} failed: {e}\n", gdb.STDERR)
            return default

    def is_uninitialized(self, *field_values):
        """
        Check if all field values indicate an uninitialized object.

        Args:
            *field_values: Field values to check (typically integers)

        Returns:
            True if object appears uninitialized, False otherwise
        """
        # If all values are None, object is likely uninitialized
        if all(v is None for v in field_values):
            return True

        # If any value exceeds sanity check, object is likely uninitialized
        for val in field_values:
            if val is not None and abs(val) > MAX_SANE_VALUE:
                return True

        return False

    def format_error(self, error_msg, context=""):
        """
        Format an error message for display.

        Args:
            error_msg: The error message
            context: Additional context about where the error occurred

        Returns:
            Formatted error string
        """
        if context:
            return f"{{error: {context}: {error_msg}}}"
        return f"{{error: {error_msg}}}"

    def extract_data_type(self, type_str):
        """
        Extract and format the data type from a type string.

        Args:
            type_str: Full type string

        Returns:
            Human-readable data type string, or None if not found
        """
        if '_Float16' in type_str:
            return "float16"
        elif 'float' in type_str:
            return "float"
        elif 'double' in type_str:
            return "double"
        elif 'int' in type_str:
            return "int"
        return None

    def to_string(self):
        """
        Convert the GDB value to a string representation.
        This should be overridden by subclasses.

        Returns:
            String representation of the value
        """
        raise NotImplementedError("Subclasses must implement to_string()")
