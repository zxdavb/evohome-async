#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the *original* Evohome API."""

from typing import Any, TypeAlias

# TCC config, status dicts
_EvoLeafT: TypeAlias = bool | float | int | str | list[str]  # Any
_EvoDictT: TypeAlias = dict[str, Any]  # '_EvoDictT' | _EvoLeafT]
_EvoListT: TypeAlias = list[_EvoDictT]
_EvoSchemaT: TypeAlias = _EvoDictT | _EvoListT

# TCC identifiers
_DhwIdT: TypeAlias = str
_GatewayIdT: TypeAlias = str
_LocationIdT: TypeAlias = str
_SystemIdT: TypeAlias = str
_UserIdT: TypeAlias = str
_ZoneIdT: TypeAlias = str
_ZoneNameT: TypeAlias = str

# TCC other
_ModeT: TypeAlias = str
_SystemModeT: TypeAlias = str

_TaskIdT: TypeAlias = str
