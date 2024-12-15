![ruff](https://github.com/zxdavb/evohome-async/actions/workflows/check-lint.yml/badge.svg)
![mypy](https://github.com/zxdavb/evohome-async/actions/workflows/check-type.yml/badge.svg)
![pytest](https://github.com/zxdavb/evohome-async/actions/workflows/check-test.yml/badge.svg)

evohome-async
==============

Python client to _asynchronously_ access the [Total Connect Comfort](https://international.mytotalconnectcomfort.com/Account/Login) RESTful API.

It provides support for Resideo TCC-based systems, such as **Evohome**, **Round Thermostat**, **VisionPro** and others:
 - it supports _only_ EU/EMEA-based systems, please use (e.g.) [somecomfort](https://github.com/mkmer/AIOSomecomfort) for US-based systems
 - it provides Evohome support for [Home Assistant](https://www.home-assistant.io/integrations/evohome) and other automation platforms

> **NOTE:** the TCC API used by the library does not currently support cooling.

This client _requires_ the [aiohttp](https://pypi.org/project/aiohttp/) library. If you prefer a non-async client, [evohome-client](https://github.com/watchforstock/evohome-client) uses [requests](https://pypi.org/project/requests/) instead.

### CLI for schedules (currently WIP)
If you download the git repo you can use a basic CLI for backup/restore of schedules (incl. DHW, if any), for example:
```
python client.py -u username@gmail.com -p password get-schedules --loc-idx 2 > schedules.json
```
... and to restore:
```
python client.py -u username@gmail.com -p password set-schedules --loc-idx 2 -f schedules.json
```

To avoid exceeding the vendor's API rate limit, it will restore the access token cache, unless you use the the `--no-tokens` switch.

> **NOTE:** the client may save your access tokens to **.evo-cache.tmp**: this presents a small security concern.

### Example code...
```python
websession = aiohttp.ClientSession()
token_manager = TokenManager(username, password, websession, cache_file=CACHE_FILE)
await token_manager.load_access_token()

evo = EvohomeClient(token_manager)
await evo.update()

...

await token_manager.save_access_token()
await websession.close()
```

### Differences from non-async version
It is loosely based upon https://github.com/watchforstock/evohome-client, but async-aware.

The difference between the **evohome-async** and **evohome-client** libraries are significant, but it should be relatively straightforward to port your code over to this async library should you wish.

For example, entity ID attrs are `.id` and no longer `.dhwId`, `zoneId`, etc.

Other differences include:
 - uses the **aiohttp** client and not **requests**
 - namespace is simpler (different) and is `snake_case` and not `camelCase`
 - parochial exceptions (e.g. **AuthenticationFailedError**) rather than generics (**TypeError**)
 - uses a **TokenManager** (for authentication) and an **Auth** (for authorization) class
 - is fully typed, including **TypedDict**s and `py.typed`
 - additional functionality (e.g. throws a warning for any active faults)
 - better error messages when things go wrong
 - extended compatability beyond pure evohome systems
 - more extensive testing via **pytest**
 - uses best of class linting/typing via **ruff**/**mypy**
 - schedule JSON import by name as well as by zone/dhw id

The non-async documentation (from **evohomeclient**) is available at http://evohome-client.readthedocs.org/en/latest/
