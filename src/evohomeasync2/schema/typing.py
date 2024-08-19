#!/usr/bin/env python3
"""evohomeasync2 schema - shared types."""

from typing import Any

# TCC config, status dicts
_EvoLeafT = bool | float | int | str | list[str]  # Any
_EvoDictT = dict[str, Any]  # '_EvoDictT' | _EvoLeafT]
_EvoListT = list[_EvoDictT]
_EvoSchemaT = _EvoDictT | _EvoListT

# TCC identifierss = strings of digits
_DhwIdT = str
_GatewayIdT = str
_LocationIdT = str
_SystemIdT = str
_UserIdT = str
_ZoneIdT = str

# TCC other
_ModeT = str
