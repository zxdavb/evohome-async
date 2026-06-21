# evohome-async

![ruff](https://github.com/zxdavb/evohome-async/actions/workflows/check-lint.yml/badge.svg)
![mypy](https://github.com/zxdavb/evohome-async/actions/workflows/check-type.yml/badge.svg)
![pytest](https://github.com/zxdavb/evohome-async/actions/workflows/check-tests.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/evohome-async?label=pypi%20package)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/evohome-async)
![PyPI - Downloads](https://img.shields.io/pypi/dm/evohome-async)
![License](https://img.shields.io/pypi/l/evohome-async)

Python client to asynchronously access the [Total Connect Comfort](https://international.mytotalconnectcomfort.com/Account/Login) RESTful API.

It provides support for Resideo TCC-based systems, such as **Evohome**, **Round Thermostat**, **VisionPro** and others:

- it supports _only_ EU/EMEA-based systems, please use (e.g.) [somecomfort](https://github.com/mkmer/AIOSomecomfort) for US-based systems
- it provides Evohome support for [Home Assistant](https://www.home-assistant.io/integrations/evohome) and other automation platforms

> **NOTE:** the vendor API available to this library does not currently support cooling.

This client _requires_ the [aiohttp](https://pypi.org/project/aiohttp/) library. If you prefer a non-async client, [evohome-client](https://github.com/watchforstock/evohome-client) uses [requests](https://pypi.org/project/requests/) instead.

## CLI for schedules (currently WIP)

To install a basic CLI:

```bash
pip install 'evohome-async[cli]'

evo-client --help
```

For example, to backup schedules (including DHW, if any):

```bash
evo-client -u username@gmail.com -p password get-schedules --loc-idx 2 > schedules.json
```

... and to restore:

```bash
evo-client -u username@gmail.com -p password set-schedules --loc-idx 2 -f schedules.json
```

To avoid exceeding the vendor's API rate limit, it will restore the access token cache, unless you use the `--no-load-tokens` switch.

> **NOTE:** the client may save your access tokens to **.evo-cache.tmp**: this presents a small security concern.

## Example code

```python
websession = aiohttp.ClientSession()
token_manager = TokenManager(username, password, websession)
await token_manager.load_access_token()

evo = EvohomeClient(token_manager)
await evo.update()

...

await token_manager.save_access_token()
await websession.close()
```

## Differences from non-async version

It is loosely based upon <https://github.com/watchforstock/evohome-client>, but async-aware.

The difference between the **evohome-async** and **evohome-client** libraries are significant, but it should be relatively straightforward to port your code over to this async library should you wish.

For example, entity ID attrs are `.id` and no longer `.dhwId`, `zoneId`, etc.

Other differences include (but are not limited to):

- namespace is refactored (simpler), and attrs are `snake_case` rather than `camelCase`
- all datetimes are now TZ-aware internally, and exposed as such
- can import schedule JSON by name as well as by zone/dhw id
- newer API exposes a **TokenManager** class (for authentication) and an **Auth** class (for authorization)
- older API exposes a **SessionManager** (for authentication) and an **Auth** class (for authorization)
- exceptions are parochial (e.g. `AuthenticationFailedError`) rather than generic (`TypeError`)
- improved logging: better error messages when things do go wrong
- additional logging: e.g. logs a warning for any active faults
- is now fully typed, including TypedDicts and py.typed
- uses best of class linting/typing via **ruff**/**mypy**
- more extensive testing via **pytest**
- (WIP) extended compatibility beyond pure evohome systems (e.g. VisionPro)

---

## Development

This is how to set up a development environment.

### Prerequisites

- Python 3.14 for local dev (HA stable requires 3.14); Python 3.13 is also tested in CI
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
git clone https://github.com/zxdavb/evohome-async
cd evohome-async

uv sync --all-extras  # creates .venv/ Python pinned via .python-version

prek install  # install pre-commit git hooks
```

### Running tests and linting

```bash
source .venv/bin/activate

ruff check .
ruff format --check .
mypy
pytest --cov=src --cov-report=term-missing
prek run --all-files  # all pre-commit hooks
```

Alternatively, prefix each command with `uv run` to skip activation.
