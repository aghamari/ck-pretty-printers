"""
Generate Mermaid diagrams for tensor_descriptor and tensor_adaptor dimension transformations.

This module provides commands to visualize the dimension flow through transforms
as a Mermaid flowchart diagram.
"""

import gdb
import re
from ..core.transform_mixin import TransformMixin
from ..utils.constants import TRANSFORM_PATTERNS
from ..utils.pretty_printer_parser import PrettyPrinterOutputParser
from ..utils.value_access import ValueAccessStrategy
from ..utils.mermaid_builder import MermaidDiagramBuilder


class MermaidGenerator(TransformMixin):
    """Generate Mermaid diagrams from tensor types."""

    def __init__(self, val, expression=None):
        self.val = val
        self.type_str = str(val.type)
        self.expression = expression  # Original expression passed to mermaid command

    def _get_pretty_printer_output(self):
        """Get pretty printer output for the expression.

        Returns:
            String with pretty printer output (without $N = prefix) or None if failed
        """
        if not self.expression:
            return None
        try:
            import gdb
            output = gdb.execute(f"p {self.expression}", to_string=True)
            if ' = ' in output:
                return output.split(' = ', 1)[1]
            return output
        except:
            return None

    def generate_mermaid(self):
        """
        Generate Mermaid diagram code for tensor_descriptor or tensor_adaptor.

        Returns:
            String containing Mermaid flowchart code
        """
        # Get the actual type, not the full string with all nested types
        # First, try to get the pretty printer output to see what it identifies as
        output = self._get_pretty_printer_output()
        if output:
            # Check the first line of the pretty printer output
            if 'tensor_descriptor{' in output:
                return self._generate_descriptor_mermaid()
            elif 'tensor_adaptor{' in output:
                return self._generate_adaptor_mermaid()

        # Fallback to type string analysis
        # But be more careful - check what comes first after ck_tile::
        import re

        # Look for the first occurrence of either type after ck_tile::
        descriptor_match = re.search(r'ck_tile::tensor_descriptor', self.type_str)
        adaptor_match = re.search(r'ck_tile::tensor_adaptor', self.type_str)

        if descriptor_match and adaptor_match:
            # Both found - use the one that appears first
            if descriptor_match.start() < adaptor_match.start():
                return self._generate_descriptor_mermaid()
            else:
                return self._generate_adaptor_mermaid()
        elif descriptor_match:
            return self._generate_descriptor_mermaid()
        elif adaptor_match:
            return self._generate_adaptor_mermaid()
        else:
            return "Error: Not a tensor_descriptor or tensor_adaptor"

    def _generate_descriptor_mermaid(self):
        """Generate Mermaid diagram for tensor_descriptor."""

        # Extract transform information
        transforms, lower_dims, upper_dims = self.extract_transform_info_from_type(
            self.type_str, 'tensor_descriptor'
        )

        if not transforms:
            # Fallback to pretty printer output when type extraction fails
            if self.expression:
                result = self._generate_from_pretty_printer()
                if result:
                    # Change the title to indicate it's a tensor_descriptor
                    result = result.replace("Tensor Adaptor Transform Flow", "Tensor Descriptor Transform Flow")
                    return result
            return "Error: No transforms found"

        # Extract bottom and top dimension IDs
        bottom_dims, top_dims = self._extract_descriptor_bottom_top_dims()

        # Use the unified diagram builder
        builder = MermaidDiagramBuilder()
        return builder.build(
            transforms=transforms,
            lower_dims=lower_dims,
            upper_dims=upper_dims,
            bottom_dims=bottom_dims,
            top_dims=top_dims,
            title="Tensor Descriptor Transform Flow"
        )

    def _generate_adaptor_mermaid(self):
        """Generate Mermaid diagram for tensor_adaptor."""

        # Use generic value access strategy instead of hardcoded names
        access_method = ValueAccessStrategy.get_access_method(self.val, self.expression)

        if access_method == 'pretty_printer':
            # Get everything from pretty printer output when direct access doesn't work
            result = self._generate_from_pretty_printer()
            if result:
                return result

        # Extract transform information from type
        transforms, lower_dims_orig, upper_dims_orig = self.extract_transform_info_from_type(
            self.type_str, 'tensor_adaptor'
        )

        if not transforms:
            return "Error: No transforms found"

        # Extract bottom and top dimension IDs from the type
        bottom_dims, top_dims = self._extract_adaptor_bottom_top_dims()

        # Check if dimensions are empty - if so, try to get them from pretty printer output
        if all(not dims for dims in lower_dims_orig) and all(not dims for dims in upper_dims_orig):
            # Try to get dimensions from the pretty printer output via 'p' command
            lower_dims, upper_dims = self._get_dimensions_from_pretty_printer(transforms)
            if not lower_dims:
                # Fall back to original empty dimensions
                lower_dims = lower_dims_orig
                upper_dims = upper_dims_orig
        else:
            lower_dims = lower_dims_orig
            upper_dims = upper_dims_orig

        # If bottom_dims looks incomplete (e.g., only [0] when we have replicate with no lower),
        # try to get the full bottom_dims from pretty printer
        if bottom_dims and len(bottom_dims) < 2 and self.expression:
            output = self._get_pretty_printer_output()
            if output:
                # Use the existing parser to extract dimensions
                parsed_bottom, parsed_top = PrettyPrinterOutputParser.parse_bottom_top_dims(output)

                if len(parsed_bottom) > len(bottom_dims):
                    bottom_dims = parsed_bottom
                if parsed_top:
                    top_dims = parsed_top

        # Use the unified diagram builder
        builder = MermaidDiagramBuilder()
        return builder.build(
            transforms=transforms,
            lower_dims=lower_dims,
            upper_dims=upper_dims,
            bottom_dims=bottom_dims,
            top_dims=top_dims,
            title="Tensor Adaptor Transform Flow"
        )

    def _extract_descriptor_bottom_top_dims(self):
        """Extract bottom and top dimension IDs for tensor_descriptor."""
        # Use the unified method from TransformMixin
        bottom_dims, top_dims = self.extract_bottom_top_dims(self.type_str)

        # For tensor_descriptor, if we didn't find bottom dims, default to [0]
        if not bottom_dims and 'tensor_descriptor' in self.type_str:
            bottom_dims = [0]

        return bottom_dims, top_dims

    def _extract_adaptor_bottom_top_dims(self):
        """Extract bottom and top dimension IDs for tensor_adaptor."""
        # Use the unified method from TransformMixin
        return self.extract_bottom_top_dims(self.type_str)

    def _generate_from_pretty_printer(self):
        """
        Generate the complete Mermaid diagram from pretty printer output.
        This is needed for ps_ys_to_xs_ and similar cases.
        """
        try:
            output = self._get_pretty_printer_output()
            if not output:
                return None

            # Use the new parser to extract all information
            parsed_data = PrettyPrinterOutputParser.parse_complete(output)

            transforms = [t['name'] for t in parsed_data['transforms']]
            lower_dims = [t['lower'] for t in parsed_data['transforms']]
            upper_dims = [t['upper'] for t in parsed_data['transforms']]
            bottom_dims = parsed_data['bottom_dims']
            top_dims = parsed_data['top_dims']

            if not transforms:
                return None

            # Use the unified diagram builder
            builder = MermaidDiagramBuilder()
            return builder.build(
                transforms=transforms,
                lower_dims=lower_dims,
                upper_dims=upper_dims,
                bottom_dims=bottom_dims,
                top_dims=top_dims,
                title="Tensor Adaptor Transform Flow"
            )

        except Exception as e:
            # If parsing fails, return None to fall back to type extraction
            return None

    def _get_dimensions_from_pretty_printer(self, transforms):
        """
        Get dimensions by executing 'p' command and parsing the pretty printer output.
        This is needed when gdb.parse_and_eval doesn't give full access to the value.
        """
        if not self.expression:
            return [], []

        try:
            output = self._get_pretty_printer_output()
            if not output:
                return [], []

            # Use the parser to extract dimensions
            return PrettyPrinterOutputParser.extract_dimensions_for_transforms(output, len(transforms))

        except:
            # If anything fails, return empty dimensions
            return [], []


def generate_mermaid_command(arg_str):
    """
    GDB command to generate Mermaid diagram for a tensor.

    Usage in GDB:
        python generate_mermaid('tensor_variable_name')
    """
    try:
        # Evaluate the expression
        val = gdb.parse_and_eval(arg_str)

        # Generate Mermaid diagram - pass the original expression
        generator = MermaidGenerator(val, expression=arg_str)
        mermaid_code = generator.generate_mermaid()

        print("\n" + "="*60)
        print(f"Mermaid Diagram for: {arg_str}")
        print("="*60)
        print(mermaid_code)
        print("="*60)
        print("Copy the code above (including ``` markers) to visualize at:")
        print("  https://mermaid.live/")
        print("  or any Markdown viewer with Mermaid support")
        print("="*60 + "\n")

        return mermaid_code

    except Exception as e:
        print(f"Error generating Mermaid diagram: {e}")
        return None


# Register the command with GDB
class MermaidCommand(gdb.Command):
    """Generate Mermaid diagram for tensor_descriptor or tensor_adaptor."""

    def __init__(self):
        super(MermaidCommand, self).__init__("mermaid", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: mermaid <tensor_variable>")
            print("Example: mermaid a_lds_block_desc")
            return

        generate_mermaid_command(arg.strip())


# Also make it available as a Python function
def mermaid(tensor_name):
    """
    Generate Mermaid diagram for a tensor.

    Usage:
        python mermaid('a_lds_block_desc')
    """
    return generate_mermaid_command(tensor_name)