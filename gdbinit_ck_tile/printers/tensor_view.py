"""Pretty printer for ck_tile::tensor_view"""

from ..core.base_printer import BaseCKTilePrinter
from .tensor_descriptor import TensorDescriptorPrinter


class TensorViewPrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::tensor_view"""

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_view{\n"

            # Extract data type
            data_type = self.extract_data_type(type_str)
            if data_type:
                result += f"  data_type: {data_type}\n"

            # Check for const
            if 'const ' in type_str:
                result += "  const: true\n"

            # Access descriptor
            try:
                desc = self.val['desc_']

                # Use tensor_descriptor printer
                desc_printer = TensorDescriptorPrinter(desc)
                desc_str = desc_printer.to_string()

                result += "\n  descriptor: "
                result += desc_str.replace('\n', '\n  ')
                result += "\n"

            except Exception as e:
                result += f"  descriptor: [error: {str(e)}]\n"

            # Check for buffer_view
            try:
                buf_view = self.val['buf_view_']
                buf_type = str(buf_view.type)

                if 'buffer_view' in buf_type:
                    result += "\n  buffer_view: {\n"

                    # Check address space
                    if 'address_space_enum)1' in buf_type:
                        result += "    address_space: global\n"
                    elif 'address_space_enum)3' in buf_type:
                        result += "    address_space: lds\n"

                    result += "  }\n"

            except:
                pass

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tensor_view")
