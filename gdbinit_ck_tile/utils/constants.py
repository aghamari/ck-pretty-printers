"""
Constants used throughout CK-Tile pretty printers.
"""

# Transform patterns - order matters for matching
# Each tuple is (type_string_pattern, display_name)
TRANSFORM_PATTERNS = [
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
    ('ck_tile::xor_t<', 'xor'),
    ('xor_t<', 'xor'),
    ('ck_tile::pass_through<', 'pass_through'),
    ('pass_through<', 'pass_through'),
    ('ck_tile::pad<', 'pad'),
    ('pad<', 'pad'),
    ('ck_tile::right_pad<', 'right_pad'),
    ('right_pad<', 'right_pad'),
    ('ck_tile::left_pad<', 'left_pad'),
    ('left_pad<', 'left_pad'),
    ('ck_tile::slice<', 'slice'),
    ('slice<', 'slice'),
    ('ck_tile::freeze<', 'freeze'),
    ('freeze<', 'freeze'),
]

# Sanity check for detecting uninitialized values
# Values larger than this are likely garbage/uninitialized
MAX_SANE_VALUE = 100_000_000

# Default maximum dimensions to read when we can't determine the exact count
DEFAULT_MAX_DIMS = 20

# Numeric types that should be converted to Python int
NUMERIC_TYPES = [
    'int',
    'long',
    'long int',
    'unsigned int',
    'unsigned long',
]
