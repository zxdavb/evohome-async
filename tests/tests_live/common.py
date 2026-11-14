"""Helpers for the tests against the vendor's real servers (know neither v1 nor v2).

A test replays a recorded request (a Call) and checks the vendor's answer (an Expect).
The request is made via the client's own session and headers (so with its session id
or access token), but not via its request methods, so that the vendor's answer is seen
as is (its status, content type and body).
"""

from __future__ import annotations

import json as json_
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping
    from http import HTTPMethod, HTTPStatus

    from _evohome.auth import AbstractAuth
    from _evohome.helpers import Validator


CONTENT_TYPE_HTML: Final = "text/html"
CONTENT_TYPE_JSON: Final = "application/json"


@dataclass(frozen=True)
class Call:
    """A request: a method, its URL (relative to the base), and its body (if any).

    The URL and the body are templates: each "{key}" in them is replaced by the value
    of that key of the live ids (see fill()).
    """

    method: HTTPMethod
    url: str
    json: object = None


@dataclass(frozen=True)
class Expect:
    """What the vendor answers: its status, and either its code, schema, or HTML.

    - code:   the vendor's error code (of any error, of the list of them)
    - schema: the validator of a success (a 200 or 201)
    - html:   its body is HTML (a 404 of an unknown path), not JSON
    - absent: a key that must not be in its body (e.g. temperatureControlSystems)
    - task:   (a PUT) the state its comm task is expected to end in, if waited for
    """

    status: HTTPStatus
    code: str | None = None
    schema: Validator[object] | None = None
    html: bool = False
    absent: str | None = None
    task: str = "Succeeded"


@dataclass(frozen=True)
class Answer:
    """The vendor's answer: its status, content type and body (JSON, or text)."""

    status: int
    content_type: str
    body: Any


def fill(
    template: object,
    ids: Mapping[str, object],
) -> object:
    """Return the template with each "{key}" replaced by its value (skip if unknown).

    A str that is only "{key}" is replaced by the value as is (e.g. a schedule).
    """

    try:
        if isinstance(template, str):
            if template == f"{{{(key := template[1:-1])}}}" and key in ids:
                return ids[key]  # e.g. a schedule, as is
            return template.format(**ids)
        if isinstance(template, dict):
            return {k: fill(v, ids) for k, v in template.items()}
        if isinstance(template, list):
            return [fill(v, ids) for v in template]
    except KeyError as err:
        pytest.skip(f"The location under test has no {err}")
    return template


async def replay(
    auth: AbstractAuth,
    call: Call,
    ids: Mapping[str, object],
) -> Answer:
    """Make the request (as the client would), and return the vendor's answer."""

    url = f"{auth.url_base}/{fill(call.url, ids)}"
    kwargs: dict[str, Any] = {"headers": await auth._headers({})}
    if call.json is not None:
        kwargs["json"] = fill(call.json, ids)

    async with auth.websession.request(call.method, url, **kwargs) as rsp:
        text = await rsp.text()
        body = json_.loads(text) if rsp.content_type == CONTENT_TYPE_JSON else text
        return Answer(rsp.status, rsp.content_type, body)


def check(
    answer: Answer,
    expect: Expect,
) -> None:
    """Check the vendor's answer is as expected (its status, content type & shape)."""

    assert answer.status == expect.status, answer

    if expect.html:
        assert answer.content_type == CONTENT_TYPE_HTML, answer
        return

    assert answer.content_type == CONTENT_TYPE_JSON, answer

    if expect.code is not None:  # e.g. [{"code": "InvalidInput", "message": "..."}]
        assert isinstance(answer.body, list), answer
        assert expect.code in [e["code"] for e in answer.body], answer

    if expect.schema is not None:
        expect.schema(answer.body)

    if expect.absent is not None:
        assert expect.absent not in json_.dumps(answer.body), answer
