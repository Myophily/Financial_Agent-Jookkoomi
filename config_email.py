"""
Email Configuration Module

This module loads and validates recipient email addresses from the .env file.
"""

import os
import re
from typing import List


def load_recipient_emails() -> List[str]:
    """
    Loads and validates a list of email addresses from the RECIPIENT_EMAILS environment variable in the .env file.

    Returns:
        List[str]: List of validated email addresses

    Raises:
        ValueError: If RECIPIENT_EMAILS is not set or contains invalid email formats

    Example:
        .env file:
        RECIPIENT_EMAILS="user1@example.com,user2@example.com,user3@example.com"

        Code:
        emails = load_recipient_emails()
        # ['user1@example.com', 'user2@example.com', 'user3@example.com']
    """
    # 1. Read RECIPIENT_EMAILS environment variable from .env
    emails_str = os.getenv("RECIPIENT_EMAILS", "").strip()

    # 2. Raise error if environment variable not set
    if not emails_str:
        raise ValueError(
            "RECIPIENT_EMAILS not configured in .env.\n"
            "Please add: RECIPIENT_EMAILS=\"email1@example.com,email2@example.com\"\n"
            "Example: RECIPIENT_EMAILS=\"user1@example.com,user2@example.com\""
        )

    # 3. Split by comma and remove whitespace
    emails = [e.strip() for e in emails_str.split(",")]

    # 4. Filter empty strings
    emails = [e for e in emails if e]

    # 5. Remove duplicates (preserve order)
    emails = list(dict.fromkeys(emails))

    # 6. Validate email format
    invalid = [e for e in emails if not validate_email_address(e)]
    if invalid:
        raise ValueError(
            f"Invalid email format in RECIPIENT_EMAILS: {', '.join(invalid)}\n"
            f"Expected format: user@domain.com"
        )

    # 7. Verify at least one email address
    if not emails:
        raise ValueError(
            "Empty RECIPIENT_EMAILS. At least one valid email required.\n"
            "Please add: RECIPIENT_EMAILS=\"email1@example.com,email2@example.com\""
        )

    return emails


def validate_email_address(email: str) -> bool:
    """
    Performs simple email format validation.

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid format, False otherwise

    Example:
        >>> validate_email_address("user@example.com")
        True
        >>> validate_email_address("invalid.email")
        False
        >>> validate_email_address("no-at-sign.com")
        False
    """
    # Basic email format validation regex
    # Format: user@domain.com
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(pattern, email.strip()))
