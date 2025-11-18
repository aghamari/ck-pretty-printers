"""
Pretty printer for tile_scatter_gather types.

Handles:
- ck_tile::tile_scatter_gather<...>
"""

import gdb
import re
from ..core.base_printer import BaseCKTilePrinter


class TileScatterGatherPrinter(BaseCKTilePrinter):
    """Pretty-printer for tile_scatter_gather types."""

    def to_string(self):
        """Generate display string for tile_scatter_gather."""
        try:
            type_str = str(self.val.type)
            result = "tile_scatter_gather{\n"

            # Extract basic data type info (same as tile_window)
            data_type = self.extract_data_type(type_str)
            if data_type:
                result += f"  data_type: {data_type}\n"

            # Extract tile dimensions (same as tile_window)
            dims_match = re.findall(r'constant<(\d+)>', type_str)
            if dims_match and len(dims_match) >= 2:
                result += f"  tile_dims: [{dims_match[0]} x {dims_match[1]}]\n"

            # Extract memory operation enum if present
            mem_op_match = re.search(r'\(ck_tile::memory_operation_enum\)(\d+)', type_str)
            if mem_op_match:
                mem_op = mem_op_match.group(1)
                mem_ops = {'0': 'set', '1': 'atomic_add', '2': 'atomic_max'}
                result += f"  memory_operation: {mem_ops.get(mem_op, f'op_{mem_op}')}\n"

            # Since tile_scatter_gather stores distribution in its type (not as runtime member),
            # we need to extract and display it from the type string
            if 'tile_distribution<' in type_str:
                from .tile_distribution import TileDistributionPrinter

                # Create a mock value with the distribution type for the printer
                # This allows us to reuse TileDistributionPrinter's full formatting
                class MockDistribution:
                    def __init__(self, type_str):
                        self.type = type_str

                        # Extract the tile_distribution<...> portion
                        dist_start = type_str.find('tile_distribution<')
                        if dist_start != -1:
                            # Find the matching closing bracket
                            pos = dist_start + len('tile_distribution<')
                            bracket_count = 1
                            end = pos
                            while bracket_count > 0 and end < len(type_str):
                                if type_str[end] == '<':
                                    bracket_count += 1
                                elif type_str[end] == '>':
                                    bracket_count -= 1
                                end += 1

                            self.dist_type_str = type_str[dist_start:end]
                        else:
                            self.dist_type_str = type_str

                        # Extract tensor_adaptor portion
                        adaptor_start = self.dist_type_str.find('tensor_adaptor<')
                        if adaptor_start != -1:
                            pos = adaptor_start + len('tensor_adaptor<')
                            bracket_count = 1
                            end = pos
                            while bracket_count > 0 and end < len(self.dist_type_str):
                                if self.dist_type_str[end] == '<':
                                    bracket_count += 1
                                elif self.dist_type_str[end] == '>':
                                    bracket_count -= 1
                                end += 1
                            self.adaptor_type_str = self.dist_type_str[adaptor_start:end]
                        else:
                            self.adaptor_type_str = None

                        # Extract tensor_descriptor portion (look for the one that's part of ys_to_d_)
                        # In tile_distribution, tensor_descriptor comes after tensor_adaptor
                        desc_start = self.dist_type_str.rfind('tensor_descriptor<')  # Use rfind to get the last one
                        if desc_start != -1:
                            pos = desc_start + len('tensor_descriptor<')
                            bracket_count = 1
                            end = pos
                            while bracket_count > 0 and end < len(self.dist_type_str):
                                if self.dist_type_str[end] == '<':
                                    bracket_count += 1
                                elif self.dist_type_str[end] == '>':
                                    bracket_count -= 1
                                end += 1
                            self.desc_type_str = self.dist_type_str[desc_start:end]
                        else:
                            self.desc_type_str = None

                        # Mock ps_ys_to_xs_ and ys_to_d_ for TileDistributionPrinter
                        self._fields = {}

                    def __getitem__(self, key):
                        # Mock accessing members - TileDistributionPrinter will extract from type
                        if key == 'ps_ys_to_xs_':
                            # Create mock tensor_adaptor that can handle printer expectations
                            class MockAdaptor:
                                def __init__(self, type_str):
                                    self.type = type_str

                                def __getitem__(self, field_name):
                                    # Return None for any field access attempts
                                    # This allows extract_int_from_field to gracefully fail
                                    # and fall back to type string extraction
                                    raise gdb.error(f"No member named {field_name}")

                                def cast(self, target_type):
                                    # Return self for any cast attempts
                                    return self

                            # Also need to provide a mock type with fields method
                            class MockType:
                                def __init__(self, type_str):
                                    self._type_str = type_str

                                def __str__(self):
                                    return self._type_str

                                def fields(self):
                                    # Return empty list - no runtime fields in type aliases
                                    return []

                            # Return mock with the tensor_adaptor type
                            if self.adaptor_type_str:
                                adaptor = MockAdaptor(None)
                                adaptor.type = MockType(self.adaptor_type_str)
                                return adaptor
                            else:
                                # Fallback - return the full distribution type
                                adaptor = MockAdaptor(None)
                                adaptor.type = MockType(self.dist_type_str)
                                return adaptor
                        elif key == 'ys_to_d_':
                            # Create mock tensor_descriptor that can handle printer expectations
                            class MockDescriptor:
                                def __init__(self, type_str):
                                    self.type = type_str

                                def __getitem__(self, field_name):
                                    # Return None for any field access attempts
                                    # This allows extract_int_from_field to gracefully fail
                                    # and fall back to type string extraction
                                    raise gdb.error(f"No member named {field_name}")

                                def cast(self, target_type):
                                    # Return self for any cast attempts
                                    return self

                            # Use the same MockType class defined above
                            class MockType:
                                def __init__(self, type_str):
                                    self._type_str = type_str

                                def __str__(self):
                                    return self._type_str

                                def fields(self):
                                    # Return empty list - no runtime fields in type aliases
                                    return []

                            # Return mock with the tensor_descriptor type
                            if self.desc_type_str:
                                descriptor = MockDescriptor(None)
                                descriptor.type = MockType(self.desc_type_str)
                                return descriptor
                            else:
                                # Fallback - return the full distribution type
                                descriptor = MockDescriptor(None)
                                descriptor.type = MockType(self.dist_type_str)
                                return descriptor
                        else:
                            raise gdb.error(f"No member named {key}")

                mock_dist = MockDistribution(type_str)

                # Use the actual TileDistributionPrinter
                dist_printer = TileDistributionPrinter(mock_dist)
                dist_str = dist_printer.to_string()

                result += "\n  tile_distribution: "
                result += dist_str.replace('\n', '\n  ')
                result += "\n"

            # Access bottom_tensor_view - EXACT same approach as tile_window
            # tile_window does:
            #   bottom_view = self.val['bottom_tensor_view_']
            #   view_printer = TensorViewPrinter(bottom_view)
            # We do the same but with a mock since it's a type alias
            try:
                from .tensor_view import TensorViewPrinter

                # Extract the tensor_view type (first template parameter)
                if 'tensor_view<' in type_str:
                    view_start = type_str.find('tensor_view<')
                    if view_start != -1:
                        # Find the matching closing bracket
                        pos = view_start + len('tensor_view<')
                        bracket_count = 1
                        end = pos
                        while bracket_count > 0 and end < len(type_str):
                            if type_str[end] == '<':
                                bracket_count += 1
                            elif type_str[end] == '>':
                                bracket_count -= 1
                            end += 1

                        # Check if it has memory_operation_enum parameter
                        if type_str[end:end+30].startswith(', (ck_tile::memory_operation_enum)'):
                            mem_op_end = type_str.find('>', end + 30)
                            if mem_op_end != -1:
                                view_type_str = type_str[view_start:mem_op_end+1]
                            else:
                                view_type_str = type_str[view_start:end]
                        else:
                            view_type_str = type_str[view_start:end]

                        # Create a mock bottom_tensor_view that provides the members TensorViewPrinter expects
                        class MockBottomTensorView:
                            def __init__(self, type_str):
                                self.type = type_str
                                self._parse_components(type_str)

                            def _parse_components(self, type_str):
                                """Parse out descriptor and buffer_view from the type"""
                                # Extract descriptor type
                                self._desc_type = None
                                desc_start = type_str.find('tensor_descriptor<')
                                if desc_start != -1:
                                    pos = desc_start + len('tensor_descriptor<')
                                    bracket_count = 1
                                    end = pos
                                    while bracket_count > 0 and end < len(type_str):
                                        if type_str[end] == '<':
                                            bracket_count += 1
                                        elif type_str[end] == '>':
                                            bracket_count -= 1
                                        end += 1
                                    self._desc_type = type_str[desc_start:end]

                                # Extract buffer_view type
                                self._buf_type = None
                                buf_start = type_str.find('buffer_view<')
                                if buf_start != -1:
                                    pos = buf_start + len('buffer_view<')
                                    bracket_count = 1
                                    end = pos
                                    while bracket_count > 0 and end < len(type_str):
                                        if type_str[end] == '<':
                                            bracket_count += 1
                                        elif type_str[end] == '>':
                                            bracket_count -= 1
                                        end += 1
                                    self._buf_type = type_str[buf_start:end]

                            def __getitem__(self, field_name):
                                # Provide mock desc_ and buf_view_ that TensorViewPrinter expects
                                if field_name == 'desc_' and self._desc_type:
                                    # Return a mock descriptor that provides the fields TensorDescriptorPrinter needs
                                    class MockDescriptor:
                                        def __init__(self, type_str):
                                            self.type = type_str
                                            self._analyze_type(type_str)

                                        def _analyze_type(self, type_str):
                                            """Analyze the descriptor type to extract info"""
                                            self._has_transforms = ('embed<' in type_str or
                                                                   'pass_through<' in type_str or
                                                                   'unmerge<' in type_str or
                                                                   'merge<' in type_str)
                                            # Count transforms
                                            self._transform_count = 0
                                            for t in ['embed<', 'pass_through<', 'unmerge<', 'merge<']:
                                                self._transform_count += type_str.count(t)

                                        def __getitem__(self, field_name):
                                            # Provide mock fields that TensorDescriptorPrinter expects
                                            if field_name == 'element_space_size_':
                                                # Return a mock constant - any non-None value prevents UNINITIALIZED
                                                class MockField:
                                                    def __init__(self):
                                                        self.type = 'ck_tile::constant<1>'
                                                return MockField()
                                            elif field_name == 'ntransform_':
                                                if self._has_transforms:
                                                    class MockField:
                                                        def __init__(self, val):
                                                            self.type = f'ck_tile::constant<{val}>'
                                                            self._val = val
                                                        def __int__(self):
                                                            return self._val
                                                    return MockField(self._transform_count)
                                                else:
                                                    return None
                                            elif field_name in ['ndim_hidden_', 'ndim_top_']:
                                                # Return something to prevent UNINITIALIZED
                                                class MockField:
                                                    def __init__(self):
                                                        self.type = 'ck_tile::constant<1>'
                                                return MockField()
                                            else:
                                                # For other fields, return None or raise error
                                                raise gdb.error(f"No member named {field_name}")

                                    return MockDescriptor(self._desc_type)

                                elif field_name == 'buf_view_' and self._buf_type:
                                    # Return a mock buffer_view
                                    class MockBufferView:
                                        def __init__(self, type_str):
                                            self.type = type_str

                                    return MockBufferView(self._buf_type)

                                else:
                                    raise gdb.error(f"No member named {field_name}")

                        bottom_view = MockBottomTensorView(view_type_str)

                        # Use tensor_view printer - EXACTLY like tile_window does
                        view_printer = TensorViewPrinter(bottom_view)
                        view_str = view_printer.to_string()

                        result += "\n  bottom_tensor_view_: "
                        result += view_str.replace('\n', '\n  ')
                        result += "\n"

            except:
                pass  # Same as tile_window - silently ignore errors

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tile_scatter_gather")

    def children(self):
        """Return child elements for hierarchical display."""
        # tile_scatter_gather doesn't have runtime members we can access
        # Everything is in the type template parameters
        return []

    def display_hint(self):
        """Return display hint for GDB."""
        return 'map'