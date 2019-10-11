evohome-async
==============

Build status: [![CircleCI](https://circleci.com/gh/zxdavb/evohome-async.svg?style=svg)](https://circleci.com/gh/zxdavb/evohome-async)

Python client to access the Evohome web service _asynchronously_.  It is a faithful port of https://github.com/watchforstock/evohome-client.  

Note that this library does not (and will not) expose more functionality than it's non-async cousin, other than asyncio.

The difference between the **evohomeasync** and **evohomeclient** libraries have been keep to the minimum, and it is planned for exisiting docs to be useful.  Thus, it should be relatively easy to port your code over to this async library should you wish.

Such documentation (from **evohomeclient**) is available at http://evohome-client.readthedocs.org/en/latest/

Currently, only `evohomeclient2` has been fully tested, and `evohomeclient` (the older API) is a WIP has not been fully tested.

This library is used by Home Assistant, see: http://home-assistant.io/components/evohome/

### Differences between sync and async version (WIP)

In both cases (`evohomeclient2` and `evohomeclient`):
 - uses **aiohttp** instead of **requests**:
 - most instantiation arguments (except for username, password) are now kwargs
 - added a new instantiation argument, `session` to allow the client to utilize teh consumer's session
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
