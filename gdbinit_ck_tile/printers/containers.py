"""Pretty printers for CK-Tile core containers (tuple, array, etc.)"""

import re
from ..core.base_printer import BaseCKTilePrinter
from ..utils.tuple_extractor import extract_tuple_elements
from ..utils.constants import DEFAULT_MAX_DIMS


class TuplePrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::tuple<...>"""

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Extract tuple elements using existing utility
            elements = extract_tuple_elements(self.val)

            num_elements = len(elements)

            # Handle empty tuple
            if num_elements == 0:
                return "tuple<0 elements> {}"

            # Build result
            plural = "element" if num_elements == 1 else "elements"
            result = f"tuple<{num_elements} {plural}> {{\n"

            for i, elem in enumerate(elements):
                result += f"  [{i}]: "

                # Try to use appropriate pretty printer for the element
                elem_str = self._format_element(elem, i)

                # Indent multi-line elements
                elem_str_indented = elem_str.replace('\n', '\n    ')
                result += elem_str_indented
                result += "\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tuple")

    def _format_element(self, elem, index):
        """
        Format a single tuple element, using appropriate printer if available.

        Args:
            elem: The element (can be int, float, or GDB value)
            index: Index of the element in the tuple

        Returns:
            Formatted string representation
        """
        # If it's a simple Python type (int, float), just display it
        if isinstance(elem, (int, float)):
            return str(elem)

        # It's a GDB value - try to use a pretty printer
        try:
            elem_type_str = str(elem.type)

            # Try to find and use the appropriate pretty printer
            printer = self._get_printer_for_type(elem, elem_type_str)

            if printer:
                return printer.to_string()
            else:
                # No pretty printer available, use default GDB formatting
                return str(elem)

        except Exception as e:
            # If anything fails, fall back to simple string conversion
            return f"<error formatting element {index}: {e}>"

    def _get_printer_for_type(self, val, type_str):
        """
        Get the appropriate pretty printer for a given type.

        This avoids code duplication by reusing existing printers.
        Uses the centralized printer dispatcher.

        Args:
            val: GDB value
            type_str: Type string

        Returns:
            Printer instance or None
        """
        from ..utils.printer_dispatcher import get_printer_for_type
        return get_printer_for_type(val, type_str)


class ArrayPrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::array<T, N> and multi_index<N>"""

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Determine if it's multi_index or array
            is_multi_index = 'multi_index' in type_str

            # Extract N (array size) from type
            n = self._extract_array_size(type_str)

            if n is None:
                return self.format_error("Could not determine array size", "array")

            # Extract data type
            data_type = self._extract_element_type(type_str)

            # Read elements from data member
            elements = self._extract_array_data(n)

            # Format output
            if is_multi_index:
                return f"multi_index<{n}> = {elements}"
            else:
                return f"array<{data_type}, {n}> = {elements}"

        except Exception as e:
            return self.format_error(str(e), "array")

    def _extract_array_size(self, type_str):
        """Extract N from array<T, N> or multi_index<N>"""
        # Try multi_index<N> first
        match = re.search(r'multi_index<(\d+)>', type_str)
        if match:
            return int(match.group(1))

        # Try array<T, N>
        match = re.search(r'array<[^,]+,\s*(\d+)[lL]?>', type_str)
        if match:
            return int(match.group(1))

        return None

    def _extract_element_type(self, type_str):
        """Extract T from array<T, N>"""
        match = re.search(r'array<([^,]+),', type_str)
        if match:
            elem_type = match.group(1).strip()
            # Simplify common types
            return self.extract_data_type(elem_type) or elem_type
        return "unknown"

    def _extract_array_data(self, n):
        """
        Extract array elements from data member.

        Args:
            n: Number of elements

        Returns:
            List representation of array, with truncation for large arrays
        """
        try:
            data = self.val['data']
            elements = []

            # Limit how many elements we read
            max_to_read = min(n, DEFAULT_MAX_DIMS)

            for i in range(max_to_read):
                try:
                    val = int(data[i])
                    elements.append(val)
                except:
                    # Try float
                    try:
                        val = float(data[i])
                        elements.append(val)
                    except:
                        # Give up, just use string
                        elements.append(str(data[i]))

            # Add truncation indicator if needed
            if n > max_to_read:
                return f"[{', '.join(map(str, elements))}, ... ({n} total)]"
            else:
                return f"[{', '.join(map(str, elements))}]"

        except Exception as e:
            return f"<error reading data: {e}>"


class ThreadBufferPrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::thread_buffer<T, N>"""

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Extract size from type
            match = re.search(r'thread_buffer<[^,]+,\s*(\d+)', type_str)
            if not match:
                return self.format_error("Could not parse thread_buffer type", "thread_buffer")

            size = int(match.group(1))

            # Extract data type
            data_type_match = re.search(r'thread_buffer<([^,]+),', type_str)
            data_type = "unknown"
            if data_type_match:
                dt = data_type_match.group(1).strip()
                data_type = self.extract_data_type(dt) or dt

            result = f"thread_buffer<{data_type}, {size}> {{\n"
            result += f"  size: {size}\n"

            # Try to show first few elements
            try:
                data = self.val['data']
                elements = []
                max_display = min(10, size)  # Show first 10 elements max

                for i in range(max_display):
                    try:
                        val = data[i]
                        elements.append(str(val))
                    except:
                        break

                if elements:
                    result += f"  data (first {len(elements)}): [{', '.join(elements)}"
                    if size > max_display:
                        result += f", ... ({size} total)"
                    result += "]\n"

            except:
                result += "  data: <not accessible>\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "thread_buffer")
