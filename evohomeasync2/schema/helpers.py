#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Account JSON."""
from __future__ import annotations

try:  # voluptuous is an optional module...
    import voluptuous as vol  # type: ignore[import-untyped]

except ModuleNotFoundError:  # No module named 'voluptuous'

    class vol:  # type: ignore[no-redef]
        class Invalid(Exception):
            pass

        Schema = dict | list
