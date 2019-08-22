evohome-async
==============

Build status: [![CircleCI](https://circleci.com/gh/zxdavb/evohome-async.svg?style=svg)](https://circleci.com/gh/zxdavb/evohome-async)

Python client to access the Evohome web service _asynchronously_.  It is a faithful port of https://github.com/watchforstock/evohome-client.  Currently, only evohomeclient2 has been ported.

Documentation (in progress) at http://evohome-client.readthedocs.org/en/latest/

Provides Evohome support for Home Assistant. See http://home-assistant.io/components/evohome/


### Differences between sync and async version (WIP)

The difference have been keep to teh minimum, and it is planned for exisiting docs to be useful:
 - uses **aiohttp** instead of **requests**:
 - `import evohomeasync2` instead of `import evohomeclient2`
 - some instantiation arguments are now kwargs
 - added session kwarg
 - need to call `await client.login()` after initialising
 - Exceptions change
    `requests.ConnectionError` becomes: `aiohttp.ClientConnectionError`
    `requests.HTTPError` becomes `aiohttp.ClientResponseError`
