"""
GDB command to print type-only variables that have no runtime storage.

Usage: type-print variable_name
"""

import gdb
import re


class TypePrintCommand(gdb.Command):
    """Print a type-only variable using its type information."""

    def __init__(self):
        super(TypePrintCommand, self).__init__("type-print", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: type-print variable_name")
            return

        var_name = arg.strip()

        try:
            # Get the type of the variable
            type_str = gdb.execute(f"whatis {var_name}", to_string=True)

            # Extract the actual type after "type = "
            if "type = " in type_str:
                type_str = type_str.split("type = ", 1)[1].strip()

                # Check if it's a known type alias or type with no runtime storage
                if "::BottomTensorView" in type_str:
                    # Extract the tensor_view type
                    self._print_tensor_view_from_type(type_str)
                elif "::TensorDesc" in type_str:
                    # Extract the tensor_descriptor type
                    self._print_tensor_descriptor_from_type(type_str)
                elif "::BufferView" in type_str:
                    # Extract buffer_view information
                    self._print_buffer_view_from_type(type_str)
                elif "::WindowLengths" in type_str:
                    # Extract window lengths (usually a tuple of constants)
                    self._print_window_lengths_from_type(type_str)
                elif "::TileDistribution" in type_str or "::TileDstr" in type_str:
                    # Extract tile distribution
                    self._print_tile_distribution_from_type(type_str)
                elif "static_distributed_tensor<" in type_str:
                    # Handle static_distributed_tensor
                    self._print_static_distributed_tensor_from_type(type_str)
                elif "tile_distribution<" in type_str:
                    # Handle standalone tile_distribution
                    self._print_tile_distribution_from_type(type_str)
                elif "tensor_view<" in type_str:
                    # Handle standalone tensor_view
                    self._print_tensor_view_from_type(type_str)
                elif "tensor_descriptor<" in type_str:
                    # Handle standalone tensor_descriptor
                    self._print_tensor_descriptor_from_type(type_str)
                else:
                    print(f"Type: {type_str}")
                    print("Note: Use type-print for type aliases with no runtime storage")

        except Exception as e:
            print(f"Error getting type for {var_name}: {e}")

    def _print_tensor_view_from_type(self, type_str):
        """Extract and print tensor_view information from a type string."""
        # Import the printer
        from gdbinit_ck_tile.printers.tensor_view import TensorViewPrinter
        from gdbinit_ck_tile.utils.smart_access import SmartMemberAccess

        # Create a mock value with this type
        class MockValue:
            def __init__(self, t):
                self.type = t

            def __getitem__(self, key):
                raise gdb.error("No runtime storage")

        mock = MockValue(type_str)

        # Use the tensor_view printer
        printer = TensorViewPrinter(mock)
        result = printer.to_string()

        print(result)

    def _print_tensor_descriptor_from_type(self, type_str):
        """Extract and print tensor_descriptor information from a type string."""
        # Import the printer and smart access
        from gdbinit_ck_tile.printers.tensor_descriptor import TensorDescriptorPrinter
        from gdbinit_ck_tile.utils.smart_access import SmartMemberAccess

        # Extract the actual tensor_descriptor type
        # For tensor_view<...>::TensorDesc, we need to find the descriptor within
        if 'tensor_descriptor<' in type_str:
            start = type_str.find('tensor_descriptor<')
            # Find matching closing bracket
            count = 1
            i = start + len('tensor_descriptor<')
            while i < len(type_str) and count > 0:
                if type_str[i] == '<':
                    count += 1
                elif type_str[i] == '>':
                    count -= 1
                i += 1

            if count == 0:
                desc_type = type_str[start:i]

                # Use the smart access mock descriptor creator
                mock = SmartMemberAccess._create_mock_descriptor(desc_type)

                # Use the tensor_descriptor printer
                printer = TensorDescriptorPrinter(mock)
                result = printer.to_string()

                # Add [from type] indicator since this is all from type
                result = result.replace("tensor_descriptor{", "tensor_descriptor [from type] {")
                print(result)
            else:
                print(f"Type: {type_str}")
                print("Could not extract tensor_descriptor type")
        else:
            print(f"Type: {type_str}")
            print("Note: TensorDesc alias but no tensor_descriptor found in type")

    def _print_buffer_view_from_type(self, type_str):
        """Print buffer_view information from type."""
        print(f"buffer_view type alias:")
        if 'address_space_enum)1' in type_str:
            print("  address_space: global")
        elif 'address_space_enum)3' in type_str:
            print("  address_space: lds")

        # Extract data type
        if '__bf16' in type_str:
            print("  data_type: bfloat16")
        elif '_Float16' in type_str:
            print("  data_type: float16")
        elif 'float' in type_str:
            print("  data_type: float")

    def _print_window_lengths_from_type(self, type_str):
        """Print window lengths from type."""
        print(f"WindowLengths type alias")
        # Usually a tuple of constants
        if 'tuple<' in type_str:
            print("  (tuple of window dimension sizes)")

    def _print_tile_distribution_from_type(self, type_str):
        """Print tile distribution from type."""
        from gdbinit_ck_tile.printers.tile_distribution import TileDistributionPrinter

        # Create mock and use printer
        class MockValue:
            def __init__(self, t):
                self.type = t

            def __getitem__(self, key):
                raise gdb.error("No runtime storage")

        mock = MockValue(type_str)
        printer = TileDistributionPrinter(mock)
        result = printer.to_string()
        print(result)

    def _print_static_distributed_tensor_from_type(self, type_str):
        """Print static_distributed_tensor from type."""
        from gdbinit_ck_tile.printers.tile_distribution import StaticDistributedTensorPrinter

        # Create mock value
        class MockValue:
            def __init__(self, t):
                self.type = t

            def __getitem__(self, key):
                raise gdb.error("No runtime storage")

        mock = MockValue(type_str)

        # Use the static distributed tensor printer
        printer = StaticDistributedTensorPrinter(mock)
        result = printer.to_string()

        # Add [from type] indicator since this is all from type
        result = result.replace("static_distributed_tensor{", "static_distributed_tensor [from type] {")
        print(result)


# Register the command
TypePrintCommand()
print("Registered 'type-print' command for type-only variables")