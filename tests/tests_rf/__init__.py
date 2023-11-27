#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked vendor server for provision via a hacked aiohttp."""
from __future__ import annotations

# normally, we want these flags to be False
_DEBUG_USE_REAL_AIOHTTP = False
_DEBUG_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema
