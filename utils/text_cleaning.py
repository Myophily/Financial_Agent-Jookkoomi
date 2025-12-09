"""
Text cleaning utilities for LLM output processing.

This module provides functions to clean and normalize text from LLM outputs,
particularly for removing trailing whitespace artifacts that may appear in
generated content.
"""

import re
from typing import Optional


def clean_trailing_spaces(text: Optional[str]) -> Optional[str]:
    """
    Remove repeated trailing spaces and NBSP from each line in the text.

    This function handles multiline content by processing each line independently,
    removing any ASCII spaces (0x20) and non-breaking spaces (U+00A0) that appear
    at the end of lines. This is particularly useful for cleaning LLM outputs that
    may contain trailing whitespace artifacts.

    The function preserves:
    - Leading whitespace (indentation)
    - Whitespace within content
    - Tabs and other whitespace characters
    - Line breaks and document structure

    Args:
        text: Input text to clean. May be None or empty string.

    Returns:
        Cleaned text with trailing spaces and NBSP removed from each line.
        Returns None if input is None.
        Returns empty string if input is empty string.

    Examples:
        >>> clean_trailing_spaces("line 1   \\nline 2  ")
        'line 1\\nline 2'

        >>> clean_trailing_spaces("test\\u00a0\\u00a0\\n")
        'test\\n'

        >>> clean_trailing_spaces(None)
        None

        >>> clean_trailing_spaces("")
        ''

        >>> clean_trailing_spaces("  indented   \\n  text  ")
        '  indented\\n  text'
    """
    if text is None:
        return None
    if not text:
        return text

    # Remove one or more spaces/NBSP at end of each line (MULTILINE mode)
    # Pattern: '[ \u00a0]+$' matches:
    #   - [ \u00a0]  : Character class matching ASCII space (0x20) or NBSP (U+00A0)
    #   - +          : One or more occurrences
    #   - $          : End of line (with MULTILINE flag, matches end of each line)
    return re.sub(r'[ \u00a0]+$', '', text, flags=re.MULTILINE)
