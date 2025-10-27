"""Pretty printers for tile distribution types"""

import re
from ..core.base_printer import BaseCKTilePrinter
from .tensor_adaptor import TensorAdaptorPrinter
from .tensor_descriptor import TensorDescriptorPrinter


class TileDistributionPrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::tile_distribution"""

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tile_distribution{\n"

            # Extract encoding information
            encoding_info = self._extract_encoding_info(type_str)
            if encoding_info:
                result += f"  encoding: {encoding_info}\n"

            # Access ps_ys_to_xs_
            try:
                ps_ys_to_xs = self.val['ps_ys_to_xs_']
                ps_type = str(ps_ys_to_xs.type)

                result += "\n  ps_ys_to_xs_: "

                # Use tensor_adaptor printer if it's a tensor_adaptor
                if 'tensor_adaptor' in ps_type:
                    adaptor_printer = TensorAdaptorPrinter(ps_ys_to_xs)
                    adaptor_str = adaptor_printer.to_string()
                    result += adaptor_str.replace('\n', '\n  ')
                else:
                    result += "{\n"
                    result += f"    type: {ps_type[:50]}...\n"
                    result += "  }"

                result += "\n"

            except Exception as e:
                result += f"  ps_ys_to_xs_: [error: {str(e)}]\n"

            # Access ys_to_d_
            try:
                ys_to_d = self.val['ys_to_d_']

                # Use tensor_descriptor printer
                desc_printer = TensorDescriptorPrinter(ys_to_d)
                desc_str = desc_printer.to_string()

                result += "\n  ys_to_d_: "
                result += desc_str.replace('\n', '\n  ')
                result += "\n"

            except Exception as e:
                result += f"  ys_to_d_: [error: {str(e)}]\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tile_distribution")

    def _extract_encoding_info(self, type_str):
        """Extract comprehensive tile_distribution_encoding information"""
        if 'tile_distribution_encoding' not in type_str:
            return None

        # Find the full encoding content
        encoding_start = type_str.find('tile_distribution_encoding<')
        if encoding_start == -1:
            return None

        pos = encoding_start + len('tile_distribution_encoding<')
        bracket_count = 1
        end = pos
        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        encoding_content = type_str[pos:end-1]

        result = "{\n"

        # Parse RsLengths (first sequence not in a tuple)
        rs_lengths = []
        rs_match = re.search(r'^ck_tile::sequence<([\d,\s-]+)>', encoding_content)
        if not rs_match:
            rs_match = re.search(r',\s*ck_tile::sequence<([\d,\s-]+)>', encoding_content)

        if rs_match:
            rs_str = rs_match.group(1)
            rs_lengths = [int(x.strip()) for x in rs_str.split(',') if x.strip().lstrip('-').isdigit()]
            result += f"    RsLengths: {rs_lengths}\n"

        # Parse HsLengthss (first tuple of sequences)
        hs_lengthss = []
        hs_start = encoding_content.find('ck_tile::tuple<')
        if hs_start != -1:
            # Extract the first tuple
            pos = hs_start + len('ck_tile::tuple<')
            bracket_count = 1
            tuple_end = pos
            while bracket_count > 0 and tuple_end < len(encoding_content):
                if encoding_content[tuple_end] == '<':
                    bracket_count += 1
                elif encoding_content[tuple_end] == '>':
                    bracket_count -= 1
                tuple_end += 1

            hs_content = encoding_content[hs_start + len('ck_tile::tuple<'):tuple_end-1]
            hs_seqs = re.findall(r'sequence<([\d,\s-]+)>', hs_content)

            if hs_seqs:
                result += "    HsLengthss: ["
                for i, seq in enumerate(hs_seqs):
                    dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                    hs_lengthss.append(dims)
                    if i > 0:
                        result += ", "
                    result += str(dims)
                result += "]\n"

        # Parse all tuples to find Ps2RHss and dimension mappings
        all_tuples = []
        tuple_start = 0
        while True:
            tuple_start = encoding_content.find('ck_tile::tuple<', tuple_start)
            if tuple_start == -1:
                break

            pos = tuple_start + len('ck_tile::tuple<')
            bracket_count = 1
            tuple_end = pos
            while bracket_count > 0 and tuple_end < len(encoding_content):
                if encoding_content[tuple_end] == '<':
                    bracket_count += 1
                elif encoding_content[tuple_end] == '>':
                    bracket_count -= 1
                tuple_end += 1

            tuple_content = encoding_content[tuple_start + len('ck_tile::tuple<'):tuple_end-1]
            seqs = re.findall(r'sequence<([\d,\s-]+)>', tuple_content)

            if seqs:
                parsed_seqs = []
                for seq in seqs:
                    dims = [int(x.strip()) for x in seq.split(',') if x.strip().lstrip('-').isdigit()]
                    parsed_seqs.append(dims)
                all_tuples.append(parsed_seqs)

            tuple_start = tuple_end

        # Ps2RHssMajor and Minor (tuples 2 and 3)
        ps_major = []
        ps_minor = []
        if len(all_tuples) > 1:
            ps_major = all_tuples[1]
        if len(all_tuples) > 2:
            ps_minor = all_tuples[2]

        # Find standalone sequences at the end (Ys2RHs)
        standalone_seqs = []
        pos = 0
        while pos < len(encoding_content):
            if encoding_content[pos:].startswith('ck_tile::tuple<'):
                # Skip the entire tuple
                bracket_count = 1
                pos += len('ck_tile::tuple<')
                while bracket_count > 0 and pos < len(encoding_content):
                    if encoding_content[pos] == '<':
                        bracket_count += 1
                    elif encoding_content[pos] == '>':
                        bracket_count -= 1
                    pos += 1
            elif encoding_content[pos:].startswith('ck_tile::sequence<'):
                # Found a standalone sequence
                seq_start = pos + len('ck_tile::sequence<')
                seq_end = encoding_content.find('>', seq_start)
                if seq_end != -1:
                    seq_content = encoding_content[seq_start:seq_end]
                    dims = [int(x.strip()) for x in seq_content.split(',') if x.strip().lstrip('-').isdigit()]
                    if dims:
                        standalone_seqs.append(dims)
                    pos = seq_end + 1
                else:
                    pos += 1
            else:
                pos += 1

        # The last standalone sequences are Ys2RHs
        ys_major = []
        ys_minor = []
        if len(standalone_seqs) >= 2:
            ys_major = standalone_seqs[-2]
            ys_minor = standalone_seqs[-1]

        # Helper function to get length from RH major/minor
        def get_rh_length(rh_major, rh_minor):
            if rh_major == 0:
                # R dimension
                if rh_minor < len(rs_lengths):
                    return rs_lengths[rh_minor]
            else:
                # H dimension (major-1 is the index into HsLengthss)
                h_idx = rh_major - 1
                if h_idx < len(hs_lengthss) and rh_minor < len(hs_lengthss[h_idx]):
                    return hs_lengthss[h_idx][rh_minor]
            return None

        # Display raw encoding sequences first
        if ps_major and ps_minor:
            result += f"    Ps2RHssMajor: {ps_major}\n"
            result += f"    Ps2RHssMinor: {ps_minor}\n"

        if ys_major and ys_minor:
            result += f"    Ys2RHsMajor: {ys_major}\n"
            result += f"    Ys2RHsMinor: {ys_minor}\n"

        # Display Ps mappings with lengths
        if ps_major and ps_minor:
            result += "    Ps mappings (with lengths):\n"
            for p_idx in range(len(ps_major)):
                if p_idx < len(ps_major) and p_idx < len(ps_minor):
                    p_major_seq = ps_major[p_idx]
                    p_minor_seq = ps_minor[p_idx]
                    result += f"      P[{p_idx}]:\n"
                    for i, (maj, min_) in enumerate(zip(p_major_seq, p_minor_seq)):
                        length = get_rh_length(maj, min_)
                        if maj == 0:
                            result += f"        -> R[{min_}]"
                        else:
                            result += f"        -> H{maj-1}[{min_}]"
                        if length is not None:
                            result += f" (length={length})"
                        result += "\n"

        # Display Ys mappings with lengths
        if ys_major and ys_minor:
            result += "    Ys mappings (with lengths):\n"
            for y_idx in range(len(ys_major)):
                if y_idx < len(ys_major) and y_idx < len(ys_minor):
                    maj = ys_major[y_idx]
                    min_ = ys_minor[y_idx]
                    length = get_rh_length(maj, min_)
                    if maj == 0:
                        result += f"      Y[{y_idx}] -> R[{min_}]"
                    else:
                        result += f"      Y[{y_idx}] -> H{maj-1}[{min_}]"
                    if length is not None:
                        result += f" (length={length})"
                    result += "\n"

        result += "  }"
        return result


class TileDistributionEncodingPrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::tile_distribution_encoding"""

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tile_distribution_encoding{\n"

            # Extract template parameters
            encoding_match = re.search(r'tile_distribution_encoding<(.*)>', type_str)
            if not encoding_match:
                return "tile_distribution_encoding{}"

            content = encoding_match.group(1)

            # Parse RsLengths (first sequence)
            rs_match = re.search(r'^ck_tile::sequence<([\d,\s-]+)>', content)
            if rs_match:
                rs_str = rs_match.group(1)
                rs_lengths = [
                    int(x.strip())
                    for x in rs_str.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]
                result += f"  RsLengths: {rs_lengths}\n"
                result += f"  NDimR: {len(rs_lengths)}\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tile_distribution_encoding")


class TileWindowPrinter(BaseCKTilePrinter):
    """Pretty printer for tile_window types"""

    def to_string(self):
        try:
            type_str = str(self.val.type)

            # Determine window type
            if 'tile_window_with_static_distribution' in type_str:
                window_type = "tile_window_with_static_distribution"
            elif 'tile_window_with_static_lengths' in type_str:
                window_type = "tile_window_with_static_lengths"
            else:
                window_type = "tile_window"

            result = f"{window_type}{{\n"

            # Extract data type
            data_type = self.extract_data_type(type_str)
            if data_type:
                result += f"  data_type: {data_type}\n"

            # Extract window dimensions
            dims_match = re.findall(r'constant<(\d+)>', type_str)
            if dims_match and len(dims_match) >= 2:
                result += f"  window_dims: [{dims_match[0]} x {dims_match[1]}]\n"

            # For static_distribution, access tile_dstr_
            if 'static_distribution' in window_type:
                try:
                    tile_dstr = self.val['tile_dstr_']

                    # Use tile_distribution printer
                    dstr_printer = TileDistributionPrinter(tile_dstr)
                    dstr_str = dstr_printer.to_string()

                    result += "\n  tile_dstr_: "
                    result += dstr_str.replace('\n', '\n  ')
                    result += "\n"

                except Exception as e:
                    result += f"  tile_dstr_: [error: {str(e)}]\n"

            # Access bottom_tensor_view
            try:
                from .tensor_view import TensorViewPrinter
                bottom_view = self.val['bottom_tensor_view_']

                # Use tensor_view printer
                view_printer = TensorViewPrinter(bottom_view)
                view_str = view_printer.to_string()

                result += "\n  bottom_tensor_view_: "
                result += view_str.replace('\n', '\n  ')
                result += "\n"

            except:
                pass

            # Check for pre_computed_coords
            try:
                coords = self.val['pre_computed_coords_']
                result += "\n  pre_computed_coords_: present\n"
            except:
                pass

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), window_type)


class StaticDistributedTensorPrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::static_distributed_tensor"""

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "static_distributed_tensor{\n"

            # Extract data type
            data_type = self.extract_data_type(type_str)
            if data_type:
                result += f"  data_type: {data_type}\n"

            # Extract shape from HsLengthss in tile_distribution_encoding
            # Pattern: tile_distribution_encoding<..., ck_tile::tuple<ck_tile::sequence<4, 8, 64, 1> >, ...>
            # Note: There may be a space before the closing >
            shape = None
            encoding_match = re.search(r'tile_distribution_encoding<', type_str)
            if encoding_match:
                # Find the first tuple after tile_distribution_encoding
                start_pos = encoding_match.end()
                # Skip the first sequence (RsLengths which is empty in this case)
                after_rs = type_str[start_pos:]
                tuple_match = re.search(r'tuple<ck_tile::sequence<([\d,\s]+)>\s*>', after_rs)
                if tuple_match:
                    shape_str = tuple_match.group(1)
                    shape = [int(x.strip()) for x in shape_str.split(',') if x.strip().isdigit()]

            if shape:
                result += f"  shape: {shape}\n"

            # Extract distribution transform information from tensor_adaptor in the type
            # This reuses the existing transform extraction logic but from the type, not runtime
            transforms = []

            # Find tensor_adaptor and extract its transforms tuple
            adaptor_match = re.search(r'tensor_adaptor<ck_tile::tuple<([^>]+(?:>[^>]+)*)', type_str)
            if adaptor_match:
                transforms_str = adaptor_match.group(1)

                # Extract replicate
                if 'replicate' in transforms_str:
                    transforms.append("replicate")

                # Extract unmerge with proper bracket matching
                pos = 0
                while True:
                    unmerge_pos = transforms_str.find('unmerge<', pos)
                    if unmerge_pos == -1:
                        break

                    # Find matching close bracket
                    bracket_start = unmerge_pos + len('unmerge<')
                    bracket_count = 1
                    end = bracket_start
                    while bracket_count > 0 and end < len(transforms_str):
                        if transforms_str[end] == '<':
                            bracket_count += 1
                        elif transforms_str[end] == '>':
                            bracket_count -= 1
                        end += 1

                    unmerge_content = transforms_str[bracket_start:end-1]
                    consts = re.findall(r'constant<(\d+)>', unmerge_content)
                    if consts:
                        dims = [int(c) for c in consts]
                        transforms.append(f"unmerge{dims}")

                    pos = end

                # Extract merge transforms
                pos = 0
                while True:
                    merge_pos = transforms_str.find('merge', pos)
                    if merge_pos == -1:
                        break

                    # Find the opening <
                    open_bracket = transforms_str.find('<', merge_pos)
                    if open_bracket == -1 or open_bracket > merge_pos + 30:  # Sanity check
                        pos = merge_pos + 5
                        continue

                    # Find matching close bracket
                    bracket_count = 1
                    end = open_bracket + 1
                    while bracket_count > 0 and end < len(transforms_str):
                        if transforms_str[end] == '<':
                            bracket_count += 1
                        elif transforms_str[end] == '>':
                            bracket_count -= 1
                        end += 1

                    merge_content = transforms_str[open_bracket+1:end-1]
                    consts = re.findall(r'constant<(\d+)>', merge_content)
                    if consts:
                        dims = [int(c) for c in consts]
                        # Get merge type
                        merge_type = transforms_str[merge_pos:open_bracket]
                        if 'v2' in merge_type:
                            transforms.append(f"merge_v2{dims}")
                        else:
                            transforms.append(f"merge{dims}")

                    pos = end

            if transforms:
                result += f"  transforms: {', '.join(transforms)}\n"

            # Try to get thread buffer size
            try:
                thread_buf = self.val['thread_buf_']
                buf_type_str = str(thread_buf.type)
                size_match = re.search(r'thread_buffer<[^,]+,\s*(\d+)', buf_type_str)
                if size_match:
                    buffer_size = int(size_match.group(1))
                    result += f"  thread_buffer_size: {buffer_size}\n"
            except:
                pass

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "static_distributed_tensor")
