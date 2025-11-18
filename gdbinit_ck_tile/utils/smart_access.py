"""
Smart member access utility for CK-Tile pretty printers.

Based on comprehensive analysis of CK-Tile types, this module provides
intelligent member access that uses the right strategy for each member type.

Member Categories:
1. TYPE_ONLY: All information encoded in template parameters (e.g., desc_ in tensor_view)
2. RUNTIME_CRITICAL: Must have runtime access, useless without it (e.g., coordinate data)
3. RUNTIME_PREFERRED: Best with runtime, but can show structure from type (e.g., transforms)
"""

from typing import Tuple, Optional, Any

try:
    import gdb
except ImportError:
    # For testing outside GDB
    gdb = None


class SmartMemberAccess:
    """
    Provides intelligent member access based on the nature of the member.
    """

    # Members that are pure type carriers with no runtime state
    TYPE_ONLY_MEMBERS = {
        'desc_',  # tensor_view's descriptor - all info in type
        'element_space_size_' # when it's a compile-time constant
    }

    # Members that are useless without runtime access
    RUNTIME_CRITICAL_MEMBERS = {
        'idx_hidden_',  # Coordinate values - the actual data
        'data',  # Array/buffer data
        'p_data_',  # Buffer pointer
        'buffer_size_',  # Runtime buffer size
        'thread_buf_',  # Thread buffer data
        'element',  # Tuple element values
        'cached_buf_res_',  # Cached buffer resource
        'invalid_element_value_'  # Invalid element value
    }

    # Members that benefit from runtime but can show structure from type
    RUNTIME_PREFERRED_MEMBERS = {
        'transforms_',  # Transform parameters best from runtime
        'ps_ys_to_xs_',  # Tensor adaptor
        'ys_to_d_',  # Tensor descriptor
        'bottom_tensor_view_',  # Tensor view
        'buf_view_',  # Buffer view (has runtime pointer but structure from type)
        'tile_dstr_',  # Tile distribution
        'window_lengths_',  # Window dimensions
        'window_origin_',  # Window position
        'pre_computed_coords_',  # Cached coordinates
        'up_lengths_',  # Transform lengths
        'low_lengths_',  # Transform lengths
        'left_pad_length_',  # Padding values
        'right_pad_length_',  # Padding values
        'coefficients_',  # Embed coefficients
        'low_lengths_magic_divisor_'  # Magic divisors
    }

    @staticmethod
    def get_member_category(member_name: str) -> str:
        """
        Determine the access category for a member.

        Returns:
            'type_only': Extract from type string only
            'runtime_critical': Must have runtime access
            'runtime_preferred': Try runtime first, fallback to type
        """
        if member_name in SmartMemberAccess.TYPE_ONLY_MEMBERS:
            return 'type_only'
        elif member_name in SmartMemberAccess.RUNTIME_CRITICAL_MEMBERS:
            return 'runtime_critical'
        elif member_name in SmartMemberAccess.RUNTIME_PREFERRED_MEMBERS:
            return 'runtime_preferred'
        else:
            # Default to runtime_preferred for unknown members
            return 'runtime_preferred'

    @staticmethod
    def smart_access(val, member_name: str) -> Tuple[Optional[Any], bool, str]:
        """
        Smart member access that uses the right strategy based on member type.

        Args:
            val: GDB value object (or mock for testing)
            member_name: Name of member to access

        Returns:
            Tuple of (value_or_none, success, access_method)
            - value_or_none: The member value or None if failed
            - success: Whether access was successful
            - access_method: 'runtime', 'type', or 'failed'
        """
        category = SmartMemberAccess.get_member_category(member_name)

        if category == 'type_only':
            # For type-only members, extract from type string
            return SmartMemberAccess._extract_from_type(val, member_name)

        elif category == 'runtime_critical':
            # For runtime-critical members, only try runtime
            return SmartMemberAccess._try_runtime_only(val, member_name)

        else:  # runtime_preferred
            # Try runtime first, fallback to type
            return SmartMemberAccess._try_runtime_with_fallback(val, member_name)

    @staticmethod
    def _try_runtime_only(val, member_name: str) -> Tuple[Optional[Any], bool, str]:
        """Try runtime access only - fail if not available."""
        if gdb is None:
            return (None, False, 'failed')
        try:
            member_val = val[member_name]
            return (member_val, True, 'runtime')
        except Exception:
            return (None, False, 'failed')

    @staticmethod
    def _try_runtime_with_fallback(val, member_name: str) -> Tuple[Optional[Any], bool, str]:
        """Try runtime first, fallback to type extraction."""
        if gdb is not None:
            # First try runtime
            try:
                member_val = val[member_name]
                return (member_val, True, 'runtime')
            except Exception:
                pass
        # Fallback to type extraction
        return SmartMemberAccess._extract_from_type(val, member_name)

    @staticmethod
    def _extract_from_type(val, member_name: str) -> Tuple[Optional[Any], bool, str]:
        """
        Extract member information from type string.

        For members like 'desc_' in tensor_view, all information is in the type.
        This creates a mock object that can be passed to the appropriate printer.
        """
        type_str = str(val.type) if hasattr(val, 'type') else str(val)

        if member_name == 'desc_':
            # For tensor_view's desc_, extract descriptor type from tensor_view type
            # tensor_view<..., tensor_descriptor<...>, ...>
            desc_type = SmartMemberAccess._extract_descriptor_type(type_str)
            if desc_type:
                # Create a mock descriptor that TensorDescriptorPrinter can handle
                mock_desc = SmartMemberAccess._create_mock_descriptor(desc_type)
                return (mock_desc, True, 'type')

        elif member_name in ['ps_ys_to_xs_', 'ys_to_d_']:
            # For tile_distribution members, extract from type
            member_type = SmartMemberAccess._extract_member_type(type_str, member_name)
            if member_type:
                if 'tensor_adaptor' in member_type:
                    mock_obj = SmartMemberAccess._create_mock_adaptor(member_type)
                elif 'tensor_descriptor' in member_type:
                    mock_obj = SmartMemberAccess._create_mock_descriptor(member_type)
                else:
                    mock_obj = None
                if mock_obj:
                    return (mock_obj, True, 'type')

        return (None, False, 'failed')

    @staticmethod
    def _extract_descriptor_type(tensor_view_type: str) -> Optional[str]:
        """Extract descriptor type from tensor_view type string."""
        # tensor_view has format: tensor_view<BufferView, TensorDesc, MemOp>
        # We need to extract the TensorDesc part
        import re

        # Find tensor_descriptor within the tensor_view template params
        # This handles nested template parameters properly
        start = tensor_view_type.find('tensor_descriptor<')
        if start == -1:
            return None

        # Count brackets to find matching closing >
        count = 1
        i = start + len('tensor_descriptor<')
        while i < len(tensor_view_type) and count > 0:
            if tensor_view_type[i] == '<':
                count += 1
            elif tensor_view_type[i] == '>':
                count -= 1
            i += 1

        if count == 0:
            return tensor_view_type[start:i]
        return None

    @staticmethod
    def _extract_member_type(type_str: str, member_name: str) -> Optional[str]:
        """Extract specific member type from a complex type string."""
        # This is simplified - real implementation would parse more carefully
        if 'tensor_adaptor' in type_str or 'tensor_descriptor' in type_str:
            return type_str  # Return full type for now
        return None

    @staticmethod
    def _create_mock_descriptor(desc_type: str):
        """Create a mock descriptor object that can be used with TensorDescriptorPrinter."""
        import re

        class MockDescriptor:
            def __init__(self, type_str):
                self.type_str = type_str
                self.type = self  # Mock type object

                # Parse critical values from type to prevent [UNINITIALIZED]
                self._parse_values()

            def __str__(self):
                return self.type_str

            def fields(self):
                """Mock fields method for compatibility."""
                return []  # No base class fields for mock

            def _parse_values(self):
                """Parse important values from type string."""
                # Count transforms
                transform_count = self.type_str.count('embed') + self.type_str.count('pad') + \
                                self.type_str.count('merge') + self.type_str.count('unmerge') + \
                                self.type_str.count('pass_through')
                self._ntransform = transform_count if transform_count > 0 else 1

                # Count dimensions from sequences
                hidden_dims = len(re.findall(r'sequence<[\d,\s-]+>', self.type_str))
                self._ndim_hidden = max(1, hidden_dims - 2)  # Estimate
                self._ndim_top = 2  # Common default

                # Extract element space size if present
                elem_match = re.search(r'ck_tile::constant<(\d+)[lL]?>', self.type_str)
                if elem_match:
                    self._element_space_size = int(elem_match.group(1))
                else:
                    self._element_space_size = 1  # Default to prevent uninitialized

            def __getitem__(self, field_name):
                # Provide minimal values to prevent [UNINITIALIZED]
                class MockIntField:
                    """Mock field that behaves like a GDB constant field."""
                    def __init__(self, value):
                        self._value = value
                        # Mimic ck_tile::constant<N> type
                        self.type = type('MockType', (), {
                            '__str__': lambda s: f'ck_tile::constant<{value}>',
                            'name': f'ck_tile::constant<{value}>'
                        })()

                    def __int__(self):
                        return self._value

                    def __getitem__(self, key):
                        # For accessing 'value' member if needed
                        if key == 'value':
                            return self._value
                        return None

                if field_name == 'element_space_size_':
                    return MockIntField(self._element_space_size)
                elif field_name == 'ntransform_':
                    return MockIntField(self._ntransform)
                elif field_name == 'ndim_hidden_':
                    return MockIntField(self._ndim_hidden)
                elif field_name == 'ndim_top_':
                    return MockIntField(self._ndim_top)
                # Return None for other fields
                return None

        return MockDescriptor(desc_type)

    @staticmethod
    def _create_mock_adaptor(adaptor_type: str):
        """Create a mock adaptor object that can be used with TensorAdaptorPrinter."""
        class MockAdaptor:
            def __init__(self, type_str):
                self.type_str = type_str
                self.type = self

            def __str__(self):
                return self.type_str

            def __getitem__(self, field_name):
                return None

        return MockAdaptor(adaptor_type)


def format_access_indicator(access_method: str) -> str:
    """
    Format an indicator showing how the value was accessed.

    Args:
        access_method: 'runtime', 'type', or 'failed'

    Returns:
        Formatted indicator string
    """
    if access_method == 'type':
        return " [from type]"
    elif access_method == 'failed':
        return " [not accessible]"
    else:
        return ""  # No indicator for successful runtime access