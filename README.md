# CK-Tile GDB Pretty Printers

Beautiful, modular GDB pretty printers for AMD Composable Kernel (CK-Tile) types.

## Supported Types

- `ck_tile::tensor_descriptor`
- `ck_tile::tensor_adaptor`
- `ck_tile::tensor_coordinate`
- `ck_tile::tensor_adaptor_coordinate`
- `ck_tile::tensor_view`
- `ck_tile::tile_distribution`
- `ck_tile::tile_distribution_encoding`
- `ck_tile::tile_window` (all variants)
- `ck_tile::static_distributed_tensor`

## Installation

### 1. Clone this repository

```bash
git clone <repo-url>
cd ck-tile-gdb-printers
```

### 2. Add to your `.gdbinit`

Add the following to your `~/.gdbinit`:

```python
python
import os
import sys

# Path to the pretty printers
ck_tile_printers_path = '/path/to/ck-tile-gdb-printers'

if os.path.exists(os.path.join(ck_tile_printers_path, 'gdbinit_ck_tile.py')):
    sys.path.insert(0, ck_tile_printers_path)
    gdb.execute(f'source {ck_tile_printers_path}/gdbinit_ck_tile.py')
end
```
**Note:** For optimal debugging experience, compile your CK-Tile project with debug symbols
and optimizations disabled:

```bash
cmake -S . -B build \
-DCMAKE_BUILD_TYPE=Debug \
-DCMAKE_CXX_FLAGS_DEBUG="-O0 -g -ggdb3 -fno-inline -fno-omit-frame-pointer" \
-DCMAKE_HIP_FLAGS_DEBUG="-O0 -g -ggdb3"
cmake --build build -j$(nproc)
```

### 3. Verify installation

```bash
rocgdb <your-program>

# You should see:
# CK-Tile pretty printers registered successfully
# Registered printers for: tensor_descriptor, tensor_adaptor, ...
```

## Usage

```gdb
# Debug your program
rocgdb ./build/bin/my_program

# Set breakpoint
break my_function

# Run
run

# Pretty print CK-Tile types
print my_tensor_descriptor
print my_tensor_view
```

## Example Output

```
(gdb) print a_lds_block.desc_
$1 = tensor_descriptor{
  element_space_size: 8192
  ntransform: 8
  ndim_hidden: 13
  ndim_top: 2
  ndim_bottom: 1
  bottom_dimension_ids: [0]
  top_dimension_ids: [11, 12]

  Transforms:
    [0] embed
        lower: [0]
        upper: [1, 2, 3]
        up_lengths: [8, 128, 8]
        coefficients: [8, 64, 1]
    [1] pass_through
        lower: [2, 1]
        upper: [4, 5]
        up_lengths: [128, 8]
    ...
}
```

## Development

### Running Tests

```bash
# Run full regression suite
./tests/run_regression_tests.sh

# Run unit tests
python3 tests/test_cpp_parser.py
```

### Adding a New Printer

1. Create `gdbinit_ck_tile/printers/my_new_type.py`:

```python
from ..core.base_printer import BaseCKTilePrinter

class MyNewTypePrinter(BaseCKTilePrinter):
    def to_string(self):
        # Your implementation here
        return "my_new_type{...}"
```

2. Register in `gdbinit_ck_tile.py`:

```python
from gdbinit_ck_tile.printers.my_new_type import MyNewTypePrinter

# In build_pretty_printer():
pp.add_printer('my_new_type', '^ck_tile::my_new_type<.*>$', MyNewTypePrinter)
```

3. Add tests and run regression suite

## Architecture

```
gdbinit_ck_tile/
├── core/
│   ├── base_printer.py      # Base class for all printers
│   └── transform_mixin.py   # Shared transform extraction logic
├── utils/
│   ├── cpp_type_parser.py   # C++ template parsing utilities
│   ├── tuple_extractor.py   # CK-Tile tuple extraction
│   └── constants.py         # Shared constants
└── printers/
    ├── tensor_descriptor.py # Individual printer modules
    ├── tensor_adaptor.py
    └── ...
```

## License

[Your license here]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite: `./tests/run_regression_tests.sh`
6. Submit a pull request

## Credits

Developed for AMD Composable Kernel (CK-Tile) debugging.
