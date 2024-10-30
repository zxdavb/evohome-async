#!/usr/bin/env python3
"""evohomeasync2 schema - shared types (WIP)."""

from typing import Any

# TCC config, status dicts
_EvoLeafT = bool | float | int | str | list[str]  # Any
_EvoDictT = dict[str, Any]  # '_EvoDictT' | _EvoLeafT]
_EvoListT = list[_EvoDictT]
_EvoSchemaT = _EvoDictT | _EvoListT

# TCC other
_ModeT = str
