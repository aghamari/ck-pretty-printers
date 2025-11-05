"""
Unified Mermaid diagram builder for tensor types.
Eliminates duplication between descriptor and adaptor diagram generation.
"""

from typing import List, Dict, Any


class MermaidDiagramBuilder:
    """
    Builds Mermaid diagrams from transform data.
    This eliminates 80+ lines of duplicated diagram generation code.
    """

    def __init__(self):
        """Initialize the diagram builder."""
        self.lines = []

    def build(self,
             transforms: List[str],
             lower_dims: List[List[int]],
             upper_dims: List[List[int]],
             bottom_dims: List[int],
             top_dims: List[int],
             title: str = "Tensor Transform Flow") -> str:
        """
        Build a complete Mermaid diagram from transform data.

        Args:
            transforms: List of transform names
            lower_dims: List of lower dimension lists for each transform
            upper_dims: List of upper dimension lists for each transform
            bottom_dims: Bottom dimension IDs
            top_dims: Top dimension IDs
            title: Title for the diagram

        Returns:
            Complete Mermaid diagram as a string
        """
        self.lines = ["```mermaid", "graph TD"]

        # Add title
        self.lines.append(f"    %% {title}")
        self.lines.append("")

        # Track current dimension mapping - maps dimension ID to its node name
        current_dims = {}

        # Track which bottom dimensions have been consumed
        unconsumed_bottom_dims = list(bottom_dims) if bottom_dims else []

        # Add bottom dimensions
        if bottom_dims:
            for dim in bottom_dims:
                current_dims[dim] = f"B{dim}"
                self.lines.append(f'    B{dim}["Bottom[{dim}]"]')
                self.lines.append(f"    style B{dim} fill:#e1f5fe")
            self.lines.append("")

        # Process each transform
        for i, (transform, lower, upper) in enumerate(zip(transforms, lower_dims, upper_dims)):
            transform_node = f"T{i}"

            # Create transform node
            label = self._format_transform_label(transform, i, lower, upper)
            color = self._get_transform_color(transform)
            self.lines.append(f"    {transform_node}{label}")
            self.lines.append(f"    style {transform_node} fill:{color}")

            # Connect inputs to transform (lower dimensions)
            if not lower and unconsumed_bottom_dims:
                # Special case: empty lower dims (e.g., replicate)
                # Connect to the first unconsumed bottom dimension
                dim = unconsumed_bottom_dims[0]
                if dim in current_dims:
                    self.lines.append(f"    {current_dims[dim]} --> {transform_node}")
                    unconsumed_bottom_dims.remove(dim)
                    # Don't remove from current_dims yet, as it's not in lower
            else:
                for dim in lower:
                    if dim in current_dims:
                        self.lines.append(f"    {current_dims[dim]} --> {transform_node}")
                    # Mark bottom dims as consumed
                    if dim in unconsumed_bottom_dims:
                        unconsumed_bottom_dims.remove(dim)

            # Create output dimensions and update mapping
            new_dims = {}
            for j, dim in enumerate(upper):
                out_node = f"D{i}_{j}"
                new_dims[dim] = out_node
                self.lines.append(f'    {out_node}["Dim[{dim}]"]')
                self.lines.append(f"    {transform_node} --> {out_node}")

            # Update current dimension mapping
            # Remove consumed dimensions
            for dim in lower:
                if dim in current_dims:
                    del current_dims[dim]
            # Add new dimensions
            current_dims.update(new_dims)

            self.lines.append("")

        # Connect to top dimensions
        if top_dims:
            self.lines.append("    %% Top Dimensions")
            for dim in top_dims:
                # Use consistent naming: X for adaptor, T for descriptor (backward compat)
                top_node = f"X{dim}"
                self.lines.append(f'    {top_node}["Top[{dim}]"]')
                self.lines.append(f"    style {top_node} fill:#c8e6c9")
                if dim in current_dims:
                    self.lines.append(f"    {current_dims[dim]} --> {top_node}")

        self.lines.append("```")
        return "\n".join(self.lines)

    def _format_transform_label(self, transform: str, index: int,
                               lower: List[int], upper: List[int]) -> str:
        """
        Format transform label for Mermaid node.

        Args:
            transform: Transform name
            index: Transform index
            lower: Lower dimensions
            upper: Upper dimensions

        Returns:
            Formatted label string
        """
        lower_str = ','.join(map(str, lower))
        upper_str = ','.join(map(str, upper))

        # Use different shapes based on transform type
        if transform in ['embed', 'unmerge']:
            # Diamond for splitting transforms
            return f'{{"[{index}] {transform}<br/>[{lower_str}] → [{upper_str}]"}}'
        elif transform in ['merge', 'merge_v2']:
            # Diamond for merging transforms
            return f'{{"[{index}] {transform}<br/>[{lower_str}] → [{upper_str}]"}}'
        elif transform == 'xor':
            # Special shape for xor
            return f'[["[{index}] XOR<br/>[{lower_str}] → [{upper_str}]"]]'
        else:
            # Rectangle for others (pass_through, replicate, pad, etc.)
            return f'["[{index}] {transform}<br/>[{lower_str}] → [{upper_str}]"]'

    def _get_transform_color(self, transform: str) -> str:
        """
        Get color for transform type.

        Args:
            transform: Transform name

        Returns:
            Color code for the transform
        """
        colors = {
            'embed': '#fff3e0',
            'unmerge': '#fce4ec',
            'merge': '#e8f5e9',
            'merge_v2': '#e8f5e9',
            'pass_through': '#f3e5f5',
            'replicate': '#e3f2fd',
            'xor': '#ffebee',
            'xor_t': '#ffebee',
            'pad': '#fff9c4',
            'right_pad': '#fff9c4',
            'left_pad': '#fff9c4',
            'slice': '#efebe9',
            'freeze': '#eceff1',
        }
        return colors.get(transform, '#f5f5f5')