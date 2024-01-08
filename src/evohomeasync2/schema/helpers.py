#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Account JSON."""
from __future__ import annotations

from typing import Any

try:  # voluptuous is an optional module...
    import voluptuous as vol

except ModuleNotFoundError:  # No module named 'voluptuous'
    # TODO: type object 'vol' has no attribute 'Required'

    class vol:  # type: ignore[no-redef]
        class Invalid(Exception):
            pass

        Schema = dict[str, Any] | list[dict[str, Any]]


def camel_case(s: str) -> str:
    """Convert a PascalCase string to camelCase."""
    return s[:1].lower() + s[1:]


def pascal_case(s: str) -> str:
    """Convert a camelCase string to PascalCase."""
    return s[:1].upper() + s[1:]
