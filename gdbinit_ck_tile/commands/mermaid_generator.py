"""
Generate Mermaid diagrams for tensor_descriptor and tensor_adaptor dimension transformations.

This module provides commands to visualize the dimension flow through transforms
as a Mermaid flowchart diagram.
"""

import gdb
import re
from ..core.transform_mixin import TransformMixin
from ..utils.constants import TRANSFORM_PATTERNS


class MermaidGenerator(TransformMixin):
    """Generate Mermaid diagrams from tensor types."""

    def __init__(self, val, expression=None):
        self.val = val
        self.type_str = str(val.type)
        self.expression = expression  # Original expression passed to mermaid command

    def generate_mermaid(self):
        """
        Generate Mermaid diagram code for tensor_descriptor or tensor_adaptor.

        Returns:
            String containing Mermaid flowchart code
        """
        # Better heuristic: Check the number of template parameters
        # tensor_adaptor typically has more parameters than tensor_descriptor
        # Count the number of top-level commas in the template

        # Find the main template content
        if 'ck_tile::' in self.type_str:
            # Count template depth to distinguish between descriptor and adaptor
            # tensor_adaptor has transforms AND bottom/top sequences
            # tensor_descriptor has transforms and one sequence

            # A more reliable check: tensor_adaptor has "ck_tile::sequence" appearing twice at the end
            # tensor_descriptor has it appearing once
            sequence_count = self.type_str.count('ck_tile::sequence<')

            # tensor_adaptor typically has 2 sequences (bottom and top dims)
            # tensor_descriptor typically has 1 sequence (top dims only)
            if sequence_count >= 2:
                # Likely tensor_adaptor
                return self._generate_adaptor_mermaid()
            else:
                # Likely tensor_descriptor
                return self._generate_descriptor_mermaid()

        # Fallback to name-based detection
        if 'tensor_descriptor' in self.type_str:
            return self._generate_descriptor_mermaid()
        elif 'tensor_adaptor' in self.type_str:
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
            return "Error: No transforms found"

        # Extract bottom and top dimension IDs
        bottom_dims, top_dims = self._extract_descriptor_bottom_top_dims()

        # Build Mermaid diagram
        lines = ["```mermaid", "graph TD"]

        # Add title
        lines.append("    %% Tensor Descriptor Transform Flow")
        lines.append("")

        # Track current dimension mapping
        # Start with bottom dimensions
        current_dims = {}
        for dim in bottom_dims:
            current_dims[dim] = f"B{dim}"
            lines.append(f"    B{dim}[\"Bottom[{dim}]\"]")
            lines.append(f"    style B{dim} fill:#e1f5fe")

        lines.append("")

        # Process each transform
        for i, (transform, lower, upper) in enumerate(zip(transforms, lower_dims, upper_dims)):
            transform_node = f"T{i}"

            # Create transform node with better styling
            transform_label = self._format_transform_label(transform, i, lower, upper)
            color = self._get_transform_color(transform)
            lines.append(f"    {transform_node}{transform_label}")
            lines.append(f"    style {transform_node} fill:{color}")

            # Connect inputs to transform
            for dim in lower:
                if dim in current_dims:
                    lines.append(f"    {current_dims[dim]} --> {transform_node}")

            # Create output dimensions
            new_dims = {}
            for j, dim in enumerate(upper):
                out_node = f"D{i}_{j}"
                new_dims[dim] = out_node
                lines.append(f"    {out_node}[\"Dim[{dim}]\"]")
                lines.append(f"    {transform_node} --> {out_node}")

            # Update current dimension mapping
            # Remove consumed dimensions
            for dim in lower:
                if dim in current_dims:
                    del current_dims[dim]
            # Add new dimensions
            current_dims.update(new_dims)

            lines.append("")

        # Connect to top dimensions
        lines.append("    %% Top Dimensions")
        for dim in top_dims:
            top_node = f"T{dim}"
            lines.append(f"    {top_node}[\"Top[{dim}]\"]")
            lines.append(f"    style {top_node} fill:#c8e6c9")
            if dim in current_dims:
                lines.append(f"    {current_dims[dim]} --> {top_node}")

        lines.append("```")

        return "\n".join(lines)

    def _generate_adaptor_mermaid(self):
        """Generate Mermaid diagram for tensor_adaptor."""

        # For ps_ys_to_xs_ and similar cases, we need to get everything from pretty printer
        # because the type extraction doesn't work correctly
        if self.expression and ('ps_ys_to_xs_' in self.expression or 'ps_xs_to_ys_' in self.expression):
            # Get EVERYTHING from pretty printer output
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

        # Build Mermaid diagram
        lines = ["```mermaid", "graph TD"]

        # Add title
        lines.append("    %% Tensor Adaptor Transform Flow")
        lines.append("")

        # Track current dimension mapping
        # Start with bottom dimensions
        current_dims = {}
        for dim in bottom_dims:
            current_dims[dim] = f"B{dim}"
            lines.append(f"    B{dim}[\"Bottom[{dim}]\"]")
            lines.append(f"    style B{dim} fill:#e1f5fe")

        lines.append("")

        # Process each transform
        for i, (transform, lower, upper) in enumerate(zip(transforms, lower_dims, upper_dims)):
            transform_node = f"T{i}"

            # Create transform node
            transform_label = self._format_transform_label(transform, i, lower, upper)
            color = self._get_transform_color(transform)
            lines.append(f"    {transform_node}{transform_label}")
            lines.append(f"    style {transform_node} fill:{color}")

            # Connect inputs to transform
            for dim in lower:
                if dim in current_dims:
                    lines.append(f"    {current_dims[dim]} --> {transform_node}")

            # Create output dimensions
            new_dims = {}
            for j, dim in enumerate(upper):
                out_node = f"D{i}_{j}"
                new_dims[dim] = out_node
                lines.append(f"    {out_node}[\"Dim[{dim}]\"]")
                lines.append(f"    {transform_node} --> {out_node}")

            # Update current dimension mapping
            for dim in lower:
                if dim in current_dims:
                    del current_dims[dim]
            current_dims.update(new_dims)

            lines.append("")

        # Connect to top dimensions
        lines.append("    %% Top Dimensions")
        for dim in top_dims:
            top_node = f"X{dim}"
            lines.append(f"    {top_node}[\"Top[{dim}]\"]")
            lines.append(f"    style {top_node} fill:#c8e6c9")
            if dim in current_dims:
                lines.append(f"    {current_dims[dim]} --> {top_node}")

        lines.append("```")

        return "\n".join(lines)

    def _format_transform_label(self, transform, index, lower, upper):
        """Format transform label for Mermaid node."""
        lower_str = ','.join(map(str, lower))
        upper_str = ','.join(map(str, upper))

        # Use different shapes based on transform type
        if transform in ['embed', 'unmerge']:
            # Diamond for splitting transforms
            return f"{{\"[{index}] {transform}<br/>[{lower_str}] → [{upper_str}]\"}}"
        elif transform in ['merge', 'merge_v2']:
            # Diamond for merging transforms
            return f"{{\"[{index}] {transform}<br/>[{lower_str}] → [{upper_str}]\"}}"
        elif transform == 'xor':
            # Special shape for xor
            return f"[[\"[{index}] XOR<br/>[{lower_str}] → [{upper_str}]\"]]"
        else:
            # Rectangle for others
            return f"[\"[{index}] {transform}<br/>[{lower_str}] → [{upper_str}]\"]"

    def _get_transform_color(self, transform):
        """Get color for transform type."""
        colors = {
            'embed': '#fff3e0',
            'unmerge': '#fce4ec',
            'merge': '#e8f5e9',
            'merge_v2': '#e8f5e9',
            'pass_through': '#f3e5f5',
            'replicate': '#e3f2fd',
            'xor': '#ffebee',
            'pad': '#fff9c4',
            'right_pad': '#fff9c4',
            'left_pad': '#fff9c4',
            'slice': '#efebe9',
            'freeze': '#eceff1',
        }
        return colors.get(transform, '#f5f5f5')

    def _extract_descriptor_bottom_top_dims(self):
        """Extract bottom and top dimension IDs for tensor_descriptor."""
        # Look for patterns like:
        # sequence<11, 12> at the end for top dims
        # sequence<0> near the beginning for bottom dims

        # Find the sequences after the transform tuples
        match = re.search(
            r'ck_tile::sequence<([\d,\s-]+)>,\s*ck_tile::constant<\d+[lL]?>,',
            self.type_str
        )

        if match:
            top_str = match.group(1)
            top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]
        else:
            top_dims = []

        # Bottom dims are usually [0] for tensor_descriptor
        bottom_dims = [0]

        return bottom_dims, top_dims

    def _extract_adaptor_bottom_top_dims(self):
        """Extract bottom and top dimension IDs for tensor_adaptor."""
        # For tensor_adaptor, look for the sequences at the end
        match = re.search(
            r'ck_tile::sequence<([\d,\s-]+)>,\s*ck_tile::sequence<([\d,\s-]+)>\s*>\s*$',
            self.type_str
        )

        if match:
            bottom_str = match.group(1)
            top_str = match.group(2)

            bottom_dims = [int(x.strip()) for x in bottom_str.split(',') if x.strip().lstrip('-').isdigit()]
            top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]
        else:
            bottom_dims = []
            top_dims = []

        return bottom_dims, top_dims

    def _generate_from_pretty_printer(self):
        """
        Generate the complete Mermaid diagram from pretty printer output.
        This is needed for ps_ys_to_xs_ and similar cases.
        """
        if not self.expression:
            return None

        try:
            # Execute the 'p' command to get pretty printer output
            output = gdb.execute(f"p {self.expression}", to_string=True)

            # Remove the "$N = " prefix from GDB output
            if ' = ' in output:
                output = output.split(' = ', 1)[1]

            # Parse everything from the output
            transforms = []
            lower_dims = []
            upper_dims = []
            bottom_dims = []
            top_dims = []

            lines = output.split('\n')

            # Look for bottom and top dimension IDs
            for line in lines:
                if 'bottom_dimension_ids:' in line:
                    match = re.search(r'\[([\d,\s-]+)\]', line)
                    if match:
                        bottom_dims = [int(x.strip()) for x in match.group(1).split(',') if x.strip().lstrip('-').isdigit()]

                if 'top_dimension_ids:' in line:
                    match = re.search(r'\[([\d,\s-]+)\]', line)
                    if match:
                        top_dims = [int(x.strip()) for x in match.group(1).split(',') if x.strip().lstrip('-').isdigit()]

            # Parse transforms and dimensions
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Look for transform marker like "[0] replicate" or "[1] unmerge"
                transform_match = re.search(r'^\[(\d+)\]\s+(\w+)', line)
                if transform_match:
                    transform_name = transform_match.group(2)
                    transforms.append(transform_name)

                    # Collect parameters for this transform
                    current_lower = []
                    current_upper = []

                    j = i + 1
                    while j < len(lines):
                        param_line = lines[j].strip()

                        # Stop if we hit another transform or closing brace
                        if re.search(r'^\[(\d+)\]\s+\w+', param_line) or param_line.startswith('}'):
                            break

                        # Extract lower dimension
                        if 'lower:' in param_line:
                            lower_match = re.search(r'lower:\s*\[([^\]]*)\]', param_line)
                            if lower_match:
                                lower_str = lower_match.group(1).strip()
                                if lower_str:
                                    current_lower = [int(x.strip()) for x in lower_str.split(',') if x.strip().lstrip('-').isdigit()]

                        # Extract upper dimension
                        if 'upper:' in param_line:
                            upper_match = re.search(r'upper:\s*\[([^\]]*)\]', param_line)
                            if upper_match:
                                upper_str = upper_match.group(1).strip()
                                if upper_str:
                                    current_upper = [int(x.strip()) for x in upper_str.split(',') if x.strip().lstrip('-').isdigit()]

                        j += 1

                    lower_dims.append(current_lower)
                    upper_dims.append(current_upper)

                    i = j
                else:
                    i += 1

            if not transforms:
                return None

            # Build Mermaid diagram
            lines = ["```mermaid", "graph TD"]
            lines.append("    %% Tensor Adaptor Transform Flow")
            lines.append("")

            # Track current dimension mapping
            current_dims = {}

            # Start with bottom dimensions
            for dim in bottom_dims:
                current_dims[dim] = f"B{dim}"
                lines.append(f"    B{dim}[\"Bottom[{dim}]\"]")
                lines.append(f"    style B{dim} fill:#e1f5fe")

            lines.append("")

            # Process each transform
            for i, (transform, lower, upper) in enumerate(zip(transforms, lower_dims, upper_dims)):
                transform_node = f"T{i}"

                # Create transform node
                transform_label = self._format_transform_label(transform, i, lower, upper)
                color = self._get_transform_color(transform)
                lines.append(f"    {transform_node}{transform_label}")
                lines.append(f"    style {transform_node} fill:{color}")

                # Connect inputs to transform
                for dim in lower:
                    if dim in current_dims:
                        lines.append(f"    {current_dims[dim]} --> {transform_node}")

                # Create output dimensions
                new_dims = {}
                for j, dim in enumerate(upper):
                    out_node = f"D{i}_{j}"
                    new_dims[dim] = out_node
                    lines.append(f"    {out_node}[\"Dim[{dim}]\"]")
                    lines.append(f"    {transform_node} --> {out_node}")

                # Update current dimension mapping
                for dim in lower:
                    if dim in current_dims:
                        del current_dims[dim]
                current_dims.update(new_dims)

                lines.append("")

            # Connect to top dimensions
            lines.append("    %% Top Dimensions")
            for dim in top_dims:
                top_node = f"X{dim}"
                lines.append(f"    {top_node}[\"Top[{dim}]\"]")
                lines.append(f"    style {top_node} fill:#c8e6c9")
                if dim in current_dims:
                    lines.append(f"    {current_dims[dim]} --> {top_node}")

            lines.append("```")
            return "\n".join(lines)

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
            # Execute the 'p' command to get pretty printer output
            output = gdb.execute(f"p {self.expression}", to_string=True)

            # Remove the "$N = " prefix from GDB output
            if ' = ' in output:
                output = output.split(' = ', 1)[1]

            # Parse the output to extract dimensions
            lower_dims = []
            upper_dims = []

            lines = output.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Look for transform marker like "[0] embed"
                if re.search(r'^\[(\d+)\]\s+\w+', line):
                    # Found a transform, collect its parameters
                    current_lower = []
                    current_upper = []

                    # Look at the next few lines for parameters
                    j = i + 1
                    while j < len(lines):
                        param_line = lines[j].strip()

                        # Stop if we hit another transform or closing brace
                        if re.search(r'^\[(\d+)\]\s+\w+', param_line) or param_line.startswith('}'):
                            break

                        # Extract lower dimension
                        if 'lower:' in param_line:
                            lower_match = re.search(r'lower:\s*\[([^\]]*)\]', param_line)
                            if lower_match:
                                lower_str = lower_match.group(1).strip()
                                if lower_str:
                                    current_lower = [int(x.strip()) for x in lower_str.split(',') if x.strip().lstrip('-').isdigit()]

                        # Extract upper dimension
                        if 'upper:' in param_line:
                            upper_match = re.search(r'upper:\s*\[([^\]]*)\]', param_line)
                            if upper_match:
                                upper_str = upper_match.group(1).strip()
                                if upper_str:
                                    current_upper = [int(x.strip()) for x in upper_str.split(',') if x.strip().lstrip('-').isdigit()]

                        j += 1

                    # Add this transform's dimensions
                    lower_dims.append(current_lower)
                    upper_dims.append(current_upper)

                    # Move to the next transform position
                    i = j
                else:
                    i += 1

            # Ensure we have the right number of dimension lists
            while len(lower_dims) < len(transforms):
                lower_dims.append([])
            while len(upper_dims) < len(transforms):
                upper_dims.append([])

            # Truncate if we have too many
            lower_dims = lower_dims[:len(transforms)]
            upper_dims = upper_dims[:len(transforms)]

            return lower_dims, upper_dims

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