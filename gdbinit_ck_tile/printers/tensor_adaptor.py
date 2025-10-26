"""Pretty printer for ck_tile::tensor_adaptor"""

from ..core.base_printer import BaseCKTilePrinter
from ..core.transform_mixin import TransformMixin


class TensorAdaptorPrinter(BaseCKTilePrinter, TransformMixin):
    """Pretty printer for ck_tile::tensor_adaptor"""

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Extract transforms using mixin
            transforms, lower_dims_list, upper_dims_list = self.extract_transform_info_from_type(
                type_str,
                template_name='tensor_adaptor'
            )

            # Extract bottom and top dimension IDs
            bottom_dims, top_dims = self._extract_bottom_top_dims_adaptor(type_str)

            # Get transform parameters from runtime member
            params_list = self.get_transform_parameters_from_member()

            # Build result
            result = "tensor_adaptor{\n"
            result += f"  ntransform: {len(transforms)}\n"

            if bottom_dims:
                result += f"  bottom_dimension_ids: {bottom_dims}\n"
            if top_dims:
                result += f"  top_dimension_ids: {top_dims}\n"

            # Display transforms
            if transforms:
                result += "\n  Transforms:\n"

                for i, transform in enumerate(transforms):
                    result += f"    [{i}] {transform}\n"

                    if i < len(lower_dims_list) and lower_dims_list[i]:
                        result += f"        lower: {lower_dims_list[i]}\n"

                    if i < len(upper_dims_list) and upper_dims_list[i]:
                        result += f"        upper: {upper_dims_list[i]}\n"

                    # Parameters
                    if i < len(params_list) and params_list[i]:
                        for key, val in params_list[i].items():
                            result += f"        {key}: {val}\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tensor_adaptor")

    def _extract_bottom_top_dims_adaptor(self, type_str):
        """Extract bottom and top dimension IDs from tensor_adaptor"""
        import re

        # Find tensor_adaptor content
        adaptor_start = type_str.find('tensor_adaptor<')
        if adaptor_start == -1:
            return [], []

        pos = adaptor_start + len('tensor_adaptor<')
        bracket_count = 1
        end = pos

        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        adaptor_content = type_str[pos:end-1]

        # Skip three tuples
        tuple_count = 0
        pos = 0

        while tuple_count < 3 and pos < len(adaptor_content):
            if adaptor_content[pos:].startswith('ck_tile::tuple<'):
                start = pos + len('ck_tile::tuple<')
                bracket_count = 1
                end = start

                while bracket_count > 0 and end < len(adaptor_content):
                    if adaptor_content[end] == '<':
                        bracket_count += 1
                    elif adaptor_content[end] == '>':
                        bracket_count -= 1
                    end += 1

                pos = end
                tuple_count += 1
            else:
                pos += 1

        # After three tuples, find the two sequences
        if tuple_count == 3:
            remaining = adaptor_content[pos:].lstrip(', ')
            seqs = re.findall(r'ck_tile::sequence<([\d,\s-]+)>', remaining)

            if len(seqs) >= 2:
                bottom_str = seqs[0]
                top_str = seqs[1]

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

        return [], []
