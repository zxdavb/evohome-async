![ruff](https://github.com/zxdavb/evohome-async/actions/workflows/check-lint.yml/badge.svg)
![mypy](https://github.com/zxdavb/evohome-async/actions/workflows/check-type.yml/badge.svg)
![pytest](https://github.com/zxdavb/evohome-async/actions/workflows/check-test.yml/badge.svg)

evohome-async
==============

Python client to _asynchronously_ access the [Total Connect Comfort](https://international.mytotalconnectcomfort.com/Account/Login) RESTful API.

It is loosely based upon https://github.com/watchforstock/evohome-client, but async-aware.

It provides support for Resideo TCC-based systems, such as **Evohome**, **Round Thermostat**, **VisionPro** and others:
 - it supports _only_ EU/EMEA-based systems, please use (e.g.) [somecomfort](https://github.com/mkmer/AIOSomecomfort) for US-based systems
 - it provides Evohome support for Home Assistant (and other automation platforms), see https://www.home-assistant.io/integrations/evohome

This client requires the [aiohttp](https://pypi.org/project/aiohttp/) library. If you prefer a non-async client, [evohome-client](https://github.com/watchforstock/evohome-client) uses [requests](https://pypi.org/project/requests/) instead.

> **NOTE:** The evohome API does not currently support cooling.


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

> Beware that the client will always save your tokens to **.evo-cache.tmp**: this presents a small security concern.

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

### Differences from non-async version (out of date)
The difference between the **evohomeasync** and **evohomeclient** libraries have been kept to the minimum, and it is planned for existing docs to be useful.  Thus, it should be relatively easy to port your code over to this async library should you wish.

The non-async documentation (from **evohomeclient**) is available at http://evohome-client.readthedocs.org/en/latest/

#### Technical differences (out of date)
Some additional functionality has been added to the methods that wrap the vendor APIs (e.g. restore schedules by name, as an alternative to by id). Note that this library is not able to expose more _core_ functionality than it's non-async cousin (i.e. they both use the same vendor API).

Note that since **0.4.0**, some attributes have been renamed, and a few have been deprecated altogether (when required, an informative exception will be thrown).

In both cases (`evohomeclient2` and `evohomeclient`):
 - requires **aiohttp** instead of **requests**:
 - added a new instantiation argument, `session` to allow the client to utilize the consumer's **aiohttp** session
 ```python
    self._session = kwargs.get('session', aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ))
```

For the newer evohome API (evohomeclient2):
 - `import evohomeasync2` instead of `import evohomeclient2`
 - must invoke `await client.login()` after instntiating `EvohomeClient`
 - generic `Exceptions` have changed...
    `requests.ConnectionError` becomes: `aiohttp.ClientConnectionError`
    `requests.HTTPError` becomes `aiohttp.ClientResponseError`
 - but in most case, exceptions are no longer generic (since **0.4.0**)...
    `RateLimitExceeded`, and `AuthenticationFailed` (among others)

For the older evohome API (evohomeclient):
 - `import evohomeasync` instead of `import evohomeclient`
 - Exceptions change similar to the above

Other minor changes:
 - some attrs/methods have been renamed (invoking the old name will advise the new name)
 - `Hotwater.zoneId` is deprecated (can use `.dhwId`, or `_id`)
 - `ZoneBase.zone_type` is deprecated (use `.TYPE`))
 - some sentinel values are now `None`
