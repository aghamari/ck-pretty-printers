"""
Utilities for extracting elements from ck_tile::tuple structures in GDB.
Handles both compile-time constants and runtime values.
"""

import re
from .cpp_type_parser import extract_constant_value


def extract_tuple_elements(tuple_obj):
    """
    Generic function to extract all elements from a ck_tile::tuple.

    Handles both:
    - Compile-time constant values (ck_tile::constant<N>)
    - Runtime integer values
    - Complex objects (like transform objects)

    Args:
        tuple_obj: GDB value representing a ck_tile::tuple

    Returns:
        List of extracted elements (integers for simple values, GDB values for objects)

    Example:
        tuple<constant<8>, constant<128>, int> -> [8, 128, <runtime_int_value>]
    """
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

                                # Check if the ELEMENT type itself is EXACTLY ck_tile::constant<N>
                                # (not a complex type that HAS constants in its template params)
                                if element_type.startswith('ck_tile::constant<') and element_type.count('<') == 1:
                                    # It's a compile-time constant like: tuple<constant<8>, constant<16>>
                                    const_val = extract_constant_value(element_type)
                                    if const_val is not None:
                                        elements.append(const_val)
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
                            # Silent failure - continue to next element
                            pass
    except:
        # Silent failure - return what we have
        pass

    return elements


def extract_transform_parameters(transforms_tuple):
    """
    Extract parameters (up_lengths, low_lengths, coefficients) from transforms.

    Args:
        transforms_tuple: GDB value representing tuple of transform objects

    Returns:
        List of dicts, each containing parameters for one transform
        Example: [{'up_lengths': [8, 128], 'coefficients': [8, 1]}, ...]
    """
    params_list = []

    try:
        # Extract all transforms from the tuple
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
