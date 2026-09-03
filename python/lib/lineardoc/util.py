"""
Utility functions for the lineardoc module.
"""

from __future__ import annotations

from typing import Any


def get_prop(path: list[str | int], obj: dict | list | Any) -> None | Any:
    """
    Null safe object getter.

    Example: To access obj['a']['b']['c'][0]['d'] in null safe way,
    use get_prop(['a', 'b', 'c', 0, 'd'], obj)

    Args:
        path: List of keys/indices to access
        obj: Object to access

    Returns:
        The value at the path, or None if any step fails
    """
    result = obj
    for key in path:
        if result is None:
            return None
        if isinstance(result, dict):
            result = result.get(key)
        elif isinstance(result, list) and isinstance(key, int):
            try:
                result = result[key]
            except (IndexError, TypeError):
                return None
        else:
            return None
    return result


__all__ = [
    "get_prop",
]
