#!/usr/bin/env python3
"""
Structure-aware comparison for CK-Tile pretty printer output.
Compares the structure and format, ignoring runtime-dependent values like coordinates.
"""

import sys
import re

def normalize_line(line):
    """Normalize a line by replacing numeric values with placeholders."""
    # Remove GDB warnings
    if 'Warning:' in line or "Use 'set logging" in line:
        return None

    # Remove empty lines
    if not line.strip():
        return None

    # Replace numeric arrays with placeholder
    # e.g., "idx_hidden_ (data): [524288, 128, 0]" -> "idx_hidden_ (data): [NUM, NUM, NUM]"
    line = re.sub(r'\[(\d+(?:, *\d+)*)\]', lambda m: '[' + ', '.join(['NUM'] * len(m.group(1).split(','))) + ']', line)

    # Replace standalone numbers (but keep field names)
    # e.g., "element_space_size: 8192" -> "element_space_size: NUM"
    line = re.sub(r':\s*\d+\s*$', ': NUM', line)
    line = re.sub(r':\s*\d+\s*\n', ': NUM\n', line)

    # Replace GDB variable numbers ($1, $2, etc.)
    line = re.sub(r'\$\d+\s*=', '$N =', line)

    return line

def compare_files(file1_path, file2_path):
    """Compare two files structurally."""
    with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
        lines1 = [normalize_line(line) for line in f1]
        lines2 = [normalize_line(line) for line in f2]

        # Filter out None lines
        lines1 = [l for l in lines1 if l is not None]
        lines2 = [l for l in lines2 if l is not None]

        if lines1 != lines2:
            # Show differences
            print(f"Structural differences found:")
            print(f"File 1: {file1_path}")
            print(f"File 2: {file2_path}")
            print()

            max_len = max(len(lines1), len(lines2))
            for i in range(max_len):
                l1 = lines1[i] if i < len(lines1) else "[MISSING]"
                l2 = lines2[i] if i < len(lines2) else "[MISSING]"

                if l1 != l2:
                    print(f"Line {i+1}:")
                    print(f"  Golden:  {l1.rstrip()}")
                    print(f"  Current: {l2.rstrip()}")

            return False

        return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <golden_file> <current_file>")
        sys.exit(1)

    if compare_files(sys.argv[1], sys.argv[2]):
        sys.exit(0)  # Files match structurally
    else:
        sys.exit(1)  # Files differ
