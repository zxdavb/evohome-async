#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from typing import Any

_FilePathT = str  # _typeshed FileDescriptorOrPath

_DhwIdT = str
_GatewayIdT = str
_LocationIdT = str
_SystemIdT = str
_ZoneIdT = str

_ModeT = str

# TCC config, status dicts
# _EvoLeafT = bool | float | int | str | list[str]
# _EvoDictT = dict[str, '_EvoDictT'] | dict[str, _EvoLeafT]
# _EvoListT = list[_EvoDictT]
# _EvoSchemaT = _EvoDictT | _EvoListT

_EvoLeafT = Any
_EvoDictT = dict[str, Any]
_EvoListT = list[Any]
_EvoSchemaT = _EvoDictT | _EvoListT
