import gdb
import gdb.printing
import re

# Shared helper function for extracting elements from ck_tile::tuple
def extract_tuple_elements(tuple_obj):
    """Generic function to extract all elements from a ck_tile::tuple"""
    elements = []
    try:
        # First, cast to the tuple_base (the immediate base class)
        for field in tuple_obj.type.fields():
            field_type_str = str(field.type)
            if 'tuple_base' in field_type_str:
                # Cast to the base class
                base = tuple_obj.cast(field.type)
                # Now iterate through the tuple_object fields in the base
                for base_field in base.type.fields():
                    base_field_type_str = str(base_field.type)
                    if 'tuple_object' in base_field_type_str:
                        try:
                            # Extract element type from tuple_object<Index, ElementType, bool>
                            # Need bracket counting because ElementType may have nested templates
                            match = re.search(r'tuple_object<(\d+),\s*', base_field_type_str)
                            if match:
                                start_pos = match.end()
                                # Count brackets to find where ElementType ends
                                bracket_count = 0
                                pos = start_pos
                                while pos < len(base_field_type_str):
                                    if base_field_type_str[pos] == '<':
                                        bracket_count += 1
                                    elif base_field_type_str[pos] == '>':
                                        if bracket_count > 0:
                                            bracket_count -= 1
                                        else:
                                            break
                                    elif base_field_type_str[pos] == ',' and bracket_count == 0:
                                        break
                                    pos += 1

                                element_type = base_field_type_str[start_pos:pos].strip()

                                # Check if the ELEMENT type itself is a constant<N>
                                if element_type.startswith('ck_tile::constant<'):
                                    # Extract the value from the type string
                                    const_match = re.search(r'constant<(\d+)[uUlL]*>', element_type)
                                    if const_match:
                                        val = int(const_match.group(1))
                                        elements.append(val)
                                else:
                                    # It's a runtime value or complex type, access the element field
                                    tuple_obj_cast = base.cast(base_field.type)
                                    elem = tuple_obj_cast['element']
                                    # Check the type and convert appropriately
                                    elem_type_str = str(elem.type)
                                    if elem_type_str in ['int', 'long', 'long int', 'unsigned int', 'unsigned long']:
                                        # It's a numeric type, convert to Python int
                                        val = int(elem)
                                        elements.append(val)
                                    else:
                                        # It's a complex object (like embed, unmerge, etc), keep as GDB value
                                        elements.append(elem)
                        except:
                            pass
    except:
        pass
    return elements

class CKTileTensorDescriptorPrinter:
    """Pretty printer for ck_tile::tensor_descriptor"""

    def __init__(self, val):
        self.val = val

    def extract_int_from_field(self, obj, field_name):
        """Safely extract integer from a field"""
        try:
            field = obj[field_name]
            field_type_str = str(field.type)

            # Check if it's a constant<> type first
            if 'constant<' in field_type_str:
                # Extract the constant value from the type
                import re
                # Handle both constant<8192l> and constant<8192>
                const_match = re.search(r'constant<(\d+)[lL]?>', field_type_str)
                if const_match:
                    val = int(const_match.group(1))
                    if abs(val) > 100000000:
                        return None
                    return val

            # Try direct conversion for regular types
            try:
                val = int(field)
                if abs(val) > 100000000:
                    return None
                return val
            except:
                # If that fails, try accessing value member
                try:
                    val = int(field['value'])
                    if abs(val) > 100000000:
                        return None
                    return val
                except:
                    pass

            return None
        except Exception as e:
            # Silently return None on any error
            return None

    def extract_transform_info_from_type(self, type_str):
        """Extract transform information from the tensor_descriptor type string"""
        transforms = []
        lower_dims = []
        upper_dims = []

        # In ck_tile, tensor_descriptor<Transforms, LowerDims, UpperDims, ...>
        # The structure is: tensor_descriptor<tuple<transforms...>, tuple<lower_seqs...>, tuple<upper_seqs...>, ...>

        # First, extract just the tensor_descriptor template parameters
        # We need to be careful with nested angle brackets
        desc_start = type_str.find('tensor_descriptor<')
        if desc_start == -1:
            return transforms, lower_dims, upper_dims

        # Find the matching closing bracket
        bracket_count = 1
        pos = desc_start + len('tensor_descriptor<')
        desc_end = pos
        while bracket_count > 0 and desc_end < len(type_str):
            if type_str[desc_end] == '<':
                bracket_count += 1
            elif type_str[desc_end] == '>':
                bracket_count -= 1
            desc_end += 1

        desc_content = type_str[pos:desc_end-1]

        # Initialize variables
        transforms_str = ""
        lower_dims_str = ""
        upper_dims_str = ""

        # Parse by finding balanced angle brackets for each tuple
        # First tuple (transforms) - needs careful parsing due to nested brackets
        if desc_content.startswith('ck_tile::tuple<'):
            # Find the end of the first tuple by counting brackets
            start = len('ck_tile::tuple<')
            bracket_count = 1
            end = start
            while bracket_count > 0 and end < len(desc_content):
                if desc_content[end] == '<':
                    bracket_count += 1
                elif desc_content[end] == '>':
                    bracket_count -= 1
                end += 1

            transforms_str = desc_content[start:end-1]
            remaining = desc_content[end:].lstrip(', ')

            # Second tuple (lower dims) - need to find the tuple's closing >
            if remaining.startswith('ck_tile::tuple<'):
                start = len('ck_tile::tuple<')
                # Need to find the matching > for the tuple, not just any >
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

                # Third tuple (upper dims) - also need proper bracket matching
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

        # Now parse the extracted strings if we found them
        if transforms_str:
            # Parse transforms - need to handle multiple instances and preserve order
            # Split by commas but be careful with nested brackets
            pos = 0
            while pos < len(transforms_str):
                found_transform = False

                transform_patterns = [
                    ('ck_tile::embed<', 'embed'),
                    ('embed<', 'embed'),
                    ('ck_tile::unmerge<', 'unmerge'),
                    ('unmerge<', 'unmerge'),
                    ('ck_tile::merge_v2_magic_division<', 'merge_v2'),
                    ('merge_v2_magic_division<', 'merge_v2'),
                    ('ck_tile::merge<', 'merge'),
                    ('merge<', 'merge'),
                    ('ck_tile::replicate<', 'replicate'),
                    ('replicate<', 'replicate'),
                    ('ck_tile::pass_through<', 'pass_through'),
                    ('pass_through<', 'pass_through'),
                    ('ck_tile::right_pad<', 'right_pad'),
                    ('right_pad<', 'right_pad'),
                    ('ck_tile::left_pad<', 'left_pad'),
                    ('left_pad<', 'left_pad'),
                    ('ck_tile::slice<', 'slice'),
                    ('slice<', 'slice'),
                    ('ck_tile::freeze<', 'freeze'),
                    ('freeze<', 'freeze')
                ]

                for pattern, name in transform_patterns:
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
                        # Skip any trailing comma and whitespace
                        while pos < len(transforms_str) and transforms_str[pos] in ', \t\n':
                            pos += 1
                        found_transform = True
                        break

                if not found_transform:
                    pos += 1

        # Parse lower dimensions if we have them (handle empty sequences)
        if lower_dims_str:
            if 'sequence' in lower_dims_str:
                # Use finditer to handle empty sequences
                seq_matches = re.finditer(r'sequence<([^>]*)>', lower_dims_str)
                for match in seq_matches:
                    content = match.group(1).strip()
                    if content:
                        dims = [int(x.strip()) for x in content.split(',') if x.strip().lstrip('-').isdigit()]
                        if dims:
                            lower_dims.append(dims)
                    else:
                        # Empty sequence
                        lower_dims.append([])

        # Parse upper dimensions if we have them (handle empty sequences)
        if upper_dims_str:
            if 'sequence' in upper_dims_str:
                # Use finditer to handle empty sequences
                seq_matches = re.finditer(r'sequence<([^>]*)>', upper_dims_str)
                for match in seq_matches:
                    content = match.group(1).strip()
                    if content:
                        dims = [int(x.strip()) for x in content.split(',') if x.strip().lstrip('-').isdigit()]
                        if dims:
                            upper_dims.append(dims)
                    else:
                        # Empty sequence
                        upper_dims.append([])

        return transforms, lower_dims, upper_dims

    def extract_bottom_top_dims(self, type_str):
        """Extract bottom and top dimension IDs from the type"""
        # From ptype output, we can see:
        # tensor_descriptor inherits from tensor_adaptor<..., ck_tile::sequence<0>, TopDimensionHiddenIds>
        # Where TopDimensionHiddenIds = ck_tile::sequence<1, 2, 3, 4>

        # First, look for the base class tensor_adaptor in the field list
        # The field name contains the full tensor_adaptor type
        if 'tensor_adaptor' in type_str:
            # Find the tensor_adaptor field (it's the base class)
            adaptor_match = re.search(r'ck_tile::tensor_adaptor<[^,]+,[^,]+,[^,]+,\s*ck_tile::sequence<([\d,\s-]+)>,\s*ck_tile::sequence<([\d,\s-]+)>', type_str)
            if adaptor_match:
                bottom_str = adaptor_match.group(1)
                top_str = adaptor_match.group(2)

                bottom_dims = [int(x.strip()) for x in bottom_str.split(',') if x.strip().lstrip('-').isdigit()]
                top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]

                return bottom_dims, top_dims

        # Alternative: Look for TopDimensionHiddenIds in the template parameters
        # tensor_descriptor<..., TopDimensionHiddenIds, ...> where TopDimensionHiddenIds is after the 3 tuples
        desc_match = re.search(r'tensor_descriptor<', type_str)
        if desc_match:
            # Find tensor_descriptor content
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

                # After three tuples, the first sequence is TopDimensionHiddenIds (not BottomDimensionHiddenIds!)
                # BottomDimensionIds is hardcoded as sequence<0> in the base class
                if tuple_count == 3:
                    remaining = desc_content[pos:].lstrip(', ')
                    # First sequence after tuples is TopDimensionHiddenIds
                    top_match = re.search(r'ck_tile::sequence<([\d,\s-]+)>', remaining)
                    if top_match:
                        top_str = top_match.group(1)
                        top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]
                        # Bottom is always [0] for this pattern
                        return [0], top_dims

        return [], []

    def extract_transform_parameters(self, transforms_tuple):
        """Extract parameters from the transforms_ tuple member"""
        params_list = []

        try:
            # Extract all transforms from the tuple using the module-level function
            transforms = extract_tuple_elements(transforms_tuple)

            for transform in transforms:
                params = {}

                # For embed, unmerge, merge, etc - try to get up_lengths
                try:
                    up_lengths_tuple = transform['up_lengths_']
                    lengths = extract_tuple_elements(up_lengths_tuple)
                    if lengths:
                        params['up_lengths'] = lengths
                except:
                    pass

                # Try to get low_lengths
                try:
                    low_lengths_tuple = transform['low_lengths_']
                    lengths = extract_tuple_elements(low_lengths_tuple)
                    if lengths:
                        params['low_lengths'] = lengths
                except:
                    pass

                # Try to get coefficients (for embed)
                try:
                    coefficients_tuple = transform['coefficients_']
                    coeffs = extract_tuple_elements(coefficients_tuple)
                    if coeffs:
                        params['coefficients'] = coeffs
                except:
                    pass

                params_list.append(params)

        except:
            pass

        return params_list

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Extract basic fields with better error handling
            elem_space_size = self.extract_int_from_field(self.val, 'element_space_size_')
            if elem_space_size is None:
                # If extraction fails, try to get it from the type
                import re
                # Handle constant<8192l> pattern
                elem_match = re.search(r'ElementSpaceSize\s*=\s*ck_tile::constant<(\d+)[lL]?>', type_str)
                if not elem_match:
                    # Try alternate pattern
                    elem_match = re.search(r'ck_tile::constant<(\d+)[lL]?>,\s*ck_tile::sequence', type_str)
                if elem_match:
                    elem_space_size = int(elem_match.group(1))

            ntransform = self.extract_int_from_field(self.val, 'ntransform_')
            ndim_hidden = self.extract_int_from_field(self.val, 'ndim_hidden_')
            ndim_top = self.extract_int_from_field(self.val, 'ndim_top_')

            # For uninitialized descriptors, check if all values are None or invalid
            if elem_space_size is None and ntransform is None and ndim_hidden is None:
                return "tensor_descriptor{[UNINITIALIZED]}"

            if elem_space_size is not None and abs(elem_space_size) > 100000000:
                return "tensor_descriptor{[UNINITIALIZED]}"

            result = "tensor_descriptor{\n"
            if elem_space_size is not None:
                result += f"  element_space_size: {elem_space_size}\n"
            if ntransform is not None:
                result += f"  ntransform: {ntransform}\n"
            if ndim_hidden is not None:
                result += f"  ndim_hidden: {ndim_hidden}\n"
            if ndim_top is not None:
                result += f"  ndim_top: {ndim_top}\n"

            # Try to get ndim_bottom from the base class (tensor_adaptor)
            try:
                # Cast to base class tensor_adaptor
                for field in self.val.type.fields():
                    if 'tensor_adaptor' in str(field.type):
                        base = self.val.cast(field.type)
                        ndim_bottom = self.extract_int_from_field(base, 'ndim_bottom_')
                        if ndim_bottom is not None:
                            result += f"  ndim_bottom: {ndim_bottom}\n"
                        break
            except:
                pass

            # Extract bottom and top dimension IDs
            bottom_dims, top_dims = self.extract_bottom_top_dims(type_str)
            if bottom_dims:
                result += f"  bottom_dimension_ids: {bottom_dims}\n"
            if top_dims:
                result += f"  top_dimension_ids: {top_dims}\n"

            # Extract transforms from type
            transforms, lower_dims_list, upper_dims_list = self.extract_transform_info_from_type(type_str)

            # Also try to get transform parameters from the transforms_ member
            params_list = []
            try:
                transforms_tuple = self.val['transforms_']
                params_list = self.extract_transform_parameters(transforms_tuple)
            except Exception as e:
                # Silent failure - transforms_ member might not exist
                pass

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

                    # Parameters
                    if i < len(params_list) and params_list[i]:
                        for key, val in params_list[i].items():
                            result += f"        {key}: {val}\n"

            result += "}"
            return result

        except Exception as e:
            # More informative error message
            import traceback
            error_msg = str(e)
            if "Cannot convert value to long" in error_msg:
                return f"tensor_descriptor [Error: {error_msg}]"
            else:
                return f"tensor_descriptor{{error: {str(e)}}}"

class CKTileTensorAdaptorPrinter:
    """Pretty printer for ck_tile::tensor_adaptor"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_adaptor{\n"

            # Extract transforms, lower/upper dims similar to tensor_descriptor
            transforms, lower_dims_list, upper_dims_list = self.extract_transform_info_from_type(type_str)

            # Extract bottom and top dimension IDs
            bottom_dims, top_dims = self.extract_bottom_top_dims_adaptor(type_str)

            # Display basic info
            result += f"  ntransform: {len(transforms)}\n"

            if bottom_dims:
                result += f"  bottom_dimension_ids: {bottom_dims}\n"
            if top_dims:
                result += f"  top_dimension_ids: {top_dims}\n"

            # Also try to get transform parameters from the transforms_ member
            params_list = []
            try:
                transforms_tuple = self.val['transforms_']
                params_list = self.extract_transform_parameters(transforms_tuple)
            except Exception as e:
                # Silent failure - transforms_ member might not exist
                pass

            # Display transforms
            if transforms:
                result += "\n  Transforms:\n"
                for i, (transform, lower, upper) in enumerate(zip(transforms, lower_dims_list, upper_dims_list)):
                    result += f"    [{i}] {transform}\n"
                    if lower:
                        result += f"        lower: {lower}\n"
                    if upper:
                        result += f"        upper: {upper}\n"

                    # Parameters (lengths)
                    if i < len(params_list) and params_list[i]:
                        for key, val in params_list[i].items():
                            result += f"        {key}: {val}\n"

            result += "}"
            return result

        except Exception as e:
            return f"tensor_adaptor{{error: {str(e)}}}"

    def extract_transform_info_from_type(self, type_str):
        """Extract transform information from tensor_adaptor type string"""
        transforms = []
        lower_dims = []
        upper_dims = []

        # Find tensor_adaptor content
        adaptor_start = type_str.find('tensor_adaptor<')
        if adaptor_start == -1:
            return transforms, lower_dims, upper_dims

        # Extract content between angle brackets
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

        # Parse the three tuples (same as tensor_descriptor)
        if adaptor_content.startswith('ck_tile::tuple<'):
            # Parse transforms tuple
            start = len('ck_tile::tuple<')
            bracket_count = 1
            end = start
            while bracket_count > 0 and end < len(adaptor_content):
                if adaptor_content[end] == '<':
                    bracket_count += 1
                elif adaptor_content[end] == '>':
                    bracket_count -= 1
                end += 1

            transforms_str = adaptor_content[start:end-1]

            # Parse transforms
            pos = 0
            while pos < len(transforms_str):
                found_transform = False

                transform_patterns = [
                    ('ck_tile::embed<', 'embed'),
                    ('embed<', 'embed'),
                    ('ck_tile::unmerge<', 'unmerge'),
                    ('unmerge<', 'unmerge'),
                    ('ck_tile::merge_v2_magic_division<', 'merge_v2'),
                    ('merge_v2_magic_division<', 'merge_v2'),
                    ('ck_tile::merge<', 'merge'),
                    ('merge<', 'merge'),
                    ('ck_tile::replicate<', 'replicate'),
                    ('replicate<', 'replicate'),
                    ('ck_tile::pass_through<', 'pass_through'),
                    ('pass_through<', 'pass_through'),
                    ('ck_tile::right_pad<', 'right_pad'),
                    ('right_pad<', 'right_pad'),
                    ('ck_tile::left_pad<', 'left_pad'),
                    ('left_pad<', 'left_pad'),
                    ('ck_tile::slice<', 'slice'),
                    ('slice<', 'slice'),
                    ('ck_tile::freeze<', 'freeze'),
                    ('freeze<', 'freeze')
                ]

                for pattern, name in transform_patterns:
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
                        # Skip any trailing comma and whitespace
                        while pos < len(transforms_str) and transforms_str[pos] in ', \t\n':
                            pos += 1
                        found_transform = True
                        break

                if not found_transform:
                    pos += 1

            # Now parse lower and upper dimension sequences
            # Skip the transforms tuple and find the next two tuples
            remaining = adaptor_content[end:].lstrip(', ')

            # Parse lower dimensions tuple
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

                # Extract sequences from lower dims (handle empty sequences)
                # First check for empty sequences
                empty_seqs = re.findall(r'sequence<\s*>', lower_dims_str)
                seqs = re.findall(r'sequence<([\d,\s-]+)>', lower_dims_str)

                # Count total sequences (empty + non-empty)
                total_seqs = len(empty_seqs) + len(seqs)

                # Process in order - we need to maintain the sequence order
                seq_matches = re.finditer(r'sequence<([^>]*)>', lower_dims_str)
                for match in seq_matches:
                    content = match.group(1).strip()
                    if content:
                        dims = [int(x.strip()) for x in content.split(',') if x.strip().lstrip('-').isdigit()]
                        lower_dims.append(dims)
                    else:
                        # Empty sequence
                        lower_dims.append([])

                # Parse upper dimensions tuple
                remaining = remaining[end:].lstrip(', ')
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

                    # Extract sequences from upper dims (handle empty sequences)
                    seq_matches = re.finditer(r'sequence<([^>]*)>', upper_dims_str)
                    for match in seq_matches:
                        content = match.group(1).strip()
                        if content:
                            dims = [int(x.strip()) for x in content.split(',') if x.strip().lstrip('-').isdigit()]
                            upper_dims.append(dims)
                        else:
                            # Empty sequence
                            upper_dims.append([])

        return transforms, lower_dims, upper_dims

    def extract_transform_parameters(self, transforms_tuple):
        """Extract parameters from the transforms_ tuple member"""
        params_list = []

        try:
            # Extract all transforms from the tuple using the module-level function
            transforms = extract_tuple_elements(transforms_tuple)

            for transform in transforms:
                params = {}

                # For embed, unmerge, merge, etc - try to get up_lengths
                try:
                    up_lengths_tuple = transform['up_lengths_']
                    lengths = extract_tuple_elements(up_lengths_tuple)
                    if lengths:
                        params['up_lengths'] = lengths
                except:
                    pass

                # Try to get low_lengths
                try:
                    low_lengths_tuple = transform['low_lengths_']
                    lengths = extract_tuple_elements(low_lengths_tuple)
                    if lengths:
                        params['low_lengths'] = lengths
                except:
                    pass

                # Try to get coefficients (for embed)
                try:
                    coefficients_tuple = transform['coefficients_']
                    coeffs = extract_tuple_elements(coefficients_tuple)
                    if coeffs:
                        params['coefficients'] = coeffs
                except:
                    pass

                params_list.append(params)

        except:
            pass

        return params_list

    def extract_bottom_top_dims_adaptor(self, type_str):
        """Extract bottom and top dimension IDs from tensor_adaptor"""
        # In tensor_adaptor, the last two sequences are BottomDimensionIds and TopDimensionIds
        # Find all sequences after the three tuples

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

                bottom_dims = [int(x.strip()) for x in bottom_str.split(',') if x.strip().lstrip('-').isdigit()]
                top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]

                return bottom_dims, top_dims

        return [], []

class CKTileTensorViewPrinter:
    """Pretty printer for ck_tile::tensor_view"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_view{\n"

            # Extract data type
            if '_Float16' in type_str:
                result += "  data_type: float16\n"
            elif 'float' in type_str:
                result += "  data_type: float\n"
            elif 'double' in type_str:
                result += "  data_type: double\n"
            elif 'int' in type_str:
                result += "  data_type: int\n"

            # Check for const
            if 'const ' in type_str:
                result += "  const: true\n"

            # Access descriptor
            try:
                desc = self.val['desc_']

                # Use tensor_descriptor printer
                desc_printer = CKTileTensorDescriptorPrinter(desc)
                desc_str = desc_printer.to_string()

                result += "\n  descriptor: "
                result += desc_str.replace('\n', '\n  ')
                result += "\n"

            except Exception as e:
                result += f"  descriptor: [error: {str(e)}]\n"

            # Check for buffer_view
            try:
                buf_view = self.val['buf_view_']
                buf_type = str(buf_view.type)

                if 'buffer_view' in buf_type:
                    result += "\n  buffer_view: {\n"

                    # Check address space
                    if 'address_space_enum)1' in buf_type:
                        result += "    address_space: global\n"
                    elif 'address_space_enum)3' in buf_type:
                        result += "    address_space: lds\n"

                    result += "  }\n"

            except:
                pass

            result += "}"
            return result

        except Exception as e:
            return f"tensor_view{{error: {str(e)}}}"

class CKTileTileDistributionPrinter:
    """Pretty printer for ck_tile::tile_distribution"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tile_distribution{\n"

            # Extract encoding information
            encoding_info = self.extract_encoding_info(type_str)
            if encoding_info:
                result += f"  encoding: {encoding_info}\n"

            # Access ps_ys_to_xs_ (PsYs2XsAdaptor)
            try:
                ps_ys_to_xs = self.val['ps_ys_to_xs_']
                ps_type = str(ps_ys_to_xs.type)

                result += "\n  ps_ys_to_xs_: "

                # Use tensor_adaptor printer if it's a tensor_adaptor
                if 'tensor_adaptor' in ps_type:
                    adaptor_printer = CKTileTensorAdaptorPrinter(ps_ys_to_xs)
                    adaptor_str = adaptor_printer.to_string()
                    result += adaptor_str.replace('\n', '\n  ')
                else:
                    result += "{\n"
                    result += f"    type: {ps_type[:50]}...\n"
                    result += "  }"

                result += "\n"

            except Exception as e:
                result += f"  ps_ys_to_xs_: [error: {str(e)}]\n"

            # Access ys_to_d_ (Ys2DDescriptor)
            try:
                ys_to_d = self.val['ys_to_d_']

                # Use tensor_descriptor printer
                desc_printer = CKTileTensorDescriptorPrinter(ys_to_d)
                desc_str = desc_printer.to_string()

                result += "\n  ys_to_d_: "
                result += desc_str.replace('\n', '\n  ')
                result += "\n"

            except Exception as e:
                result += f"  ys_to_d_: [error: {str(e)}]\n"

            result += "}"
            return result

        except Exception as e:
            return f"tile_distribution{{error: {str(e)}}}"

    def extract_encoding_info(self, type_str):
        """Extract comprehensive tile_distribution_encoding information"""
        if 'tile_distribution_encoding' not in type_str:
            return None

        # Find the full encoding content
        encoding_start = type_str.find('tile_distribution_encoding<')
        if encoding_start == -1:
            return None

        pos = encoding_start + len('tile_distribution_encoding<')
        bracket_count = 1
        end = pos
        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        encoding_content = type_str[pos:end-1]

        result = "{\n"

        # Parse RsLengths (first sequence not in a tuple)
        rs_lengths = []
        rs_match = re.search(r'^ck_tile::sequence<([\d,\s-]+)>', encoding_content)
        if not rs_match:
            rs_match = re.search(r',\s*ck_tile::sequence<([\d,\s-]+)>', encoding_content)

        if rs_match:
            rs_str = rs_match.group(1)
            rs_lengths = [int(x.strip()) for x in rs_str.split(',') if x.strip().lstrip('-').isdigit()]
            result += f"    RsLengths: {rs_lengths}\n"

        # Parse HsLengthss (first tuple of sequences)
        hs_lengthss = []
        hs_start = encoding_content.find('ck_tile::tuple<')
        if hs_start != -1:
            # Extract the first tuple
            pos = hs_start + len('ck_tile::tuple<')
            bracket_count = 1
            tuple_end = pos
            while bracket_count > 0 and tuple_end < len(encoding_content):
                if encoding_content[tuple_end] == '<':
                    bracket_count += 1
                elif encoding_content[tuple_end] == '>':
                    bracket_count -= 1
                tuple_end += 1

            hs_content = encoding_content[hs_start + len('ck_tile::tuple<'):tuple_end-1]
            hs_seqs = re.findall(r'sequence<([\d,\s-]+)>', hs_content)

            if hs_seqs:
                result += "    HsLengthss: ["
                for i, seq in enumerate(hs_seqs):
                    dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                    hs_lengthss.append(dims)
                    if i > 0:
                        result += ", "
                    result += str(dims)
                result += "]\n"

        # Parse all tuples to find Ps2RHss and dimension mappings
        all_tuples = []
        tuple_start = 0
        while True:
            tuple_start = encoding_content.find('ck_tile::tuple<', tuple_start)
            if tuple_start == -1:
                break

            pos = tuple_start + len('ck_tile::tuple<')
            bracket_count = 1
            tuple_end = pos
            while bracket_count > 0 and tuple_end < len(encoding_content):
                if encoding_content[tuple_end] == '<':
                    bracket_count += 1
                elif encoding_content[tuple_end] == '>':
                    bracket_count -= 1
                tuple_end += 1

            tuple_content = encoding_content[tuple_start + len('ck_tile::tuple<'):tuple_end-1]
            seqs = re.findall(r'sequence<([\d,\s-]+)>', tuple_content)

            if seqs:
                parsed_seqs = []
                for seq in seqs:
                    dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                    parsed_seqs.append(dims)
                all_tuples.append(parsed_seqs)

            tuple_start = tuple_end

        # Ps2RHssMajor and Minor (tuples 2 and 3)
        ps_major = []
        ps_minor = []
        if len(all_tuples) > 1:
            ps_major = all_tuples[1]
        if len(all_tuples) > 2:
            ps_minor = all_tuples[2]

        # Find standalone sequences at the end (Ys2RHs)
        # These are sequences not inside tuples
        standalone_seqs = []
        pos = 0
        in_tuple = False
        while pos < len(encoding_content):
            if encoding_content[pos:].startswith('ck_tile::tuple<'):
                # Skip the entire tuple
                bracket_count = 1
                pos += len('ck_tile::tuple<')
                while bracket_count > 0 and pos < len(encoding_content):
                    if encoding_content[pos] == '<':
                        bracket_count += 1
                    elif encoding_content[pos] == '>':
                        bracket_count -= 1
                    pos += 1
            elif encoding_content[pos:].startswith('ck_tile::sequence<'):
                # Found a standalone sequence
                seq_start = pos + len('ck_tile::sequence<')
                seq_end = encoding_content.find('>', seq_start)
                if seq_end != -1:
                    seq_content = encoding_content[seq_start:seq_end]
                    dims = [int(x.strip()) for x in seq_content.split(',') if x.strip().lstrip('-').isdigit()]
                    if dims:
                        standalone_seqs.append(dims)
                    pos = seq_end + 1
                else:
                    pos += 1
            else:
                pos += 1

        # The last standalone sequences are Ys2RHs
        ys_major = []
        ys_minor = []
        if len(standalone_seqs) >= 2:
            ys_major = standalone_seqs[-2]
            ys_minor = standalone_seqs[-1]

        # Helper function to get length from RH major/minor
        def get_rh_length(rh_major, rh_minor):
            if rh_major == 0:
                # R dimension
                if rh_minor < len(rs_lengths):
                    return rs_lengths[rh_minor]
            else:
                # H dimension (major-1 is the index into HsLengthss)
                h_idx = rh_major - 1
                if h_idx < len(hs_lengthss) and rh_minor < len(hs_lengthss[h_idx]):
                    return hs_lengthss[h_idx][rh_minor]
            return None

        # Display raw encoding sequences first
        if ps_major and ps_minor:
            result += f"    Ps2RHssMajor: {ps_major}\n"
            result += f"    Ps2RHssMinor: {ps_minor}\n"

        if ys_major and ys_minor:
            result += f"    Ys2RHsMajor: {ys_major}\n"
            result += f"    Ys2RHsMinor: {ys_minor}\n"

        # Display Ps mappings with lengths
        if ps_major and ps_minor:
            result += "    Ps mappings (with lengths):\n"
            for p_idx in range(len(ps_major)):
                if p_idx < len(ps_major) and p_idx < len(ps_minor):
                    p_major_seq = ps_major[p_idx]
                    p_minor_seq = ps_minor[p_idx]
                    result += f"      P[{p_idx}]:\n"
                    for i, (maj, min_) in enumerate(zip(p_major_seq, p_minor_seq)):
                        length = get_rh_length(maj, min_)
                        if maj == 0:
                            result += f"        -> R[{min_}]"
                        else:
                            result += f"        -> H{maj-1}[{min_}]"
                        if length is not None:
                            result += f" (length={length})"
                        result += "\n"

        # Display Ys mappings with lengths
        if ys_major and ys_minor:
            result += "    Ys mappings (with lengths):\n"
            for y_idx in range(len(ys_major)):
                if y_idx < len(ys_major) and y_idx < len(ys_minor):
                    maj = ys_major[y_idx]
                    min_ = ys_minor[y_idx]
                    length = get_rh_length(maj, min_)
                    if maj == 0:
                        result += f"      Y[{y_idx}] -> R[{min_}]"
                    else:
                        result += f"      Y[{y_idx}] -> H{maj-1}[{min_}]"
                    if length is not None:
                        result += f" (length={length})"
                    result += "\n"

        result += "  }"
        return result

class CKTileTensorAdaptorCoordinatePrinter:
    """Pretty printer for ck_tile::tensor_adaptor_coordinate"""

    def __init__(self, val):
        self.val = val

    def extract_dimension_ids_from_type(self, type_str):
        """Extract NDimHidden, BottomDimensionHiddenIds and TopDimensionHiddenIds from type"""
        # tensor_adaptor_coordinate<NDimHidden, BottomDimensionHiddenIds, TopDimensionHiddenIds>

        # Find tensor_adaptor_coordinate content
        coord_start = type_str.find('tensor_adaptor_coordinate<')
        if coord_start == -1:
            return 0, [], []

        pos = coord_start + len('tensor_adaptor_coordinate<')
        bracket_count = 1
        end = pos
        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        coord_content = type_str[pos:end-1]

        # Extract NDimHidden (first template parameter)
        ndim_hidden = 0
        first_comma = coord_content.find(',')
        if first_comma != -1:
            ndim_str = coord_content[:first_comma].strip()
            if ndim_str.isdigit():
                ndim_hidden = int(ndim_str)

        # Find all sequences in the template parameters
        seqs = re.findall(r'ck_tile::sequence<([^>]*)>', coord_content)

        bottom_dims = []
        top_dims = []

        if len(seqs) >= 2:
            # Second-to-last sequence is BottomDimensionHiddenIds
            bottom_str = seqs[-2]
            if bottom_str.strip():
                bottom_dims = [int(x.strip()) for x in bottom_str.split(',') if x.strip().lstrip('-').isdigit()]

            # Last sequence is TopDimensionHiddenIds
            top_str = seqs[-1]
            if top_str.strip():
                top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]

        return ndim_hidden, bottom_dims, top_dims

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_adaptor_coordinate{\n"

            # Extract dimension IDs and NDimHidden
            ndim_hidden, bottom_dim_ids, top_dim_ids = self.extract_dimension_ids_from_type(type_str)

            # Access idx_hidden_ member
            hidden_vals = []
            try:
                idx_hidden = self.val['idx_hidden_']

                # Try to get the data member of multi_index
                try:
                    data = idx_hidden['data']
                    # Extract values from array (only NDimHidden elements)
                    max_dims = ndim_hidden if ndim_hidden > 0 else 20
                    for i in range(max_dims):
                        try:
                            val = int(data[i])
                            hidden_vals.append(val)
                        except:
                            break
                except:
                    # Try direct indexing
                    max_dims = ndim_hidden if ndim_hidden > 0 else 20
                    for i in range(max_dims):
                        try:
                            val = int(idx_hidden[i])
                            hidden_vals.append(val)
                        except:
                            break

            except Exception as e:
                result += f"  [error accessing idx_hidden_: {str(e)}]\n"

            # Show the full data array (only valid NDimHidden elements)
            if hidden_vals:
                result += f"  idx_hidden_ (data): {hidden_vals}\n"

            # Show dimension IDs and computed indices
            if bottom_dim_ids:
                result += f"  bottom_dimension_ids: {bottom_dim_ids}\n"
            if top_dim_ids:
                result += f"  top_dimension_ids: {top_dim_ids}\n"

            if hidden_vals:
                # Show computed top index (subset of hidden index using top_dim_ids)
                if top_dim_ids:
                    top_vals = [hidden_vals[i] for i in top_dim_ids if i < len(hidden_vals)]
                    result += f"  top_index: {top_vals}\n"

                # Show computed bottom index (subset of hidden index using bottom_dim_ids)
                if bottom_dim_ids:
                    bottom_vals = [hidden_vals[i] for i in bottom_dim_ids if i < len(hidden_vals)]
                    result += f"  bottom_index: {bottom_vals}\n"

            result += "}"
            return result

        except Exception as e:
            return f"tensor_adaptor_coordinate{{error: {str(e)}}}"

class CKTileTensorCoordinatePrinter:
    """Pretty printer for ck_tile::tensor_coordinate"""

    def __init__(self, val):
        self.val = val

    def extract_top_dimension_ids_from_type(self, type_str):
        """Extract NDimHidden and TopDimensionHiddenIds from type"""
        # tensor_coordinate<NDimHidden, TopDimensionHiddenIds>
        # Inherits from tensor_adaptor_coordinate<NDimHidden, sequence<0>, TopDimensionHiddenIds>

        # Find tensor_coordinate content
        coord_start = type_str.find('tensor_coordinate<')
        if coord_start == -1:
            return 0, []

        pos = coord_start + len('tensor_coordinate<')
        bracket_count = 1
        end = pos
        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        coord_content = type_str[pos:end-1]

        # Extract NDimHidden (first template parameter)
        ndim_hidden = 0
        first_comma = coord_content.find(',')
        if first_comma != -1:
            ndim_str = coord_content[:first_comma].strip()
            if ndim_str.isdigit():
                ndim_hidden = int(ndim_str)

        # Find all sequences in the template parameters
        seqs = re.findall(r'ck_tile::sequence<([^>]*)>', coord_content)

        top_dims = []

        if len(seqs) >= 1:
            # Last sequence is TopDimensionHiddenIds
            top_str = seqs[-1]
            if top_str.strip():
                top_dims = [int(x.strip()) for x in top_str.split(',') if x.strip().lstrip('-').isdigit()]

        return ndim_hidden, top_dims

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_coordinate{\n"

            # Extract dimension IDs and NDimHidden
            ndim_hidden, top_dim_ids = self.extract_top_dimension_ids_from_type(type_str)

            # Access idx_hidden_ member (inherited from base)
            hidden_vals = []
            try:
                idx_hidden = self.val['idx_hidden_']

                # Try to get the data member of multi_index
                try:
                    data = idx_hidden['data']
                    # Extract values from array (only NDimHidden elements)
                    max_dims = ndim_hidden if ndim_hidden > 0 else 20
                    for i in range(max_dims):
                        try:
                            val = int(data[i])
                            hidden_vals.append(val)
                        except:
                            break
                except:
                    # Try direct indexing
                    max_dims = ndim_hidden if ndim_hidden > 0 else 20
                    for i in range(max_dims):
                        try:
                            val = int(idx_hidden[i])
                            hidden_vals.append(val)
                        except:
                            break

            except Exception as e:
                result += f"  [error accessing idx_hidden_: {str(e)}]\n"

            # Show the full data array (only valid NDimHidden elements)
            if hidden_vals:
                result += f"  idx_hidden_ (data): {hidden_vals}\n"

            # Show dimension IDs
            result += f"  bottom_dimension_ids: [0]\n"
            if top_dim_ids:
                result += f"  top_dimension_ids: {top_dim_ids}\n"

            if hidden_vals:
                # Show index (top index)
                if top_dim_ids:
                    top_vals = [hidden_vals[i] for i in top_dim_ids if i < len(hidden_vals)]
                    result += f"  index (top): {top_vals}\n"

                # Show offset (bottom_index[0])
                if len(hidden_vals) > 0:
                    result += f"  offset (bottom[0]): {hidden_vals[0]}\n"

            result += "}"
            return result

        except Exception as e:
            return f"tensor_coordinate{{error: {str(e)}}}"

class CKTileTileDistributionEncodingPrinter:
    """Pretty printer for ck_tile::tile_distribution_encoding"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tile_distribution_encoding{\n"

            # Extract template parameters
            encoding_match = re.search(r'tile_distribution_encoding<(.*)>', type_str)
            if not encoding_match:
                return "tile_distribution_encoding{}"

            content = encoding_match.group(1)

            # Parse RsLengths (first sequence)
            rs_match = re.search(r'^ck_tile::sequence<([\d,\s-]+)>', content)
            if rs_match:
                rs_str = rs_match.group(1)
                rs_lengths = [int(x.strip()) for x in rs_str.split(',') if x.strip().lstrip('-').isdigit()]
                result += f"  RsLengths: {rs_lengths}\n"
                result += f"  NDimR: {len(rs_lengths)}\n"

            # Parse HsLengthss (first tuple of sequences)
            hs_start = content.find('ck_tile::tuple<')
            if hs_start != -1:
                # Extract the first tuple
                pos = hs_start + len('ck_tile::tuple<')
                bracket_count = 1
                end = pos
                while bracket_count > 0 and end < len(content):
                    if content[end] == '<':
                        bracket_count += 1
                    elif content[end] == '>':
                        bracket_count -= 1
                    end += 1

                hs_content = content[hs_start + len('ck_tile::tuple<'):end-1]
                hs_seqs = re.findall(r'sequence<([\d,\s-]+)>', hs_content)

                result += f"  HsLengthss: [\n"
                for i, seq in enumerate(hs_seqs):
                    dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                    result += f"    [{i}]: {dims}\n"
                result += "  ]\n"
                result += f"  NDimX: {len(hs_seqs)}\n"

            # Parse Ps2RHssMajor and Ps2RHssMinor
            # These are the second and third tuples
            tuples = re.findall(r'ck_tile::tuple<(ck_tile::sequence<[\d,\s-]+>(?:,\s*ck_tile::sequence<[\d,\s-]+>)*)>', content)
            if len(tuples) >= 3:
                # Ps2RHssMajor (second tuple)
                ps_major_seqs = re.findall(r'sequence<([\d,\s-]+)>', tuples[1])
                result += f"  Ps2RHssMajor: [\n"
                for i, seq in enumerate(ps_major_seqs):
                    dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                    result += f"    P[{i}] -> RH_major: {dims}\n"
                result += "  ]\n"
                result += f"  NDimP: {len(ps_major_seqs)}\n"

                # Ps2RHssMinor (third tuple)
                if len(tuples) >= 3:
                    ps_minor_seqs = re.findall(r'sequence<([\d,\s-]+)>', tuples[2])
                    result += f"  Ps2RHssMinor: [\n"
                    for i, seq in enumerate(ps_minor_seqs):
                        dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                        result += f"    P[{i}] -> RH_minor: {dims}\n"
                    result += "  ]\n"

            # Parse Ys2RHsMajor and Ys2RHsMinor (last two sequences not in tuples)
            # Find sequences after the tuples
            last_seqs = []
            pos = 0
            while pos < len(content):
                # Skip tuples
                if content[pos:].startswith('ck_tile::tuple<'):
                    bracket_count = 1
                    pos += len('ck_tile::tuple<')
                    while bracket_count > 0 and pos < len(content):
                        if content[pos] == '<':
                            bracket_count += 1
                        elif content[pos] == '>':
                            bracket_count -= 1
                        pos += 1
                # Find standalone sequences
                elif content[pos:].startswith('ck_tile::sequence<'):
                    seq_start = pos + len('ck_tile::sequence<')
                    seq_end = content.find('>', seq_start)
                    if seq_end != -1:
                        seq_content = content[seq_start:seq_end]
                        if seq_content not in ['']:  # Skip empty sequences
                            last_seqs.append(seq_content)
                        pos = seq_end + 1
                else:
                    pos += 1

            # The last two non-tuple sequences are Ys2RHsMajor and Ys2RHsMinor
            if len(last_seqs) >= 2:
                ys_major = last_seqs[-2]
                ys_minor = last_seqs[-1]

                ys_major_dims = [int(x.strip()) for x in ys_major.split(',') if x.strip().lstrip('-').isdigit()]
                ys_minor_dims = [int(x.strip()) for x in ys_minor.split(',') if x.strip().lstrip('-').isdigit()]

                result += f"  Ys2RHsMajor: {ys_major_dims}\n"
                result += f"  Ys2RHsMinor: {ys_minor_dims}\n"
                result += f"  NDimY: {len(ys_major_dims)}\n"

            result += "}"
            return result

        except Exception as e:
            return f"tile_distribution_encoding{{error: {str(e)}}}"

class CKTileTileWindowPrinter:
    """Pretty printer for tile_window types"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Determine window type
            if 'tile_window_with_static_distribution' in type_str:
                window_type = "tile_window_with_static_distribution"
            elif 'tile_window_with_static_lengths' in type_str:
                window_type = "tile_window_with_static_lengths"
            else:
                window_type = "tile_window"

            result = f"{window_type}{{\n"

            # Extract data type
            if '_Float16' in type_str:
                result += "  data_type: float16\n"
            elif 'float' in type_str:
                result += "  data_type: float\n"
            elif 'double' in type_str:
                result += "  data_type: double\n"

            # Extract window dimensions
            dims_match = re.findall(r'constant<(\d+)>', type_str)
            if dims_match and len(dims_match) >= 2:
                result += f"  window_dims: [{dims_match[0]} x {dims_match[1]}]\n"

            # For static_distribution, access tile_dstr_
            if 'static_distribution' in window_type:
                try:
                    tile_dstr = self.val['tile_dstr_']

                    # Use tile_distribution printer
                    dstr_printer = CKTileTileDistributionPrinter(tile_dstr)
                    dstr_str = dstr_printer.to_string()

                    result += "\n  tile_dstr_: "
                    result += dstr_str.replace('\n', '\n  ')
                    result += "\n"

                except Exception as e:
                    result += f"  tile_dstr_: [error: {str(e)}]\n"

            # Access bottom_tensor_view
            try:
                bottom_view = self.val['bottom_tensor_view_']

                # Use tensor_view printer
                view_printer = CKTileTensorViewPrinter(bottom_view)
                view_str = view_printer.to_string()

                result += "\n  bottom_tensor_view_: "
                result += view_str.replace('\n', '\n  ')
                result += "\n"

            except:
                pass

            # Check for pre_computed_coords
            try:
                coords = self.val['pre_computed_coords_']
                result += "\n  pre_computed_coords_: present\n"
            except:
                pass

            result += "}"
            return result

        except Exception as e:
            return f"{window_type}{{error: {str(e)}}}"

class CKTileStaticDistributedTensorPrinter:
    """Pretty printer for ck_tile::static_distributed_tensor"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "static_distributed_tensor{\n"

            # Extract data type
            if '_Float16' in type_str:
                result += "  data_type: float16\n"
            elif 'float' in type_str:
                result += "  data_type: float\n"
            elif 'double' in type_str:
                result += "  data_type: double\n"

            # Extract shape
            encoding_match = re.search(r'tile_distribution_encoding<[^>]*tuple<ck_tile::sequence<([\d,\s]+)>', type_str)
            if encoding_match:
                shape_str = encoding_match.group(1)
                shape = [int(x.strip()) for x in shape_str.split(',') if x.strip().isdigit()]
                if shape:
                    result += f"  shape: {shape}\n"

            # Check distribution pattern
            if 'replicate' in type_str:
                result += "  distribution: replicated\n"
            elif 'unmerge' in type_str:
                unmerge_match = re.search(r'unmerge<ck_tile::tuple<([^>]+)>', type_str)
                if unmerge_match:
                    params_str = unmerge_match.group(1)
                    consts = re.findall(r'constant<(\d+)>', params_str)
                    if consts:
                        result += f"  distribution: unmerged {consts}\n"
            elif 'merge' in type_str:
                result += "  distribution: merged\n"

            # Try to get thread buffer size
            try:
                thread_buf = self.val['thread_buf_']
                buf_type_str = str(thread_buf.type)
                size_match = re.search(r'thread_buffer<[^,]+,\s*(\d+)', buf_type_str)
                if size_match:
                    buffer_size = int(size_match.group(1))
                    result += f"  thread_buffer_size: {buffer_size}\n"
            except:
                pass

            result += "}"
            return result

        except Exception as e:
            return f"static_distributed_tensor{{error: {str(e)}}}"

def build_pretty_printer():
    pp = gdb.printing.RegexpCollectionPrettyPrinter("ck_tile")

    # Register all pretty printers
    pp.add_printer('tensor_descriptor', '^ck_tile::tensor_descriptor<.*>$', CKTileTensorDescriptorPrinter)
    pp.add_printer('tensor_adaptor', '^ck_tile::tensor_adaptor<.*>$', CKTileTensorAdaptorPrinter)
    pp.add_printer('tensor_adaptor_coordinate', '^ck_tile::tensor_adaptor_coordinate<.*>$', CKTileTensorAdaptorCoordinatePrinter)
    pp.add_printer('tensor_coordinate', '^ck_tile::tensor_coordinate<.*>$', CKTileTensorCoordinatePrinter)
    pp.add_printer('tensor_view', '^ck_tile::tensor_view<.*>$', CKTileTensorViewPrinter)
    pp.add_printer('tile_distribution', '^ck_tile::tile_distribution<.*>$', CKTileTileDistributionPrinter)
    pp.add_printer('tile_distribution_encoding', '^ck_tile::tile_distribution_encoding<.*>$', CKTileTileDistributionEncodingPrinter)
    pp.add_printer('tile_window_with_static_distribution', '^ck_tile::tile_window_with_static_distribution<.*>$', CKTileTileWindowPrinter)
    pp.add_printer('tile_window_with_static_lengths', '^ck_tile::tile_window_with_static_lengths<.*>$', CKTileTileWindowPrinter)
    pp.add_printer('tile_window', '^ck_tile::tile_window<.*>$', CKTileTileWindowPrinter)
    pp.add_printer('static_distributed_tensor', '^ck_tile::static_distributed_tensor<.*>$', CKTileStaticDistributedTensorPrinter)

    return pp

def register_printers(obj):
    gdb.printing.register_pretty_printer(obj, build_pretty_printer(), replace=True)

# Register the printers
try:
    register_printers(None)
    print("CK-Tile pretty printers registered successfully")
    print("Registered printers for: tensor_descriptor, tensor_adaptor, tensor_adaptor_coordinate, tensor_coordinate,")
    print("  tensor_view, tile_distribution, tile_distribution_encoding, tile_window, static_distributed_tensor")
except Exception as e:
    print(f"Failed to register pretty printers: {e}")