#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the *original* Evohome API."""

from typing import Any, TypeAlias

# TCC config, status dicts
_EvoLeafT: TypeAlias = bool | float | int | str | list[str]  # Any
_DeviceDictT: TypeAlias = dict[str, Any]  # '_EvoDeviceT' | _EvoLeafT]
_EvoDictT: TypeAlias = dict[str, Any]  # '_EvoDictT' | _EvoLeafT]
_EvoListT: TypeAlias = list[_EvoDictT]
_EvoSchemaT: TypeAlias = _EvoDictT | _EvoListT

# TCC identifiers (Usr, Loc, Gwy, Sys, Zon|Dhw)
_DhwIdT: TypeAlias = int
_GatewayIdT: TypeAlias = int
_LocationIdT: TypeAlias = int
_SystemIdT: TypeAlias = int
_UserIdT: TypeAlias = int
_ZoneIdT: TypeAlias = int
_ZoneNameT: TypeAlias = str

# TCC other
_ModeT: TypeAlias = str
_SystemModeT: TypeAlias = str

_TaskIdT: TypeAlias = str  # TODO: int or str?
