#!/usr/bin/env python3
"""
Simple test for the refactored Mermaid generator.
This tests the core functionality without requiring GDB.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules
from gdbinit_ck_tile.utils.mermaid_builder import MermaidDiagramBuilder
from gdbinit_ck_tile.utils.pretty_printer_parser import PrettyPrinterOutputParser

def test_mermaid_builder():
    """Test the MermaidDiagramBuilder works correctly."""
    print("Testing MermaidDiagramBuilder...")

    # Test data
    transforms = ['replicate', 'unmerge', 'unmerge', 'merge_v2', 'merge_v2']
    lower_dims = [[0], [1], [2], [4, 5], [3, 6]]
    upper_dims = [[1], [2, 3], [4, 5, 6], [7], [8, 9]]
    bottom_dims = [0, 1]
    top_dims = [8, 9, 3, 7]

    builder = MermaidDiagramBuilder()
    result = builder.build(
        transforms=transforms,
        lower_dims=lower_dims,
        upper_dims=upper_dims,
        bottom_dims=bottom_dims,
        top_dims=top_dims,
        title="Test Tensor Transform Flow"
    )

    # Check that key elements are in the output
    assert "```mermaid" in result
    assert "graph TD" in result
    assert "Test Tensor Transform Flow" in result
    assert "replicate" in result
    assert "unmerge" in result
    assert "merge_v2" in result
    assert "Bottom[0]" in result
    assert "Bottom[1]" in result
    assert "Top[8]" in result
    assert "Top[9]" in result

    print("✓ MermaidDiagramBuilder test passed")
    return result

def test_parser():
    """Test the PrettyPrinterOutputParser."""
    print("\nTesting PrettyPrinterOutputParser...")

    # Sample pretty printer output
    sample_output = """tensor_adaptor:
    ntransform: 5
    bottom_dimension_ids: [0, 1]
    top_dimension_ids: [8, 9, 3, 7]
    transforms:
    [0] replicate
        lower: [0], upper: [1]
        lengths: [8]
    [1] unmerge
        lower: [1], upper: [2, 3]
        low_lengths: [256], up_lengths: [16, 16]
    [2] unmerge
        lower: [2], upper: [4, 5, 6]
        low_lengths: [16], up_lengths: [1, 16, 1]
    [3] merge_v2
        lower: [4, 5], upper: [7]
        low_lengths: [1, 16], up_lengths: [16]
    [4] merge_v2
        lower: [3, 6], upper: [8, 9]
        low_lengths: [16, 1], up_lengths: [8, 2]"""

    # Test complete parsing
    result = PrettyPrinterOutputParser.parse_complete(sample_output)

    assert result['ntransform'] == 5
    assert result['bottom_dims'] == [0, 1]
    assert result['top_dims'] == [8, 9, 3, 7]
    assert len(result['transforms']) == 5
    assert result['transforms'][0]['name'] == 'replicate'
    assert result['transforms'][0]['lower'] == [0]
    assert result['transforms'][0]['upper'] == [1]

    print("✓ PrettyPrinterOutputParser test passed")
    return result

def test_integration():
    """Test the integration of parser and builder."""
    print("\nTesting integration of parser and builder...")

    # Sample output
    sample_output = """tensor_adaptor:
    ntransform: 5
    bottom_dimension_ids: [0, 1]
    top_dimension_ids: [8, 9, 3, 7]
    transforms:
    [0] replicate
        lower: [0], upper: [1]
    [1] unmerge
        lower: [1], upper: [2, 3]
    [2] unmerge
        lower: [2], upper: [4, 5, 6]
    [3] merge_v2
        lower: [4, 5], upper: [7]
    [4] merge_v2
        lower: [3, 6], upper: [8, 9]"""

    # Parse
    parsed = PrettyPrinterOutputParser.parse_complete(sample_output)

    # Build diagram
    builder = MermaidDiagramBuilder()
    result = builder.build(
        transforms=[t['name'] for t in parsed['transforms']],
        lower_dims=[t['lower'] for t in parsed['transforms']],
        upper_dims=[t['upper'] for t in parsed['transforms']],
        bottom_dims=parsed['bottom_dims'],
        top_dims=parsed['top_dims'],
        title="Integration Test"
    )

    # Verify
    assert "```mermaid" in result
    assert "[0] replicate" in result
    assert "[1] unmerge" in result
    assert "Bottom[0]" in result
    assert "Top[8]" in result

    print("✓ Integration test passed")
    print("\nGenerated Mermaid diagram:")
    print(result)

    return result

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing refactored Mermaid generator components")
    print("=" * 60)

    try:
        test_mermaid_builder()
        test_parser()
        test_integration()

        print("\n" + "=" * 60)
        print("All tests passed successfully!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()