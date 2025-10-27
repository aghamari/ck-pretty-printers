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

## Quick Start

### Step 1: Clone this repository anywhere
```bash
git clone <repo-url> /path/to/ck-tile-gdb-printers
```

### Step 2: Choose your setup method

#### Option A: Use ~/.gdbinit (Recommended for persistent setup)
Copy the example configuration to your home directory and edit the path:

```bash
cp /path/to/ck-tile-gdb-printers/examples/example.gdbinit ~/.gdbinit
```

Edit `~/.gdbinit` and change this line:
```python
ck_tile_printers_path = '/path/to/ck-tile-gdb-printers'  # Update this path!
```

#### Option B: Load directly in GDB session
```bash
rocgdb ./your_program
source /path/to/ck-tile-gdb-printers/gdbinit_ck_tile.py
end
```

### Step 3: Build CK with proper debug symbols

For optimal debugging experience, you need to compile Composable Kernel with debug symbols. **Important:** Comment out these lines in CK's CMakeLists.txt:

```cmake
# Comment out these lines for debug builds:
# add_compile_options(
#     "$<$<CONFIG:Debug>:-Og>"
#     "$<$<CONFIG:Debug>:-gdwarf64>"
# )
```

Then build with debug flags:
```bash
cmake -S . -B build \
-DCMAKE_BUILD_TYPE=Debug \
-DCMAKE_CXX_FLAGS_DEBUG="-O0 -g -ggdb3 -fno-inline -fno-omit-frame-pointer" \
-DCMAKE_HIP_FLAGS_DEBUG="-O0 -g -ggdb3"
cmake --build build -j$(nproc)
```

### Step 4: Verify installation

```bash
rocgdb ./build/bin/your_program
# You should see:
# CK-Tile pretty printers registered successfully
# Registered printers for: tensor_descriptor, tensor_adaptor, ...
```

## Usage

### Basic GDB Commands with Pretty Printers
```bash
# Start debugging
rocgdb ./build/bin/my_program

# Set breakpoints at specific lines
(gdb) break filename.hpp:123
(gdb) break /full/path/to/file.hpp:456

# Set breakpoints at functions
(gdb) break my_function
(gdb) break ck_tile::MyClass::operator()

# Run the program
(gdb) run

# When stopped at breakpoint, pretty print CK-Tile types
(gdb) print my_tensor_descriptor
(gdb) print my_tensor_view

# Navigate through execution
(gdb) next          # Next line
(gdb) step          # Step into functions
(gdb) continue      # Continue execution
(gdb) backtrace     # Show call stack
```

### Breakpoint Management
```bash
(gdb) info breakpoints              # List all breakpoints
(gdb) break pool_kernel.hpp:377     # Set breakpoint at line 377
(gdb) break main if argc > 1        # Conditional breakpoint
(gdb) disable 1                     # Disable breakpoint #1
(gdb) delete 1                      # Delete breakpoint #1
(gdb) clear filename:line           # Remove breakpoint at location
```

### VS Code Integration
The pretty printers also work with VS Code's debugger. See the `.vscode/` configuration files in your CK project for setup details.

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

### Design Principles

- **DRY**: No code duplication - shared logic in base classes and mixins
- **Modular**: Each printer in its own file
- **Testable**: Comprehensive regression test suite
- **Extensible**: Easy to add new printers

## Code Metrics

- **Lines of code**: ~900 (down from 1637 in monolithic version)
- **Code reduction**: 45%
- **Duplication eliminated**: 400+ lines
- **Test coverage**: Regression tests for all printer types

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

