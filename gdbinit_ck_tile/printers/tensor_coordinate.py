"""Pretty printers for tensor coordinates"""

import re
from ..core.base_printer import BaseCKTilePrinter
from ..utils.constants import DEFAULT_MAX_DIMS


class TensorAdaptorCoordinatePrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::tensor_adaptor_coordinate"""

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_adaptor_coordinate{\n"

            # Extract dimension IDs and NDimHidden
            ndim_hidden, bottom_dim_ids, top_dim_ids = self._extract_dimension_ids_from_type(type_str)

            # Access idx_hidden_ member
            hidden_vals = self._extract_hidden_values(ndim_hidden)

            # Show the data array (only valid NDimHidden elements)
            if hidden_vals:
                result += f"  idx_hidden_ (data): {hidden_vals}\n"

            # Show dimension IDs
            if bottom_dim_ids:
                result += f"  bottom_dimension_ids: {bottom_dim_ids}\n"
            if top_dim_ids:
                result += f"  top_dimension_ids: {top_dim_ids}\n"

            if hidden_vals:
                # Show computed top index
                if top_dim_ids:
                    top_vals = [hidden_vals[i] for i in top_dim_ids if i < len(hidden_vals)]
                    result += f"  top_index: {top_vals}\n"

                # Show computed bottom index
                if bottom_dim_ids:
                    bottom_vals = [hidden_vals[i] for i in bottom_dim_ids if i < len(hidden_vals)]
                    result += f"  bottom_index: {bottom_vals}\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tensor_adaptor_coordinate")

    def _extract_dimension_ids_from_type(self, type_str):
        """Extract NDimHidden, BottomDimensionHiddenIds and TopDimensionHiddenIds from type"""
        coord_start = type_str.find('tensor_adaptor_coordinate<')
        if coord_start == -1:
            return 0, [], []

        pos = coord_start + len('tensor_adaptor_coordinate<')
        bracket_count = 1
        end = pos

        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        coord_content = type_str[pos:end-1]

        # Extract NDimHidden (first template parameter)
        ndim_hidden = 0
        first_comma = coord_content.find(',')
        if first_comma != -1:
            ndim_str = coord_content[:first_comma].strip()
            if ndim_str.isdigit():
                ndim_hidden = int(ndim_str)

        # Find all sequences
        seqs = re.findall(r'ck_tile::sequence<([^>]*)>', coord_content)

        bottom_dims = []
        top_dims = []

        if len(seqs) >= 2:
            # Second-to-last sequence is BottomDimensionHiddenIds
            bottom_str = seqs[-2]
            if bottom_str.strip():
                bottom_dims = [
                    int(x.strip())
                    for x in bottom_str.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]

            # Last sequence is TopDimensionHiddenIds
            top_str = seqs[-1]
            if top_str.strip():
                top_dims = [
                    int(x.strip())
                    for x in top_str.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]

        return ndim_hidden, bottom_dims, top_dims

    def _extract_hidden_values(self, ndim_hidden):
        """Extract values from idx_hidden_ member"""
        hidden_vals = []

        try:
            idx_hidden = self.val['idx_hidden_']

            # Try to get the data member
            try:
                data = idx_hidden['data']
                max_dims = ndim_hidden if ndim_hidden > 0 else DEFAULT_MAX_DIMS

                for i in range(max_dims):
                    try:
                        val = int(data[i])
                        hidden_vals.append(val)
                    except:
                        break
            except:
                # Try direct indexing
                max_dims = ndim_hidden if ndim_hidden > 0 else DEFAULT_MAX_DIMS
                for i in range(max_dims):
                    try:
                        val = int(idx_hidden[i])
                        hidden_vals.append(val)
                    except:
                        break

        except Exception:
            pass

        return hidden_vals


class TensorCoordinatePrinter(BaseCKTilePrinter):
    """Pretty printer for ck_tile::tensor_coordinate"""

    def to_string(self):
        try:
            type_str = str(self.val.type)
            result = "tensor_coordinate{\n"

            # Extract dimension IDs and NDimHidden
            ndim_hidden, top_dim_ids = self._extract_top_dimension_ids_from_type(type_str)

            # Access idx_hidden_ member
            hidden_vals = self._extract_hidden_values(ndim_hidden)

            # Show the data array
            if hidden_vals:
                result += f"  idx_hidden_ (data): {hidden_vals}\n"

            # Show dimension IDs (bottom is always [0] for tensor_coordinate)
            result += f"  bottom_dimension_ids: [0]\n"
            if top_dim_ids:
                result += f"  top_dimension_ids: {top_dim_ids}\n"

            if hidden_vals:
                # Show index (top index)
                if top_dim_ids:
                    top_vals = [hidden_vals[i] for i in top_dim_ids if i < len(hidden_vals)]
                    result += f"  index (top): {top_vals}\n"

                # Show offset (bottom_index[0])
                if len(hidden_vals) > 0:
                    result += f"  offset (bottom[0]): {hidden_vals[0]}\n"

            result += "}"
            return result

        except Exception as e:
            return self.format_error(str(e), "tensor_coordinate")

    def _extract_top_dimension_ids_from_type(self, type_str):
        """Extract NDimHidden and TopDimensionHiddenIds from type"""
        coord_start = type_str.find('tensor_coordinate<')
        if coord_start == -1:
            return 0, []

        pos = coord_start + len('tensor_coordinate<')
        bracket_count = 1
        end = pos

        while bracket_count > 0 and end < len(type_str):
            if type_str[end] == '<':
                bracket_count += 1
            elif type_str[end] == '>':
                bracket_count -= 1
            end += 1

        coord_content = type_str[pos:end-1]

        # Extract NDimHidden
        ndim_hidden = 0
        first_comma = coord_content.find(',')
        if first_comma != -1:
            ndim_str = coord_content[:first_comma].strip()
            if ndim_str.isdigit():
                ndim_hidden = int(ndim_str)

        # Find all sequences
        seqs = re.findall(r'ck_tile::sequence<([^>]*)>', coord_content)

        top_dims = []

        if len(seqs) >= 1:
            # Last sequence is TopDimensionHiddenIds
            top_str = seqs[-1]
            if top_str.strip():
                top_dims = [
                    int(x.strip())
                    for x in top_str.split(',')
                    if x.strip().lstrip('-').isdigit()
                ]

        return ndim_hidden, top_dims

    def _extract_hidden_values(self, ndim_hidden):
        """Extract values from idx_hidden_ member (inherited from base)"""
        hidden_vals = []

        try:
            idx_hidden = self.val['idx_hidden_']

            # Try to get the data member
            try:
                data = idx_hidden['data']
                max_dims = ndim_hidden if ndim_hidden > 0 else DEFAULT_MAX_DIMS

                for i in range(max_dims):
                    try:
                        val = int(data[i])
                        hidden_vals.append(val)
                    except:
                        break
            except:
                # Try direct indexing
                max_dims = ndim_hidden if ndim_hidden > 0 else DEFAULT_MAX_DIMS
                for i in range(max_dims):
                    try:
                        val = int(idx_hidden[i])
                        hidden_vals.append(val)
                    except:
                        break

        except Exception:
            pass

        return hidden_vals
