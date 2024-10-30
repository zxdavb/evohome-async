#!/usr/bin/env python3
"""evohomeasync2 schema - shared helpers."""

from __future__ import annotations

import re
from typing import TypeVar

_T = TypeVar("_T")


def camel_case(s: str) -> str:
    """Convert a PascalCase string to camelCase."""
    return s[:1].lower() + s[1:]


def pascal_case(s: str) -> str:
    """Convert a camelCase string to PascalCase."""
    return s[:1].upper() + s[1:]


def camel_to_snake(value: str) -> str:
    """Convert a camelCase string to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def convert_keys_to_snake_case(data: _T) -> _T:
    """Convert all keys in a dictionary to snake_case."""

    if isinstance(data, list):
        return [convert_keys_to_snake_case(item) for item in data]  # type: ignore[return-value]

    if not isinstance(data, dict):
        return data

    return {camel_to_snake(k): convert_keys_to_snake_case(v) for k, v in data.items()}  # type: ignore[return-value]
