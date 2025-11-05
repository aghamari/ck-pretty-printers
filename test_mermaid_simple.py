#!/usr/bin/env python3
"""
Simple test to verify Mermaid parsing logic works
"""

import re

def parse_pretty_printer_output(output):
    """Parse dimensions from pretty printer output"""
    lower_dims = []
    upper_dims = []

    lines = output.split('\n')

    for line in lines:
        line = line.strip()

        # Look for transform lines with dimensions
        if 'lower:' in line and 'upper:' in line:
            # Extract lower dimensions
            lower_match = re.search(r'lower:\s*\[([^\]]*)\]', line)
            upper_match = re.search(r'upper:\s*\[([^\]]*)\]', line)

            if lower_match:
                lower_str = lower_match.group(1).strip()
                if lower_str:
                    lower = [int(x.strip()) for x in lower_str.split(',') if x.strip()]
                else:
                    lower = []
                lower_dims.append(lower)

            if upper_match:
                upper_str = upper_match.group(1).strip()
                if upper_str:
                    upper = [int(x.strip()) for x in upper_str.split(',') if x.strip()]
                else:
                    upper = []
                upper_dims.append(upper)
        elif 'lower:' in line:
            # Just lower dimension
            lower_match = re.search(r'lower:\s*\[([^\]]*)\]', line)
            if lower_match:
                lower_str = lower_match.group(1).strip()
                if lower_str:
                    lower = [int(x.strip()) for x in lower_str.split(',') if x.strip()]
                else:
                    lower = []
                lower_dims.append(lower)
                upper_dims.append([])  # No upper for this transform
        elif 'upper:' in line:
            # Just upper dimension
            upper_match = re.search(r'upper:\s*\[([^\]]*)\]', line)
            if upper_match:
                upper_str = upper_match.group(1).strip()
                if upper_str:
                    upper = [int(x.strip()) for x in upper_str.split(',') if x.strip()]
                else:
                    upper = []
                if len(lower_dims) == len(upper_dims):
                    lower_dims.append([])  # No lower for this transform
                upper_dims.append(upper)

    return lower_dims, upper_dims

# Test with sample pretty printer output
sample_output = """tensor_adaptor{
  ntransform: 6
  bottom_dimension_ids: [0]
  top_dimension_ids: [0, 1, 2, 3, 4, 5]

  Transforms:
    [0] embed
        lower: [0]
        upper: [3, 4, 5]
        lengths: [4, 64, 64]
    [1] pass_through
        upper: [2]
    [2] unmerge
        lower: [0]
        upper: [0, 1]
        up_lengths: [64, 16]
    [3] xor
        lower: [1, 5]
        upper: [1]
    [4] xor
        lower: [0, 4]
        upper: [0]
    [5] pass_through
        lower: [3]
        upper: [3]
}"""

lower_dims, upper_dims = parse_pretty_printer_output(sample_output)

print("Extracted dimensions:")
for i, (lower, upper) in enumerate(zip(lower_dims, upper_dims)):
    print(f"  Transform {i}: lower={lower}, upper={upper}")

print("\nExpected:")
print("  Transform 0: lower=[0], upper=[3, 4, 5]")
print("  Transform 1: lower=[], upper=[2]")
print("  Transform 2: lower=[0], upper=[0, 1]")
print("  Transform 3: lower=[1, 5], upper=[1]")
print("  Transform 4: lower=[0, 4], upper=[0]")
print("  Transform 5: lower=[3], upper=[3]")

# Verify
expected = [
    ([0], [3, 4, 5]),
    ([], [2]),
    ([0], [0, 1]),
    ([1, 5], [1]),
    ([0, 4], [0]),
    ([3], [3])
]

if list(zip(lower_dims, upper_dims)) == expected:
    print("\n✅ Parsing logic works correctly!")
else:
    print("\n❌ Parsing logic has issues")
    print("Got:", list(zip(lower_dims, upper_dims)))