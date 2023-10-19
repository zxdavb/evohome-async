#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Exceptions."""
from __future__ import annotations
import logging


_LOGGER = logging.getLogger(__name__)


# def _handle_exception(exc: Exception) -> None:
#     """Return False if the exception can't be ignored."""

#     try:
#         raise err

#     except evohomeasync2.AuthenticationError:
#         _LOGGER.error(
#             (
#                 "Failed to authenticate with the vendor's server. Check your username"
#                 " and password. NB: Some special password characters that work"
#                 " correctly via the website will not work via the web API. Message"
#                 " is: %s"
#             ),
#             exc,
#         )

#     except aiohttp.ClientConnectionError:
#         # this appears to be a common occurrence with the vendor's servers
#         _LOGGER.warning("Unable to connect with the vendor's server.")

#     except aiohttp.ClientResponseError:
#         if err.status == HTTPStatus.SERVICE_UNAVAILABLE:
#             _LOGGER.warning("The vendor says their server is currently unavailable.")

#         elif err.status == HTTPStatus.TOO_MANY_REQUESTS:
#             _LOGGER.warning("The vendor's API rate limit has been exceeded.")

#         else:
#             raise  # we don't expect/handle any other Exceptions
