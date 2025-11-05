#!/usr/bin/env python3
"""
Test PrettyPrinterOutputParser with tensor_descriptor output
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdbinit_ck_tile.utils.pretty_printer_parser import PrettyPrinterOutputParser

descriptor_output = """tensor_descriptor{
  element_space_size: 0
  ntransform: 15
  ndim_hidden: 23
  ndim_top: 2
  ndim_bottom: 1
  bottom_dimension_ids: [0]
  top_dimension_ids: [21, 22]

  Transforms:
    [0] embed
        lower: [0]
        upper: [1, 2, 3, 4, 5]
        up_lengths: [0, 0, 0, 0, 0]
    [1] pass_through
        lower: [1]
        upper: [6]
    [2] pad
        lower: [2]
        upper: [7]
    [3] pad
        lower: [3]
        upper: [8]
    [4] pad
        lower: [4]
        upper: [9]
    [5] pass_through
        lower: [5]
        upper: [10]
    [6] pass_through
        lower: [6]
        upper: [11]
    [7] embed
        lower: [7]
        upper: [12, 13]
    [8] embed
        lower: [8]
        upper: [14, 15]
    [9] embed
        lower: [9]
        upper: [16, 17]
    [10] pass_through
        lower: [10]
        upper: [18]
    [11] merge_v2
        lower: [11, 13, 15, 17, 18]
        upper: [19]
    [12] merge_v2
        lower: [12, 14, 16]
        upper: [20]
    [13] right_pad
        lower: [19]
        upper: [21]
    [14] right_pad
        lower: [20]
        upper: [22]
}"""

print("Testing parser with tensor_descriptor output...")
parsed = PrettyPrinterOutputParser.parse_complete(descriptor_output)

print(f"\nParsed data:")
print(f"  ntransform: {parsed['ntransform']}")
print(f"  bottom_dims: {parsed['bottom_dims']}")
print(f"  top_dims: {parsed['top_dims']}")
print(f"  Number of transforms parsed: {len(parsed['transforms'])}")

if parsed['transforms']:
    print(f"\n  First transform: {parsed['transforms'][0]}")
    print(f"  Last transform: {parsed['transforms'][-1]}")
else:
    print("\n  ERROR: No transforms parsed!")

# Test if it would work with the MermaidDiagramBuilder
if parsed['transforms']:
    from gdbinit_ck_tile.utils.mermaid_builder import MermaidDiagramBuilder

    transforms = [t['name'] for t in parsed['transforms']]
    lower_dims = [t['lower'] for t in parsed['transforms']]
    upper_dims = [t['upper'] for t in parsed['transforms']]

    builder = MermaidDiagramBuilder()
    result = builder.build(
        transforms=transforms,
        lower_dims=lower_dims,
        upper_dims=upper_dims,
        bottom_dims=parsed['bottom_dims'],
        top_dims=parsed['top_dims'],
        title="Tensor Descriptor Transform Flow"
    )

    print("\n✓ Successfully generated Mermaid diagram!")
    print(f"  Contains 'Bottom[0]': {'Bottom[0]' in result}")
    print(f"  Contains 'embed': {'embed' in result}")
    print(f"  Contains 'Top[21]': {'Top[21]' in result}")
else:
    print("\n✗ Cannot generate Mermaid - no transforms found")