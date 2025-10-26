"""
Utilities for parsing C++ template type strings.
Provides robust bracket counting and template parameter extraction.
"""

import re


def find_matching_bracket(text, start_pos, open_char='<', close_char='>'):
    """
    Find the position of the matching closing bracket.

    Args:
        text: The string to search
        start_pos: Position of the opening bracket
        open_char: Opening bracket character
        close_char: Closing bracket character

    Returns:
        Position of matching closing bracket, or -1 if not found
    """
    bracket_count = 1
    pos = start_pos + 1

    while pos < len(text) and bracket_count > 0:
        if text[pos] == open_char:
            bracket_count += 1
        elif text[pos] == close_char:
            bracket_count -= 1
        pos += 1

    return pos - 1 if bracket_count == 0 else -1


def extract_template_content(type_str, template_name):
    """
    Extract the content between angle brackets of a template.

    Args:
        type_str: The full type string
        template_name: Name of the template (e.g., 'tensor_descriptor', 'ck_tile::tuple')

    Returns:
        The content between < and > of the template, or empty string if not found

    Example:
        extract_template_content("tensor_descriptor<int, float>", "tensor_descriptor")
        -> "int, float"
    """
    # Find template start
    pattern = re.escape(template_name) + r'<'
    match = re.search(pattern, type_str)

    if not match:
        return ""

    start = match.end() - 1  # Position of '<'
    end = find_matching_bracket(type_str, start, '<', '>')

    if end == -1:
        return ""

    return type_str[start + 1:end]


def split_template_params(content):
    """
    Split template parameters by comma, respecting nested templates.

    Args:
        content: Template content string (without outer <>)

    Returns:
        List of parameter strings

    Example:
        split_template_params("int, tuple<float, double>, bool")
        -> ["int", "tuple<float, double>", "bool"]
    """
    params = []
    current_param = []
    bracket_count = 0

    for char in content:
        if char == '<':
            bracket_count += 1
            current_param.append(char)
        elif char == '>':
            bracket_count -= 1
            current_param.append(char)
        elif char == ',' and bracket_count == 0:
            # End of parameter
            params.append(''.join(current_param).strip())
            current_param = []
        else:
            current_param.append(char)

    # Add last parameter
    if current_param:
        params.append(''.join(current_param).strip())

    return params


def extract_sequences(content):
    """
    Extract all ck_tile::sequence<...> from content.

    Args:
        content: String to search

    Returns:
        List of sequence contents (without the sequence<> wrapper)

    Example:
        extract_sequences("sequence<1, 2>, other, sequence<3>")
        -> ["1, 2", "3"]
    """
    sequences = []
    pos = 0

    while pos < len(content):
        # Look for sequence<
        seq_patterns = ['ck_tile::sequence<', 'sequence<']
        found = False

        for pattern in seq_patterns:
            if content[pos:].startswith(pattern):
                start = pos + len(pattern) - 1  # Position of '<'
                end = find_matching_bracket(content, start, '<', '>')

                if end != -1:
                    seq_content = content[start + 1:end].strip()
                    sequences.append(seq_content)
                    pos = end + 1
                    found = True
                    break

        if not found:
            pos += 1

    return sequences


def extract_tuples(content):
    """
    Extract all ck_tile::tuple<...> from content.

    Args:
        content: String to search

    Returns:
        List of tuple contents (without the tuple<> wrapper)

    Example:
        extract_tuples("tuple<int, float>, other, tuple<double>")
        -> ["int, float", "double"]
    """
    tuples = []
    pos = 0

    while pos < len(content):
        # Look for tuple<
        tuple_patterns = ['ck_tile::tuple<', 'tuple<']
        found = False

        for pattern in tuple_patterns:
            if content[pos:].startswith(pattern):
                start = pos + len(pattern) - 1  # Position of '<'
                end = find_matching_bracket(content, start, '<', '>')

                if end != -1:
                    tuple_content = content[start + 1:end]
                    tuples.append(tuple_content)
                    pos = end + 1
                    found = True
                    break

        if not found:
            pos += 1

    return tuples


def extract_constant_value(type_str):
    """
    Extract the numeric value from a ck_tile::constant<N> type.

    Args:
        type_str: Type string containing constant<...>

    Returns:
        The integer value, or None if not a constant type

    Example:
        extract_constant_value("ck_tile::constant<8192l>") -> 8192
        extract_constant_value("int") -> None
    """
    match = re.search(r'constant<(\d+)[uUlL]*>', type_str)
    if match:
        return int(match.group(1))
    return None


def parse_sequence_values(seq_content):
    """
    Parse a sequence content string into list of integers.

    Args:
        seq_content: Content of sequence (e.g., "1, 2, 3" or "")

    Returns:
        List of integers, or empty list if sequence is empty

    Example:
        parse_sequence_values("1, 2, 3") -> [1, 2, 3]
        parse_sequence_values("") -> []
    """
    if not seq_content.strip():
        return []

    values = []
    for val in seq_content.split(','):
        val = val.strip()
        # Handle negative numbers too
        if val and val.lstrip('-').isdigit():
            values.append(int(val))

    return values
