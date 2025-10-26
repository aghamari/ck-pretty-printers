"""
Mixin class for extracting transform information from tensor types.
This eliminates the 200+ lines of duplicated transform parsing code.
"""

import re
from ..utils.constants import TRANSFORM_PATTERNS
from ..utils.tuple_extractor import extract_transform_parameters


class TransformMixin:
    """
    Mixin providing transform extraction capabilities.

    Classes using this mixin should have self.val as a GDB value.
    """

    def extract_transform_info_from_type(self, type_str, template_name='tensor_descriptor'):
        """
        Extract transform information from a tensor type string.

        This method parses the type string to extract:
        - Transform types (embed, unmerge, merge, etc.)
        - Lower dimension sequences for each transform
        - Upper dimension sequences for each transform

        Args:
            type_str: Full C++ type string
            template_name: Name of the template to parse ('tensor_descriptor' or 'tensor_adaptor')

        Returns:
            Tuple of (transforms, lower_dims_list, upper_dims_list)
            - transforms: List of transform names (e.g., ['embed', 'pass_through', ...])
            - lower_dims_list: List of dimension lists for lower dimensions
            - upper_dims_list: List of dimension lists for upper dimensions
        """
        transforms = []
        lower_dims = []
        upper_dims = []

        # Find the template content
        template_start = type_str.find(f'{template_name}<')
        if template_start == -1:
            return transforms, lower_dims, upper_dims

        # Find the matching closing bracket
        pos = template_start + len(f'{template_name}<')
        bracket_count = 1
        template_end = pos

        while bracket_count > 0 and template_end < len(type_str):
            if type_str[template_end] == '<':
                bracket_count += 1
            elif type_str[template_end] == '>':
                bracket_count -= 1
            template_end += 1

        template_content = type_str[pos:template_end-1]

        # Parse the three tuples: transforms, lower_dims, upper_dims
        transforms_str, lower_dims_str, upper_dims_str = self._extract_three_tuples(template_content)

        # Parse transforms
        if transforms_str:
            transforms = self._parse_transforms(transforms_str)

        # Parse lower and upper dimensions
        if lower_dims_str:
            lower_dims = self._parse_dimension_sequences(lower_dims_str)

        if upper_dims_str:
            upper_dims = self._parse_dimension_sequences(upper_dims_str)

        return transforms, lower_dims, upper_dims

    def _extract_three_tuples(self, content):
        """
        Extract the first three tuples from template content.

        Args:
            content: Template content string

        Returns:
            Tuple of (transforms_str, lower_dims_str, upper_dims_str)
        """
        transforms_str = ""
        lower_dims_str = ""
        upper_dims_str = ""

        if not content.startswith('ck_tile::tuple<'):
            return transforms_str, lower_dims_str, upper_dims_str

        # Extract first tuple (transforms)
        start = len('ck_tile::tuple<')
        bracket_count = 1
        end = start

        while bracket_count > 0 and end < len(content):
            if content[end] == '<':
                bracket_count += 1
            elif content[end] == '>':
                bracket_count -= 1
            end += 1

        transforms_str = content[start:end-1]
        remaining = content[end:].lstrip(', ')

        # Extract second tuple (lower dims)
        if remaining.startswith('ck_tile::tuple<'):
            start = len('ck_tile::tuple<')
            bracket_count = 1
            end = start

            while bracket_count > 0 and end < len(remaining):
                if remaining[end] == '<':
                    bracket_count += 1
                elif remaining[end] == '>':
                    bracket_count -= 1
                end += 1

            lower_dims_str = remaining[start:end-1]
            remaining = remaining[end:].lstrip(', ')

            # Extract third tuple (upper dims)
            if remaining.startswith('ck_tile::tuple<'):
                start = len('ck_tile::tuple<')
                bracket_count = 1
                end = start

                while bracket_count > 0 and end < len(remaining):
                    if remaining[end] == '<':
                        bracket_count += 1
                    elif remaining[end] == '>':
                        bracket_count -= 1
                    end += 1

                upper_dims_str = remaining[start:end-1]

        return transforms_str, lower_dims_str, upper_dims_str

    def _parse_transforms(self, transforms_str):
        """
        Parse transform type names from transforms string.

        Args:
            transforms_str: String containing transform types

        Returns:
            List of transform names
        """
        transforms = []
        pos = 0

        while pos < len(transforms_str):
            found_transform = False

            for pattern, name in TRANSFORM_PATTERNS:
                if transforms_str[pos:].startswith(pattern):
                    transforms.append(name)

                    # Skip to the end of this transform
                    bracket_count = 1
                    pos += len(pattern)

                    while bracket_count > 0 and pos < len(transforms_str):
                        if transforms_str[pos] == '<':
                            bracket_count += 1
                        elif transforms_str[pos] == '>':
                            bracket_count -= 1
                        pos += 1

                    # Skip trailing comma and whitespace
                    while pos < len(transforms_str) and transforms_str[pos] in ', \t\n':
                        pos += 1

                    found_transform = True
                    break

            if not found_transform:
                pos += 1

        return transforms

    def _parse_dimension_sequences(self, dims_str):
        """
        Parse dimension sequences from a string.

        Args:
            dims_str: String containing ck_tile::sequence<...> elements

        Returns:
            List of dimension lists (e.g., [[0], [1, 2], [3]])
        """
        dims_list = []

        if 'sequence' not in dims_str:
            return dims_list

        # Use regex to find all sequences, including empty ones
        seq_matches = re.finditer(r'sequence<([^>]*)>', dims_str)

        for match in seq_matches:
            content = match.group(1).strip()

            if content:
                # Parse comma-separated integers (including negative)
                dims = [
                    int(x.strip())
                    for x in content.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]
                dims_list.append(dims if dims else [])
            else:
                # Empty sequence
                dims_list.append([])

        return dims_list

    def extract_bottom_top_dims(self, type_str):
        """
        Extract bottom and top dimension IDs from the type.

        Args:
            type_str: Full type string

        Returns:
            Tuple of (bottom_dims, top_dims) where each is a list of dimension IDs
        """
        # Pattern 1: Look for tensor_adaptor in the type
        if 'tensor_adaptor' in type_str:
            adaptor_match = re.search(
                r'ck_tile::tensor_adaptor<[^,]+,[^,]+,[^,]+,\s*'
                r'ck_tile::sequence<([\d,\s-]+)>,\s*'
                r'ck_tile::sequence<([\d,\s-]+)>',
                type_str
            )
            if adaptor_match:
                bottom_str = adaptor_match.group(1)
                top_str = adaptor_match.group(2)

                bottom_dims = [
                    int(x.strip())
                    for x in bottom_str.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]
                top_dims = [
                    int(x.strip())
                    for x in top_str.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]

                return bottom_dims, top_dims

        # Pattern 2: Extract from tensor_descriptor template parameters
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

            desc_content = type_str[pos:end-1]

            # Skip three tuples
            tuple_count = 0
            pos = 0

            while tuple_count < 3 and pos < len(desc_content):
                if desc_content[pos:].startswith('ck_tile::tuple<'):
                    start = pos + len('ck_tile::tuple<')
                    bracket_count = 1
                    end = start

                    while bracket_count > 0 and end < len(desc_content):
                        if desc_content[end] == '<':
                            bracket_count += 1
                        elif desc_content[end] == '>':
                            bracket_count -= 1
                        end += 1

                    pos = end
                    tuple_count += 1
                else:
                    pos += 1

            # After three tuples, first sequence is TopDimensionHiddenIds
            if tuple_count == 3:
                remaining = desc_content[pos:].lstrip(', ')
                top_match = re.search(r'ck_tile::sequence<([\d,\s-]+)>', remaining)

                if top_match:
                    top_str = top_match.group(1)
                    top_dims = [
                        int(x.strip())
                        for x in top_str.split(',')
                        if x.strip().lstrip('-').isdigit()
                    ]
                    # Bottom is always [0] for tensor_descriptor
                    return [0], top_dims

        return [], []

    def get_transform_parameters_from_member(self):
        """
        Extract transform parameters from the transforms_ member of self.val.

        Returns:
            List of parameter dicts, or empty list if extraction fails
        """
        try:
            transforms_tuple = self.val['transforms_']
            return extract_transform_parameters(transforms_tuple)
        except Exception:
            return []
