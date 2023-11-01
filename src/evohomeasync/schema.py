#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from typing import Any

# TCC config, status dicts
_EvoLeafT = bool | float | int | str | list[str]  # Any
_EvoDictT = dict[str, Any]  # '_EvoDictT' | _EvoLeafT]
_EvoListT = list[_EvoDictT]
_EvoSchemaT = _EvoDictT | _EvoListT

# TCC identifiers
_DhwIdT = str
_GatewayIdT = str
_LocationIdT = str
_SystemIdT = str
_ZoneIdT = str

_DeviceIdT = _DhwIdT | _ZoneIdT

# TCC other
_ModeT = str
_SystemModeT = str

_TaskIdT = str
