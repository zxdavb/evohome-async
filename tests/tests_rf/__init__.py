#!/usr/bin/env python3
"""Mocked vendor server for provision via a hacked aiohttp."""

# normally, we want these debug flags to be False
_DEBUG_USE_REAL_AIOHTTP = False
_DEBUG_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema
