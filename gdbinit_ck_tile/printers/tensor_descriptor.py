"""Pretty printer for ck_tile::tensor_descriptor"""

import re
from ..core.base_printer import BaseCKTilePrinter
from ..core.transform_mixin import TransformMixin


class TensorDescriptorPrinter(BaseCKTilePrinter, TransformMixin):
    """Pretty printer for ck_tile::tensor_descriptor"""

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Extract basic fields
            elem_space_size = self.extract_int_from_field(self.val, 'element_space_size_')
            if elem_space_size is None:
                # Try to get from type string
                elem_match = re.search(r'ElementSpaceSize\s*=\s*ck_tile::constant<(\d+)[lL]?>', type_str)
                if not elem_match:
                    elem_match = re.search(r'ck_tile::constant<(\d+)[lL]?>,\s*ck_tile::sequence', type_str)
                if elem_match:
                    elem_space_size = int(elem_match.group(1))

            ntransform = self.extract_int_from_field(self.val, 'ntransform_')
            ndim_hidden = self.extract_int_from_field(self.val, 'ndim_hidden_')
            ndim_top = self.extract_int_from_field(self.val, 'ndim_top_')

            # Check if uninitialized
            if self.is_uninitialized(elem_space_size, ntransform, ndim_hidden):
                return "tensor_descriptor{[UNINITIALIZED]}"

            # Build result string
            result = "tensor_descriptor{\n"
            if elem_space_size is not None:
                result += f"  element_space_size: {elem_space_size}\n"
            if ntransform is not None:
                result += f"  ntransform: {ntransform}\n"
            if ndim_hidden is not None:
                result += f"  ndim_hidden: {ndim_hidden}\n"
            if ndim_top is not None:
                result += f"  ndim_top: {ndim_top}\n"

            # Try to get ndim_bottom from base class
            try:
                for field in self.val.type.fields():
                    if 'tensor_adaptor' in str(field.type):
                        base = self.val.cast(field.type)
                        ndim_bottom = self.extract_int_from_field(base, 'ndim_bottom_')
                        if ndim_bottom is not None:
                            result += f"  ndim_bottom: {ndim_bottom}\n"
                        break
            except:
                pass

            # Extract bottom and top dimension IDs using mixin
            bottom_dims, top_dims = self.extract_bottom_top_dims(type_str)
            if bottom_dims:
                result += f"  bottom_dimension_ids: {bottom_dims}\n"
            if top_dims:
                result += f"  top_dimension_ids: {top_dims}\n"

            # Extract transforms using mixin
            transforms, lower_dims_list, upper_dims_list = self.extract_transform_info_from_type(type_str)

            # Get transform parameters from runtime member using mixin
            params_list = self.get_transform_parameters_from_member()

            # Print transforms
            if transforms and ntransform and ntransform > 0:
                result += "\n  Transforms:\n"

                for i in range(min(ntransform, len(transforms))):
                    result += f"    [{i}] {transforms[i]}\n"

                    # Lower dimensions
                    if i < len(lower_dims_list) and lower_dims_list[i]:
                        result += f"        lower: {lower_dims_list[i]}\n"

                    # Upper dimensions
                    if i < len(upper_dims_list) and upper_dims_list[i]:
                        result += f"        upper: {upper_dims_list[i]}\n"

                    # Parameters from runtime member
                    if i < len(params_list) and params_list[i]:
                        for key, val in params_list[i].items():
                            result += f"        {key}: {val}\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tensor_descriptor")
