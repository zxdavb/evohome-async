"""Schema for the vendor's TCC v2 API - for GET account of User, etc.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the probatio
schemas, which can be used to validate/coerce the vendor's responses.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "userId", "streetAddress", "period")
- PascalCase for JSON values that are enum strings (e.g. "TemporaryOverride", "Period")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Literal, NotRequired, TypedDict, overload

import probatio as vol

from _evohome.helpers import camel_to_snake, noop, redact

from .const import (
    REGEX_TASK_ID,
    S2_CITY,
    S2_CODE,
    S2_COUNTRY,
    S2_ERROR,
    S2_FIRSTNAME,
    S2_ID,
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

if TYPE_CHECKING:
    from _evohome.helpers import Validator
    from evohomeasync2.typedefs import EvoUsrAccountResponseT


#
# Vendor-native typed dicts for authentication URLs
# - this is the 'truth', as understood, for this undocumented API


# Successful Authentication requests respond with a token
class TccOAuthTokenResponseT(TypedDict):
    """Typed dict for responses from the vendor servers for successful authentication.

    This schemas is snake_case, unlike the RESTful API which is camelCase/PascalCase.
    """

    access_token: str
    expires_in: int
    refresh_token: str
    scope: NotRequired[str]  # "EMEA-V1-Basic EMEA-V1-Anonymous"
    token_type: str


def factory_post_oauth_token(_: Case = Case.VENDOR) -> Validator[TccOAuthTokenResponseT]:
    """Factory for the OAuth authorization response schema."""

    # NOTE: These keys are always in snake_case

    return vol.Schema(
        {
            vol.Required(SZ_ACCESS_TOKEN): vol.All(str, redact),
            vol.Required(SZ_EXPIRES_IN): vol.Range(min=1770, max=1800),  # usu. 179x
            vol.Required(SZ_REFRESH_TOKEN): vol.All(str, redact),
            vol.Optional(SZ_SCOPE): str,  # "EMEA-V1-Basic EMEA-V1-Anonymous"
            vol.Required(SZ_TOKEN_TYPE): str,
        }
    )


# Failed Authentication requests respond with an error
class TccErrorResponseT(TypedDict):
    """Typed dict for responses from the vendor servers for failed authentication."""

    error: str  # e.g. "attempt_limit_exceeded" or "invalid_grant"


def factory_error_response(case: Case = Case.VENDOR) -> Validator[TccErrorResponseT]:
    """Factory for the error response schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_ERROR)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


#
# Vendor-native typed dicts for success/failure of authorization URLs
# - this is the 'truth', as understood, for this undocumented API


# Failed GETs / PUTs respond with a code/message structure
class TccFailureResponseT(TypedDict):
    """Typed dict for responses from the vendor servers for failed GETs / PUTs."""

    code: str
    message: str


# Successful PUTs respond with a task ID
class TccTaskResponseT(TypedDict):
    """Typed dict for responses from the vendor servers for successful PUTs."""

    id: str  # {'id': '1668279943'}


def factory_task_response(case: Case = Case.VENDOR) -> Validator[TccTaskResponseT]:
    """Factory for the task response schema (a successful PUT)."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_ID)): vol.Match(REGEX_TASK_ID),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_failure_response(case: Case = Case.VENDOR) -> Validator[list[TccFailureResponseT]]:
    """Factory for the failure response schema (a failed GET / PUT)."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    entry_schema = vol.Schema(
        {
            vol.Required(fnc(S2_CODE)): str,
            vol.Required(fnc(S2_MESSAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(vol.All([entry_schema], vol.Length(min=1)))


#
# Vendor-native typed dicts for account URLs
# - this is the 'truth', as understood, for this undocumented API


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


@overload
def factory_usr_account(case: Literal[Case.VENDOR] = ...) -> Validator[TccUsrAccountResponseT]: ...


@overload
def factory_usr_account(case: Literal[Case.PYTHONIC]) -> Validator[EvoUsrAccountResponseT]: ...


@overload
def factory_usr_account(case: Case) -> Validator[TccUsrAccountResponseT] | Validator[EvoUsrAccountResponseT]: ...


def factory_usr_account(
    case: Case = Case.VENDOR,
) -> Validator[TccUsrAccountResponseT] | Validator[EvoUsrAccountResponseT]:
    """Factory for the user account schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_USER_ID)): str,
            vol.Required(fnc(S2_USERNAME)): vol.All(vol.Email(), redact),
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


#
# Vendor-native schemas

# POST /Auth/OAuth/Token
TCC_POST_OAUTH_TOKEN: Final[Validator[TccOAuthTokenResponseT]] = factory_post_oauth_token()

#
TCC_ERROR_RESPONSE: Final[Validator[TccErrorResponseT]] = factory_error_response()
TCC_FAILURE_RESPONSE: Final[Validator[list[TccFailureResponseT]]] = factory_failure_response()

# PUT (e.g. /temperatureZone/{zone_id}/heatSetpoint)
TCC_TASK_RESPONSE: Final[Validator[TccTaskResponseT]] = factory_task_response()

# GET /userAccount
TCC_GET_USR_ACCOUNT: Final[Validator[TccUsrAccountResponseT]] = factory_usr_account()
