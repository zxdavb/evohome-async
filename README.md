evohome-async
==============

[![CircleCI](https://circleci.com/gh/zxdavb/evohome-async.svg?style=svg)](https://circleci.com/gh/zxdavb/evohome-async)

Python client to _asynchronously_ access the [Total Connect Comfort](https://international.mytotalconnectcomfort.com/Account/Login) RESTful API.

It is a faithful port of https://github.com/watchforstock/evohome-client, which is not async-aware.

It provides support for **Evohome** and the **Round Thermostat**. It supports only EU/EMEA-based systems, please use [somecomfort](https://github.com/kk7ds/somecomfort) for US-based systems.

This client uses the [aiohttp](https://pypi.org/project/aiohttp/) library. If you prefer a non-async client, [evohome-client](https://github.com/watchforstock/evohome-client) uses [requests](https://pypi.org/project/requests/) instead.

Provides Evohome support for Home Assistant (and other automation platforms), see https://www.home-assistant.io/integrations/evohome

Documentation (from **evohomeclient**) is available at http://evohome-client.readthedocs.org/en/latest/

### Differences from non-async version
Note that this library is not intended to expose more functionality than it's non-async cousin, other than asyncio.

The difference between the **evohomeasync** and **evohomeclient** libraries have been keep to the minimum, and it is planned for exisiting docs to be useful.  Thus, it should be relatively easy to port your code over to this async library should you wish.

Currently, only `evohomeclient2` has been fully tested, and `evohomeclient` (the older API) is a WIP has not been fully tested.

### Technical differences
In both cases (`evohomeclient2` and `evohomeclient`):
 - uses **aiohttp** instead of **requests**:
 - most instantiation arguments (except for username, password) are now kwargs
 - added a new instantiation argument, `session` to allow the client to utilize the consumer's session
 ```python
    self._session = kwargs.get('session', aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ))
```

For the newer evohome API (evohomeclient2):
 - `import evohomeasync2` instead of `import evohomeclient2`
 - need to add a call `await client.login()` after initialising
 - `Exceptions` have changed...
    `requests.ConnectionError` becomes: `aiohttp.ClientConnectionError`
    `requests.HTTPError` becomes `aiohttp.ClientResponseError`

For the older evohome API (evohomeclient):
 - `import evohomeasync` instead of `import evohomeclient`
 - Exceptions change similar to the above
