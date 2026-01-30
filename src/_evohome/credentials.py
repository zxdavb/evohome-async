"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import json
import logging
from functools import cached_property
from http import HTTPMethod
from typing import TYPE_CHECKING, Any, Final

import aiohttp

from . import exceptions as exc
from .auth import _payload
from .const import ERR_MSG_LOOKUP_BASE, HINT_CHECK_NETWORK, HOSTNAME

if TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL


class CredentialsManagerBase:
    """A base class for managing the credentials used for HTTP authentication."""

    def __init__(
        self,
        client_id: str,
        secret: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        logger: logging.Logger | None = None,
        _hostname: str | None = None,
    ) -> None:
        """Initialise the session manager."""

        self._client_id = client_id
        self._secret = secret
        self.websession: Final = websession

        self.logger = logger or logging.getLogger(__name__)
        self._hostname: Final = _hostname or HOSTNAME

        self._was_authenticated = False  # True once credentials are proven valid

    def __str__(self) -> str:
        """Return a string representation of the object."""
        return (
            f"{self.__class__.__name__}"
            f"(client_id='{self.client_id}, hostname='{self.hostname}')"
        )

    @cached_property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    @cached_property
    def hostname(self) -> str:
        """Return the hostname used for HTTP authentication."""
        return self._hostname

    async def _post_request(self, url: StrOrURL, /, **kwargs: Any) -> dict[str, Any]:
        """POST an authentication request and return the response (a dict).

        Will raise an exception if the authentication is not successful.
        """

        rsp: aiohttp.ClientResponse | None = None  # to prevent unbound error

        try:
            rsp = await self._request(HTTPMethod.POST, url, **kwargs)
            assert rsp is not None  # mypy hint

            await rsp.read()  # so we can use rsp.json()/rsp.text(), below
            rsp.raise_for_status()

            # can't assert content_length != 0 with aioresponses, so skip that check
            if rsp.content_type != "application/json":  # usu. "text/plain", "text/html"
                raise exc.AuthenticationFailedError(
                    f"Authenticator response is not JSON: {await _payload(rsp)}"
                )

            if (response := await rsp.json()) is None:  # an unanticipated edge-case
                raise exc.AuthenticationFailedError("Authenticator response is null")

        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise exc.AuthenticationFailedError(
                f"Authenticator response is not valid JSON: {await _payload(rsp)}"
            ) from err

        except aiohttp.ClientResponseError as err:
            # TODO: process payload and raise BadCredentialsError if code = EmailOrPasswordIncorrect
            if hint := ERR_MSG_LOOKUP_BASE.get(err.status):
                self.logger.error(hint)  # noqa: TRY400

            msg = f"{err.status} {err.message}, response={await _payload(rsp)}"

            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {msg}", status=err.status
            ) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            self.logger.error(HINT_CHECK_NETWORK)  # noqa: TRY400

            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {err}",
            ) from err

        else:
            return response  # type: ignore[no-any-return]

        finally:
            if rsp is not None:
                rsp.release()

    async def _request(  # dev/test wrapper
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """Wrap the request to the ClientSession (useful for dev/test)."""
        return await self.websession.request(method, url, **kwargs)
