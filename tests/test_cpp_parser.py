#!/usr/bin/env python3
"""Unit tests for cpp_type_parser utilities."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gdbinit_ck_tile.utils.cpp_type_parser import *


def test_find_matching_bracket():
    """Test bracket matching."""
    text = "template<int, tuple<float, double>>"
    assert find_matching_bracket(text, 8, '<', '>') == 34

    text = "nested<outer<inner<>>>"
    assert find_matching_bracket(text, 6, '<', '>') == 21


def test_extract_template_content():
    """Test template content extraction."""
    type_str = "tensor_descriptor<int, float, bool>"
    content = extract_template_content(type_str, "tensor_descriptor")
    assert content == "int, float, bool"

    type_str = "tuple<merge<constant<8>>, sequence<1,2>>"
    content = extract_template_content(type_str, "tuple")
    assert content == "merge<constant<8>>, sequence<1,2>"


def test_split_template_params():
    """Test parameter splitting."""
    params = split_template_params("int, tuple<float, double>, bool")
    assert params == ["int", "tuple<float, double>", "bool"]

    params = split_template_params("merge<constant<8>>")
    assert params == ["merge<constant<8>>"]


def test_extract_sequences():
    """Test sequence extraction."""
    content = "ck_tile::sequence<1, 2, 3>, other, sequence<4, 5>"
    seqs = extract_sequences(content)
    assert seqs == ["1, 2, 3", "4, 5"]

    # Empty sequence
    content = "sequence<>"
    seqs = extract_sequences(content)
    assert seqs == [""]


def test_extract_constant_value():
    """Test constant value extraction."""
    assert extract_constant_value("ck_tile::constant<8192l>") == 8192
    assert extract_constant_value("constant<64>") == 64
    assert extract_constant_value("int") is None


def test_parse_sequence_values():
    """Test sequence value parsing."""
    assert parse_sequence_values("1, 2, 3") == [1, 2, 3]
    assert parse_sequence_values("") == []
    assert parse_sequence_values("-1, 0, 1") == [-1, 0, 1]


if __name__ == "__main__":
    # Run all tests
    tests = [
        test_find_matching_bracket,
        test_extract_template_content,
        test_split_template_params,
        test_extract_sequences,
        test_extract_constant_value,
        test_parse_sequence_values,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
    sys.exit(0 if failed == 0 else 1)
