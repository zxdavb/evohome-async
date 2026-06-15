"""Schema for the vendor's TCC v2 API - for GET account of User, etc.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the voluptuous
schemas, which can be used to validate/coerce the vendor's responses.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "userId", "streetAddress", "period")
- PascalCase for JSON values that are enum strings (e.g. "TemporaryOverride", "Period")
"""

from __future__ import annotations

from typing import Final, TypedDict

import voluptuous as vol

from _evohome.helpers import camel_to_snake, noop, redact

from .const import (
    S2_CITY,
    S2_CODE,
    S2_COUNTRY,
    S2_ERROR,
    S2_FIRSTNAME,
    S2_LANGUAGE,
    S2_LASTNAME,
    S2_MESSAGE,
    S2_POSTCODE,
    S2_STREET_ADDRESS,
    S2_USER_ID,
    S2_USERNAME,
    SZ_ACCESS_TOKEN,
    SZ_EXPIRES_IN,
    SZ_REFRESH_TOKEN,
    SZ_SCOPE,
    SZ_TOKEN_TYPE,
)
from .helpers import Case


class TccOAuthTokenResponseT(TypedDict):
    """Typed dict for the OAuth authorization response schema.

    This schemas is snake_case, unlike the RESTful API which is camelCase.
    """

    access_token: str
    expires_in: int
    refresh_token: str
    scope: str
    token_type: str


def factory_post_oauth_token(_: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the OAuth authorization response schema."""

    # NOTE: These keys are always in snake_case

    return vol.Schema(
        {
            vol.Required(SZ_ACCESS_TOKEN): vol.All(str, redact),
            vol.Required(SZ_EXPIRES_IN): vol.Range(min=1770, max=1800),  # usu. 179x
            vol.Required(SZ_REFRESH_TOKEN): vol.All(str, redact),
            vol.Required(SZ_TOKEN_TYPE): str,
            vol.Optional(SZ_SCOPE): str,  # "EMEA-V1-Basic EMEA-V1-Anonymous"
        }
    )


class TccErrorResponseT(TypedDict):
    """Typed dict for error responses from the vendor servers."""

    error: str


def factory_error_response(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the error response schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_ERROR)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


class TccUsrAccountResponseT(TypedDict):
    """Response to GET /userAccount"""

    userId: str  # '12345678' (i.e. str, not int)
    username: str  # user@mailbox.com
    firstname: str
    lastname: str
    streetAddress: str
    city: str
    postcode: str
    country: str  # UnitedKingdom
    language: str  # enGB


def factory_user_account(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the user account schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_USER_ID)): str,
            vol.Required(fnc(S2_USERNAME)): vol.All(vol.Email(), redact),  # pyright: ignore[reportCallIssue]
            vol.Required(fnc(S2_FIRSTNAME)): str,
            vol.Required(fnc(S2_LASTNAME)): vol.All(str, redact),
            vol.Required(fnc(S2_STREET_ADDRESS)): vol.All(str, redact),
            vol.Required(fnc(S2_CITY)): vol.All(str, redact),
            vol.Required(fnc(S2_POSTCODE)): vol.All(str, redact),
            vol.Required(fnc(S2_COUNTRY)): str,
            vol.Required(fnc(S2_LANGUAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


class TccFailureResponseT(TypedDict):
    """Typed dict for code/message responses from the vendor servers."""

    code: str
    message: str


def factory_status_response(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the error response schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    entry_schema = vol.Schema(
        {
            vol.Required(fnc(S2_CODE)): str,
            vol.Required(fnc(S2_MESSAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(vol.All([entry_schema], vol.Length(min=1)))


class TccTaskResponseT(TypedDict):
    """Typed dict for code/message responses from the vendor servers."""

    id: str  # {'id': '1668279943'}


#
TCC_ERROR_RESPONSE: Final = factory_error_response()
TCC_STATUS_RESPONSE: Final = factory_status_response()

# POST /Auth/OAuth/Token  # TODO: add this
TCC_POST_OAUTH_TOKEN: Final = factory_post_oauth_token()

# GET /userAccount
TCC_GET_USR_ACCOUNT: Final = factory_user_account()
