"""
Generic value access detection utilities.
Determines the best strategy for accessing tensor values without hardcoding specific variable names.
"""

import gdb
from typing import Optional


class ValueAccessStrategy:
    """
    Determines the best strategy for accessing values based on type analysis,
    not hardcoded variable names.
    """

    @staticmethod
    def needs_pretty_printer_fallback(val, expression=None) -> bool:
        """
        Determine if we need to use pretty printer output instead of direct value access.

        This is a generic approach that detects when gdb.parse_and_eval doesn't provide
        full access to members, without hardcoding specific variable names like ps_ys_to_xs_.

        Args:
            val: GDB value object
            expression: Original expression string (optional)

        Returns:
            True if pretty printer fallback is needed, False otherwise
        """
        # Strategy 1: Try to access a known member that should exist
        # For tensor_adaptor, the 'transforms_' member should be accessible
        try:
            # Check if we can access the transforms_ member
            if hasattr(val, 'type'):
                type_str = str(val.type)

                # Only check for tensor_adaptor types
                if 'tensor_adaptor' in type_str:
                    try:
                        # Try to access transforms_ member
                        transforms = val['transforms_']
                        # If we can access it, no fallback needed
                        return False
                    except:
                        # Can't access transforms_, need fallback
                        return True

            return False

        except:
            return False

    @staticmethod
    def is_nested_member_access(expression: str) -> bool:
        """
        Check if the expression is accessing a nested member.
        Nested members often have access issues with gdb.parse_and_eval.

        Args:
            expression: Expression string like "obj.member.submember"

        Returns:
            True if it's a nested member access (2+ dots), False otherwise
        """
        if not expression:
            return False

        # Count the number of dots in the expression
        dot_count = expression.count('.')

        # If there are 2 or more dots, it's likely a nested member
        # Examples:
        #   - a_copy_dram_window.tile_dstr_.ps_ys_to_xs_ (2 dots)
        #   - simple_var.member (1 dot - usually fine)
        return dot_count >= 2

    @staticmethod
    def get_access_method(val, expression=None) -> str:
        """
        Determine the best access method for a given value.

        Args:
            val: GDB value object
            expression: Original expression string (optional)

        Returns:
            Access method: 'direct', 'pretty_printer', or 'type_only'
        """
        # Check if it's a deeply nested member access
        if expression and ValueAccessStrategy.is_nested_member_access(expression):
            # For deeply nested members, check if we need fallback
            if ValueAccessStrategy.needs_pretty_printer_fallback(val, expression):
                return 'pretty_printer'

        # Check if we can access members directly
        if ValueAccessStrategy.needs_pretty_printer_fallback(val, expression):
            return 'pretty_printer'

        # Default to direct access
        return 'direct'

    @staticmethod
    def is_reference_type(val) -> bool:
        """
        Check if the value is a reference type.
        Reference types may need special handling.

        Args:
            val: GDB value object

        Returns:
            True if it's a reference type, False otherwise
        """
        try:
            type_str = str(val.type)
            return '&' in type_str
        except:
            return False

    @staticmethod
    def can_access_member(val, member_name: str) -> bool:
        """
        Generic check if a specific member can be accessed.

        Args:
            val: GDB value object
            member_name: Name of the member to check

        Returns:
            True if member is accessible, False otherwise
        """
        try:
            # Try to access the member
            member = val[member_name]
            return True
        except:
            return False