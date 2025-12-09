"""
Retry utility with exponential backoff for handling transient failures.
"""
import asyncio
import time
from typing import Callable, Any, TypeVar, Optional
from functools import wraps

T = TypeVar('T')


async def retry_with_exponential_backoff(
    func: Callable[..., T],
    max_retries: int = 1,
    initial_delay: float = 2.0,
    *args,
    **kwargs
) -> tuple[T, int]:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retries (default 1, means 2 total attempts)
        initial_delay: Initial delay in seconds (default 2s)
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Tuple of (result, attempts_made)

    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            print(f"  Attempt {attempt + 1}/{max_retries + 1}...")
            result = await func(*args, **kwargs)
            if attempt > 0:
                print(f"  ✓ Retry successful (attempt: {attempt + 1})")
            return result, attempt + 1
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = initial_delay * (2 ** attempt)  # Exponential: 2s, 4s, 8s...
                print(f"  ✗ Failed: {str(e)[:100]}")
                print(f"  Retrying after {delay}s...")
                await asyncio.sleep(delay)
            else:
                print(f"  ✗ All retries failed ({attempt + 1} attempts)")

    # If we get here, all retries failed
    raise last_exception


def retry_sync_with_exponential_backoff(
    func: Callable[..., T],
    max_retries: int = 1,
    initial_delay: float = 2.0,
    *args,
    **kwargs
) -> tuple[T, int]:
    """
    Retry a synchronous function with exponential backoff.

    Args:
        func: Synchronous function to retry
        max_retries: Maximum number of retries (default 1, means 2 total attempts)
        initial_delay: Initial delay in seconds (default 2s)
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Tuple of (result, attempts_made)

    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            print(f"  Attempt {attempt + 1}/{max_retries + 1}...")
            result = func(*args, **kwargs)
            if attempt > 0:
                print(f"  ✓ Retry successful (attempt: {attempt + 1})")
            return result, attempt + 1
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = initial_delay * (2 ** attempt)  # Exponential: 2s, 4s, 8s...
                print(f"  ✗ Failed: {str(e)[:100]}")
                print(f"  Retrying after {delay}s...")
                time.sleep(delay)
            else:
                print(f"  ✗ All retries failed ({attempt + 1} attempts)")

    # If we get here, all retries failed
    raise last_exception
