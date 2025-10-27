#!/usr/bin/env python3
"""
Compare GDB pretty printer outputs for structural equivalence.

This tool compares test outputs with golden outputs to detect regressions.
It performs structural comparison rather than exact string matching, allowing
for minor formatting differences.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def extract_test_sections(output: str) -> Dict[str, str]:
    """
    Extract individual test sections from GDB output.

    Returns a dictionary mapping test names to their output.
    """
    sections = {}
    # Pattern to match test markers
    pattern = r'===\s+TEST\s+(\d+):\s+([^=]+)\s+===\s*\n(.*?)(?====\s+TEST|$)'

    matches = re.finditer(pattern, output, re.DOTALL)
    for match in matches:
        test_num = match.group(1)
        test_name = match.group(2).strip()
        test_output = match.group(3).strip()

        # Clean up the output - remove gdb prompts and values like $1 =
        test_output = re.sub(r'\$\d+\s*=\s*', '', test_output)

        sections[f"TEST_{test_num}_{test_name}"] = test_output

    return sections


def normalize_output(text: str) -> str:
    """
    Normalize output for comparison.

    Removes whitespace variations and other non-semantic differences.
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove trailing/leading whitespace
    text = text.strip()
    return text


def extract_structure(text: str) -> List[str]:
    """
    Extract structural elements from pretty printer output.

    Returns a list of key structural features:
    - Container types (tuple, array, etc.)
    - Element counts
    - Nested types (tensor_view, tensor_descriptor, etc.)
    - Key fields (data_type, ntransform, etc.)
    """
    features = []

    # Extract container types and element counts
    container_match = re.search(r'(tuple|array|multi_index|thread_buffer)<(\d+)\s+elements?>', text)
    if container_match:
        features.append(f"{container_match.group(1)}_count_{container_match.group(2)}")

    # Extract nested type names
    type_patterns = [
        r'tensor_view',
        r'tensor_descriptor',
        r'tensor_adaptor',
        r'tile_window_with_static_lengths',
        r'tile_window_with_static_distribution',
        r'tile_window\s',
    ]

    for pattern in type_patterns:
        matches = re.findall(pattern, text)
        if matches:
            pattern_name = pattern.replace(r'\s', '')
            features.append(f"{pattern_name}_count_{len(matches)}")

    # Extract key numeric fields
    numeric_fields = [
        r'ntransform:\s*(\d+)',
        r'ndim_hidden:\s*(\d+)',
        r'ndim_top:\s*(\d+)',
        r'ndim_bottom:\s*(\d+)',
        r'window_dims:\s*\[([^\]]+)\]',
    ]

    for pattern in numeric_fields:
        matches = re.findall(pattern, text)
        if matches:
            field_name = pattern.split(':')[0].replace(r'\s*', '').replace('r\'', '')
            features.append(f"{field_name}={matches}")

    # Extract transform types
    transform_types = re.findall(r'\[\d+\]\s+(embed|pass_through|merge|freeze|unmerge)', text)
    if transform_types:
        features.append(f"transforms={','.join(transform_types)}")

    return features


def compare_structures(golden: str, test: str) -> Tuple[bool, List[str]]:
    """
    Compare two outputs structurally.

    Returns:
        (matches: bool, differences: List[str])
    """
    golden_features = extract_structure(golden)
    test_features = extract_structure(test)

    differences = []

    # Check for missing features
    for feature in golden_features:
        if feature not in test_features:
            differences.append(f"Missing in test: {feature}")

    # Check for extra features
    for feature in test_features:
        if feature not in golden_features:
            differences.append(f"Extra in test: {feature}")

    return len(differences) == 0, differences


def compare_outputs(golden_file: Path, test_file: Path) -> int:
    """
    Compare golden and test outputs.

    Returns:
        0 if outputs match, 1 if they differ, 2 if error
    """
    try:
        golden_text = golden_file.read_text()
        test_text = test_file.read_text()
    except Exception as e:
        print(f"Error reading files: {e}", file=sys.stderr)
        return 2

    golden_sections = extract_test_sections(golden_text)
    test_sections = extract_test_sections(test_text)

    if not golden_sections:
        print("Warning: No test sections found in golden output", file=sys.stderr)
        return 2

    if not test_sections:
        print("Warning: No test sections found in test output", file=sys.stderr)
        return 2

    all_passed = True

    for test_name in sorted(golden_sections.keys()):
        if test_name not in test_sections:
            print(f"❌ {test_name}: Missing in test output")
            all_passed = False
            continue

        golden_out = golden_sections[test_name]
        test_out = test_sections[test_name]

        # First try exact normalized match
        if normalize_output(golden_out) == normalize_output(test_out):
            print(f"✅ {test_name}: Exact match")
            continue

        # Try structural match
        matches, differences = compare_structures(golden_out, test_out)

        if matches:
            print(f"✅ {test_name}: Structural match (formatting differs)")
        else:
            print(f"❌ {test_name}: Structural differences found")
            for diff in differences:
                print(f"     {diff}")
            all_passed = False

    # Check for extra tests
    for test_name in test_sections.keys():
        if test_name not in golden_sections:
            print(f"⚠️  {test_name}: Extra test (not in golden output)")

    return 0 if all_passed else 1


def main():
    if len(sys.argv) != 3:
        print("Usage: compare_outputs.py <golden_file> <test_file>")
        print("\nCompares GDB pretty printer test outputs for structural equivalence.")
        return 2

    golden_file = Path(sys.argv[1])
    test_file = Path(sys.argv[2])

    if not golden_file.exists():
        print(f"Error: Golden file not found: {golden_file}", file=sys.stderr)
        return 2

    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", file=sys.stderr)
        return 2

    print(f"Comparing outputs:")
    print(f"  Golden: {golden_file}")
    print(f"  Test:   {test_file}")
    print()

    result = compare_outputs(golden_file, test_file)

    if result == 0:
        print("\n✅ All tests passed!")
    elif result == 1:
        print("\n❌ Some tests failed - see differences above")
    else:
        print("\n⚠️  Error during comparison")

    return result


if __name__ == "__main__":
    sys.exit(main())
