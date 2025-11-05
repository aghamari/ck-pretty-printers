"""
Parser for pretty printer output.
Consolidates duplicated parsing logic from mermaid_generator.py and test files.
"""

import re
from typing import List, Tuple, Dict, Any, Optional


class PrettyPrinterOutputParser:
    """
    Parse pretty printer output to extract transform information.
    This eliminates 150+ lines of duplicated parsing code.
    """

    @staticmethod
    def parse_transforms(output: str) -> List[Dict[str, Any]]:
        """
        Parse transform information from pretty printer output.

        Args:
            output: Pretty printer output string

        Returns:
            List of transform dictionaries with keys:
                - name: Transform name (e.g., 'replicate', 'unmerge')
                - lower: List of lower dimension indices
                - upper: List of upper dimension indices
                - parameters: Dict of additional parameters
        """
        transforms = []
        lines = output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for transform marker like "[0] replicate" or "[1] unmerge"
            transform_match = re.search(r'^\[(\d+)\]\s+(\w+)', line)
            if transform_match:
                transform_index = int(transform_match.group(1))
                transform_name = transform_match.group(2)

                # Collect parameters for this transform
                current_lower = []
                current_upper = []
                parameters = {}

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
                                current_lower = [int(x.strip()) for x in lower_str.split(',')
                                               if x.strip().lstrip('-').isdigit()]

                    # Extract upper dimension
                    if 'upper:' in param_line:
                        upper_match = re.search(r'upper:\s*\[([^\]]*)\]', param_line)
                        if upper_match:
                            upper_str = upper_match.group(1).strip()
                            if upper_str:
                                current_upper = [int(x.strip()) for x in upper_str.split(',')
                                               if x.strip().lstrip('-').isdigit()]

                    # Extract other parameters (lengths, etc.)
                    if 'up_lengths:' in param_line:
                        match = re.search(r'up_lengths:\s*\[([^\]]*)\]', param_line)
                        if match:
                            parameters['up_lengths'] = match.group(1)

                    if 'low_lengths:' in param_line:
                        match = re.search(r'low_lengths:\s*\[([^\]]*)\]', param_line)
                        if match:
                            parameters['low_lengths'] = match.group(1)

                    if 'lengths:' in param_line and 'up_lengths' not in param_line and 'low_lengths' not in param_line:
                        match = re.search(r'lengths:\s*\[([^\]]*)\]', param_line)
                        if match:
                            parameters['lengths'] = match.group(1)

                    j += 1

                transforms.append({
                    'index': transform_index,
                    'name': transform_name,
                    'lower': current_lower,
                    'upper': current_upper,
                    'parameters': parameters
                })

                i = j
            else:
                i += 1

        return transforms

    @staticmethod
    def parse_bottom_top_dims(output: str) -> Tuple[List[int], List[int]]:
        """
        Parse bottom and top dimension IDs from pretty printer output.

        Args:
            output: Pretty printer output string

        Returns:
            Tuple of (bottom_dims, top_dims) as lists of integers
        """
        bottom_dims = []
        top_dims = []

        lines = output.split('\n')

        for line in lines:
            if 'bottom_dimension_ids:' in line:
                match = re.search(r'\[([\d,\s-]+)\]', line)
                if match:
                    bottom_dims = [int(x.strip()) for x in match.group(1).split(',')
                                 if x.strip().lstrip('-').isdigit()]

            if 'top_dimension_ids:' in line:
                match = re.search(r'\[([\d,\s-]+)\]', line)
                if match:
                    top_dims = [int(x.strip()) for x in match.group(1).split(',')
                               if x.strip().lstrip('-').isdigit()]

        return bottom_dims, top_dims

    @staticmethod
    def parse_ntransform(output: str) -> Optional[int]:
        """
        Parse the ntransform count from pretty printer output.

        Args:
            output: Pretty printer output string

        Returns:
            Number of transforms or None if not found
        """
        match = re.search(r'ntransform:\s*(\d+)', output)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def parse_complete(output: str) -> Dict[str, Any]:
        """
        Parse complete pretty printer output into structured data.

        Args:
            output: Pretty printer output string

        Returns:
            Dictionary with all parsed information:
                - transforms: List of transform dictionaries
                - bottom_dims: List of bottom dimension IDs
                - top_dims: List of top dimension IDs
                - ntransform: Number of transforms
        """
        return {
            'transforms': PrettyPrinterOutputParser.parse_transforms(output),
            'bottom_dims': PrettyPrinterOutputParser.parse_bottom_top_dims(output)[0],
            'top_dims': PrettyPrinterOutputParser.parse_bottom_top_dims(output)[1],
            'ntransform': PrettyPrinterOutputParser.parse_ntransform(output)
        }

    @staticmethod
    def extract_dimensions_for_transforms(output: str, transform_count: int) -> Tuple[List[List[int]], List[List[int]]]:
        """
        Extract lower and upper dimensions for a given number of transforms.
        Ensures the lists are properly sized even if some transforms have no dimensions.

        Args:
            output: Pretty printer output string
            transform_count: Expected number of transforms

        Returns:
            Tuple of (lower_dims_list, upper_dims_list) where each is a list of lists
        """
        transforms = PrettyPrinterOutputParser.parse_transforms(output)

        lower_dims = []
        upper_dims = []

        for i in range(transform_count):
            if i < len(transforms):
                lower_dims.append(transforms[i]['lower'])
                upper_dims.append(transforms[i]['upper'])
            else:
                lower_dims.append([])
                upper_dims.append([])

        return lower_dims, upper_dims