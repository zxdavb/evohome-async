# Ledger: rebuild `tests/tests_rf` as `tests/tests_api` (+ `tests/tests_live`)

Working document (prompt: `.vscode/18-vendor-api-test-suite-prompt.md`). Deleted at the
end (Phase 5), once its lasting content is in module docstrings.

## Next step

Phase 3, U14: `v1/test_get_device.py` (Q6: every other v1 GET, via `Auth.request()`, as
the client has no schemas for them): locations?locationId (a dict), ±allData;
locations?userId sans allData; gateways?locationId ±allData; devices?locationId ±allData;
devices/{id}; devices/{id}/thermostat; devices/{id}/thermostat/changeableValues (adds
*ChangeSource). Payloads derived by nesting from USR_LOCS where possible; the gateway's
from the old docstring (gatewayID, mac, crc, locationId, isUpgrading, isRedlinkGateway).

Notes: a test with > 5 params makes them keyword-only (`*,`), for PLR0917. Payloads use the Tcc* StrEnums (and, v1, the id NewTypes); ids redacted
(20000xx). `mock` is autouse; client fixtures clear `mock.requests` after setup; each
test has its own token cache (tests_api/conftest.py::cache_path). Mark a done verdict /
fact home with ✓.

## Status

| Phase | Unit | State |
| ----- | ---- | ----- |
| 1 | Audit: inventory, vendor facts, debt, plan | done 2055cf0 (approved 2026-11-13, see Decisions) |
| 2 | U1 `aioresponses.py`: non-JSON responses (e.g. a 404's HTML), additive, own commit | done f06d05d |
| 2 | U2 `tests_api/conftest.py` (`mock`), `v2/conftest.py` (`ec2`, entities), `v2/vendor.py` | done 8bd33f0 |
| 2 | U3 `v1/conftest.py` (`ec1`, entities), `v1/vendor.py` | done 2bde958 |
| 3 | U4 `v2/test_auth.py` (token POST: password & refresh grants; bearer) | done d9344aa |
| 3 | U5 `v2/test_get.py` (userAccount, installationInfo, location status) | done ff2d9ff |
| 3 | U6 `v2/test_get_entity.py` (every other GET URL: loc config, gwy/TCS/zone/DHW config & status) | done 50b100c |
| 3 | U7 `v2/test_comm_task.py` | done c217c1d |
| 3 | U8 `v2/test_tcs_put.py` | done 125e0ca |
| 3 | U9 `v2/test_zone_put.py` | done ab35949 |
| 3 | U10 `v2/test_dhw_put.py` | done 97fa5c7 |
| 3 | U11 `v2/test_schedule.py` | done 28f93fd |
| 3 | U12 `v1/test_auth.py` (session POST; sessionId header) | done 6432d56 |
| 3 | U13 `v1/test_get.py` (accountInfo, locations?userId) | done (this commit) |
| 3 | U14 `v1/test_get_device.py` (every other GET URL: locations?locationId, gateways, devices, device, thermostat, changeableValues) | todo |
| 3 | U15 `v1/test_comm_task.py` | todo |
| 3 | U16 `v1/test_zone_put.py` (heatSetpoint & changeableValues forms) | todo |
| 3 | U17 `v1/test_dhw_put.py` | todo |
| 3 | U18 `v1/test_tcs_put.py` | todo |
| 4 | U19 `tests_live/` (conftest, `test_v2.py`, `test_v1.py`); run once (with the maintainer's credentials); record outcome | todo |
| 5 | U20 delete `tests_rf/`, the fake's hook in `tests/conftest.py`, the mypy override (D19), unused `_DBG_*`; update CONTRIBUTING; fold ledger into docstrings; delete ledger | todo |

## Plan

### Findings that shape it

- Of 70 collected `tests_rf` tests, **8 run in CI**; 62 skip (D18). The fake has no v1
  at all, and no TCS/zone/DHW PUT, and no DHW. So the old suite tests almost none of the
  wire contract in CI.
- `tests/tests` mocks **above** the wire (`AbstractAuth.request` / `Auth.get`, with
  snake_case JSON and relative URLs), except the credential flows
  (`test_v{1,2}_urls_cred.py`, via `aioresponses`). So the new suite is additive: full
  URL, camelCase body, HTTP status → exception, vendor JSON → entity state.
- L0 is `Auth.get()` / `Auth.put()` / `Auth.request()` (`_evohome/auth.py`, shared): they
  convert keys/datetimes/enums, so an L0 test asserts the camelCase wire form.
- L1: v2 `ControlSystem._put_mode()`, `Zone._put_mode()`, `HotWater._put_mode()`; v1
  `ControlSystem._put_mode()`, `Zone._set_heat_setpoint()`, `HotWater._set_dhw()`;
  plus `CommTask.from_put()` / `get_state()` (both versions).
- L2: v2 `setup()`, `Location.get_status()`, `set_mode()`/`set_*()`/`reset()` (TCS,
  zone, DHW), `get_schedule()`/`set_schedule()`, `CommTask.wait()`; v1 `get_status()`,
  `Zone.set_temperature()`/`set_zone_auto()`, `HotWater.set_dhw_on/off/auto()`,
  `ControlSystem.set_mode()`/`set_*()`, `get_temperatures()`.

### Layout

```text
tests/tests_api/
  __init__.py
  conftest.py         # `mock` (a fresh AioResponses, entered after the client is set up),
                      # `client_session` (a real aiohttp.ClientSession: aioresponses
                      # patches it); knows neither v1 nor v2
  v2/
    __init__.py
    conftest.py       # ec2 (set up from v2/vendor.py, its setup GETs mocked), loc/tcs/zone/dhw
    vendor.py         # recorded v2 payloads (Tcc*T-typed), with provenance; the endpoint
                      # table & API-wide conventions in its docstring
    test_get.py       # userAccount, installationInfo, location status: L0 + setup()/get_status(); 401/400/404/429/500
    test_comm_task.py # 201 + id; GET commTasks (states, 404 CommTaskNotFound, 400s); wait() → CommTaskFailedError
    test_tcs_put.py   # PUT .../mode: _put_mode bodies; set_mode()/set_*()/reset(); 400/401/500
    test_zone_put.py  # PUT .../heatSetpoint: _put_mode bodies; set_mode()/set_temperature()/reset(); 400/401/500
    test_dhw_put.py   # PUT .../state: _put_mode bodies; set_mode()/set_on/off()/reset(); 400/401
    test_schedule.py  # GET/PUT .../schedule (zone & DHW); 400 DayOfWeekMissing/ScheduleNotFound/DHWNotFound; ghost zone
  v1/
    __init__.py
    conftest.py       # ec1 (set up from v1/vendor.py), tcs/zone/dhw
    vendor.py         # recorded v1 payloads; endpoint table & conventions in its docstring
    test_get.py       # accountInfo, locations?userId&allData: L0 + get_status(); 401/400/404
    test_comm_task.py # int id; GET commTasks (Succeeded, started…); 404/400
    test_zone_put.py  # PUT .../heatSetpoint: bodies (local NextTime); set_temperature()/set_zone_auto(); DeviceIsLost
    test_dhw_put.py   # PUT .../changeableValues: bodies; set_dhw_on/off/auto(); ForbiddenParameter, DeviceIsLost
    test_tcs_put.py   # PUT evoTouchSystems: removed by the vendor, 404 HTML → ApiCallRejectedError
tests/tests_live/
  __init__.py
  conftest.py         # skip all unless enabled (Q1); real session & token cache; reset at end
  test_v2.py          # replay each recorded v2 request: status, content type, factory_* shape
  test_v1.py          # same for v1
```

Also (per Q6/Q7): `v2/test_auth.py`, `v2/test_get_entity.py`, `v1/test_auth.py`,
`v1/test_get_device.py` (see Status). `tests/tests/test_v{1,2}_urls_cred.py` test the
client's re-auth logic; the new `test_auth.py` modules document the wire contract of
each POST and its responses.

### Conventions for the new tests (from §4.2, made concrete)

- `ec2`/`ec1` fixtures: register the setup GETs on their own `AioResponses`, set up the
  client, exit; the test's `mock` is a new one, so `mock.requests` holds only the test's
  calls. The token cache is the unexpired one of `tests/conftest.py` (no POST).
- Assert the request with `mock.assert_called_once_with(url, method, json=...)` (it is a
  partial match on kwargs, so pass `json=` explicitly; a `{}`/absent body is `json=None`).
- Each error test asserts the exception class, `status`, `reason`, and `details["code"]`.
- Recorded payloads: literal JSON, annotated `Final[Tcc…T]`; ids redacted to the fake's.

## Inventory

Layer: L0 = URL (raw `Auth`), L1 = `_put_*`, L2 = public method. "real-only" = skipped
unless `_DBG_USE_REAL_AIOHTTP` (the fake can't serve it). Verdicts: *port* / *merge* →
new home; *drop*: reason. "live" = the request is replayed by `tests_live`.

### test_v2_urls.py (all real-only)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_tcs_urls | L0 | GET userAccount, usr locations, loc status (+ unused: loc/gwy/tcs config & status, without-TCSs variants; nested == standalone); PUT tcs mode Away/temp + Auto; Away with `untilTime` → 400 SystemModeChangeTimeUntilNotSet | — | — | ✓ merge → v2/test_get, v2/test_get_entity (unused GETs, Q6), v2/test_tcs_put; live |
| test_zon_urls | L0 | PUT heatSetpoint Temp/Perm(PascalCase key)/Follow; `untilTime` → 400 HeatSetpointChangeTimeUntilNotSet; GET+PUT zone schedule | — | — | ✓ merge → v2/test_zone_put, v2/test_schedule |
| test_dhw_urls | L0 | PUT dhw state Temp/Perm/Follow; `timeUntil` → 400 DHWUntilTimeNotSet; GET+PUT dhw schedule | — | — | ✓ merge → v2/test_dhw_put, v2/test_schedule |

### test_v2_urls_auth.py

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_usr_account | L0 | GET ok; PUT → 405 JSON; `userXxxxxxx` → 404 HTML | runs | — | ✓ merge → v2/test_get (ok; 404 HTML); 405 → live |
| test_usr_locations | L0 | ok; PUT → 405; no query → 404 JSON; userId=1230000 → 401; =xxxxxxx → 400; unknown key → 404 | runs | — | ✓ merge → v2/test_get (401); 405/400/404 → live |
| test_loc_status | L0 | ok; PUT → 405; `location/{id}` → 404 HTML; 1230000 → 401; xxxxxxx → 400; `/{id}/xxxxxxx` → 404 HTML | runs | — | ✓ merge → v2/test_get; 405/400/404 → live |
| test_tcs_status | L0 | GET mode → 405; `{}` → 400 ParameterIsMissing ×2 (SystemMode, Permanent); xxxxx → 400 InvalidInput; Cool (not allowed) → **500**; Auto/Away ok; foreign id → 401; `/systemMode` → 404 HTML | skips | — | ✓ port → v2/test_tcs_put (400/401/500 mapping); 405/404 → live |
| test_zone_status | L0 | GET heatSetpoint → **404 HTML**; Perm w/o value → 400 …TargetTemperatureNotSet; Perm + `timeUntil: null` ok; 99 ok; Temp w/o until → …TimeUntilNotSet; xxxxx → InvalidInput; Follow + 0.0 ok | skips | — | ✓ port → v2/test_zone_put; GET 404 → live |
| test_dhw_status | L0 | PUT status → 405; GET state → 405; `{}` → ParameterIsMissing (Mode); bad mode/state → InvalidInput; Perm w/o state → DHWStateNotSet; Temp w/o until → DHWUntilTimeNotSet; Pascal keys ok; foreign id → 401; `/mode` → 404 HTML | skips (no DHW) | — | ✓ port → v2/test_dhw_put; 405/404 → live |
| test_ids_not_the_users | L0 | foreign id → 401 Unauthorized, every URL, GET & PUT; user's id of wrong type → 400 DHWNotFound / TemperatureZoneNotFound / ScheduleNotFound | skips | — | ✓ port → v2/test_get, v2/test_schedule, v2/test_*_put (401); live (GETs only) |
| test_url_case_insensitive | L0 | path/base/query keys case-insensitive; controls | real-only | — | port → live |
| test_case_insensitive | L0 | PUT keys & enum values case-insensitive, not snake_case | real-only | — | port → live (all are rejected PUTs: harmless) |

### test_v2_urls_cred.py (all real-only)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| _test_bad0 (disabled) | L0 | POST to the host's IP → cert error | — | — | ✓ drop: disabled; a TLS fact, not of the API (one line in v2/vendor.py docstring) |
| test_bad1 | L0 | password grant, bad user → 400 invalid_grant | — | tests/test_v2_urls_cred::test_bad1 | ✓ port → v2/test_auth (Q7); live (cred flag) |
| test_bad2 | L0 | bad bearer → 401 `[Unauthorized 'Unauthorized.']` | — | …::test_bad2 | ✓ port → v2/test_auth; live |
| test_bad3 | L0 | refresh grant, bad → 400 (sent as GET: D7) | — | …::test_bad3 | ✓ port (fixed: a POST, D7) → v2/test_auth; live (cred flag) |
| test_good | L0 | password grant → 200; bearer ok; refresh → 200 | — | …::test_good | ✓ port → v2/test_auth; live (cred flag) |

### test_setup.py (all real-only)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_update_v1 | L2 | NotFetchedError before `get_status()` | — | tests/test_client_setup::test_v1_setup | ✓ drop: duplicate; wire → v1/test_get |
| test_update_v2 | L2 | same, via `setup()` | — | …::test_v2_setup | ✓ drop: duplicate; wire → v2/test_get |

### test_v2_urls_task.py

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_task_id_dhw | L0 | DHW PUT → 201 `{'id': '840367013'}`; Pascal keys ok; swapped values → 400 InvalidInput ×2 (enum & path in message); commTaskId ABC → 400; 12345678 → 404 | real-only | — | ✓ merge → v2/test_dhw_put (InvalidInput ×2), v2/test_comm_task |
| _out_test_task_id_zone (disabled) | — | GETs a zone status, asserts nothing | — | — | ✓ drop: disabled, no assertion |
| test_comm_task_ids | L0 | 12345678 → 404 CommTaskNotFound; ABC → 400 InvalidInput; '' → 400 ParameterIsMissing; no query → 404 JSON; `0{id}` normalised | real-only | tests/test_v2_comm_task (above the wire) | ✓ port → v2/test_comm_task; normalisation → live |

### test_v2_urls_sked.py

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_schedule_put | L0 | PUT `null` → 400 ParameterIsMissing (`request`); `{}` → 400 DayOfWeekMissing; valid → 201 | runs (D8) | — | ✓ port → v2/test_schedule (400 mapping, 201); bad bodies → live |
| test_schedule_tsk | L0 | PUT a changed schedule; GET shows it; restore | runs (tests the fake: D9) | — | ✓ drop: tests the fake; a real round trip needs a live gateway (offline), and changes state |
| test_schedule_get_schema_zon | L0 | GET keys camelCase; dayOfWeek a name; types | runs (D9) | tests/test_schedules (snake side) | ✓ merge → v2/test_schedule (parse) + live (shape) |
| test_schedule_get_schema_dhw | L0 | same for DHW | skips | — | ✓ merge → v2/test_schedule + live |

### test_v2_urls_limits.py (all real-only; each PUT waits for its task, then GETs status)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_tcs_until_outside_config[×5] | L0 | out-of-spec untils accepted; until reported to the minute | — | tests/test_v2_apis (client side) | ✓ drop: needs a live gateway (offline since 2026-11-04) and changes state; facts (probed 2026-11-04) → v2/test_tcs_put docstring |
| test_zon_setpoint_outside_config[×6] | L0 | same for zone setpoints/untils | — | same | ✓ drop: as above; facts → v2/test_zone_put docstring |
| test_zon_setpoint_rejected | L0 | Temp w/o until → 400; Advance* → 400 InvalidInput; int 4 → 500 | — | — | ✓ merge → v2/test_zone_put (400 & 500 mapping) + live (all rejected: harmless) |
| test_zon_vacation_hold_task_fails | L0 | VacationHold on a zone lacking it → 201, task fails | — | tests/test_v2_apis_edges | ✓ merge → v2/test_comm_task (Failed → CommTaskFailedError); fact → v2/test_zone_put docstring |
| test_dhw_until_outside_config[×3] | L0 | DHW untils accepted; status `until`; w/o untilTime → 400 | — | — | ✓ merge → v2/test_dhw_put (400); rest drop as above, facts → docstring |

### test_v2_apis.py

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_usr_apis | L2 | `setup()` + `get_status()`; SCH_* truthiness (D11) | runs | tests/test_client_setup, test_v2_installs (above wire) | ✓ merge → v2/test_get (L2, with the exact GETs) |
| test_tcs | L2 | set_mode Away / Eco +1h / Away 1-day period / restore | skips | tests/test_v2_apis (above wire) | ✓ port → v2/test_tcs_put (L2: the wire form of a duration & a period) |
| test_dhw_apis | L2 | dhw get_schedule/set_schedule | skips | — | ✓ port → v2/test_schedule |
| test_dhw_mode | L2 | set_off, set_mode Temp+duration, reset | skips | tests/test_v2_apis | ✓ port → v2/test_dhw_put |
| test_zon_apis | L2 | zone get/set_schedule; ghost zone → InvalidGetScheduleError | runs (ghost branch dead: D10) | tests/test_v2_exceptions::test_ghost_zone (above wire) | ✓ port → v2/test_schedule (incl. the ghost zone's 400 ScheduleNotFound) |
| test_zon_mode | L2 | set_temperature(min), set_mode Temp+duration, reset | skips | tests/test_v2_apis | ✓ port → v2/test_zone_put |

### test_vx_until.py (real-only; uses BOTH v1 and v2: D14)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_v1_next_time | L0 | v1 NextTime is local; Z ignored; v2 until = sent − offset | — | tests/test_v1_next_time | merge → v1/test_zone_put (docstring + L1 body); cross-API check: Q3 |
| test_v2_time_until | L0 | v2 timeUntil is UTC; v1 nextTime = sent + offset | — | — | ✓ merge → v2/test_zone_put (docstring + L1 body); cross-API check: Q3 |
| test_v1_client_until | L2 | v1 `set_temperature(until=)` sends local NextTime | — | tests/test_v1_next_time | port → v1/test_zone_put (L2, exact body, DST via patched `now()`) |

### test_v1_urls.py (all real-only)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_loc_urls | L0 | accountInfo; locations ±allData; locationId; gateways; devices; device; thermostat; changeableValues (key relations) | — | — | merge → v1/test_get, v1/test_get_device (the other GETs, Q6); live |
| test_tcs_urls | L0 | PUT evoTouchSystems → 404 | — | — | port → v1/test_tcs_put |
| test_zon_urls | L0 | PUT heatSetpoint Scheduled; PUT changeableValues `{Mode, HeatSetpoint}` | — | — | merge → v1/test_zone_put (both forms, Q6) |
| test_dhw_urls | L0 | PUT changeableValues `{Mode}` | — | — | merge → v1/test_dhw_put |
| test_comm_task_ids | L0 | 404 CommTaskNotFound; ABC/'' → 400 InvalidInput; no query → 404 JSON | — | tests/test_v1_comm_task (above wire) | port → v1/test_comm_task |

### test_v1_urls_auth.py (all real-only; the fake has no v1)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_usr_locations | L0 | ok; PUT → 404; sans allData ok; 123456 → 401; `'123456'` → 400; `xxxxxxx` → 404 HTML | skips | — | ✓ merge → v1/test_get (401, 404 HTML); rest → live |
| test_evo_systems | L0 | evoTouchSystems GET & PUT → 404 HTML | real-only | — | merge → v1/test_tcs_put; GET → live |
| test_zon_heat_setpoint | L0 | Temporary with Pascal & camel keys applied; nextTime == sent sans Z; revert | real-only | — | merge → v1/test_zone_put (bodies; facts in docstring); applied-state checks dropped: need a live gateway |
| test_dhw_changeable_values | L0 | `{Mode}` and `{mode}` accepted | real-only | — | merge → v1/test_dhw_put |
| test_dhw_forbidden_params | L0 | ParameterIsMissing; ForbiddenParameter (Status, NextTime); full revert body → ForbiddenParameter; sans Status → 201; Off → ThermostatModeNotAllowed; Auto → InvalidInput | real-only | — | port → v1/test_dhw_put (each 400 → ApiCallRejectedError code); bodies → live |
| test_url_case_insensitive | L0 | as v2 | real-only | — | port → live |
| test_case_insensitive | L0 | keys/values case-insensitive; NoSuchStatus → InvalidInput | real-only | — | port → live |
| test_zon_lost | L0 | lost zone → 400 DeviceIsLost | real-only | — | port → v1/test_zone_put + live (the test gateway is offline: harmless) |
| test_dhw_lost | L0 | lost DHW → 400 DeviceIsLost | real-only | — | port → v1/test_dhw_put + live |
| (USER_DATA, FULL_DATA) | — | unused payloads (D16) | — | — | merge → v1/vendor.py (provenance: old tests_rf) |

### test_v1_urls_cred.py (all real-only)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| _test_bad0 (disabled) | L0 | IP → cert error | — | — | ✓ drop: disabled; TLS, not the API |
| test_bad1 | L0 | bad creds → 401 EmailOrPasswordIncorrect | — | tests/test_v1_urls_cred::test_bad1 | ✓ port → v1/test_auth (Q7); live (cred flag) |
| test_bad2 | L0 | bad sessionId → 401 `[Unauthorized 'Unauthorized']` | — | …::test_bad2 | ✓ port → v1/test_auth; live |
| test_good | L0 | session 200; accountInfo 200 (D17) | — | …::test_good | ✓ port → v1/test_auth; live (cred flag) |

### test_v1_apis.py (all real-only)

| Test | L | Asserts | Fake | Overlap | Verdict |
| ---- | - | ------- | ---- | ------- | ------- |
| test_usr_apis | L2 | `get_status()`; `get_temperatures(dont_update_status=True)` keys == zone ids | — | tests/test_v1_status (above wire) | ✓ merge → v1/test_get |
| test_tcs_apis | L2 | `set_auto()` → ApiCallFailedError 404 | — | — | port → v1/test_tcs_put |
| test_dhw_apis | L2 | set_dhw_on/off(until=), set_dhw_auto() | — | — | port → v1/test_dhw_put |
| test_zon_apis | L2 | set_temperature(until=), set_temperature(), set_zone_auto() (no Value) | — | tests/test_v1_next_time | port → v1/test_zone_put |

## Vendor facts

Where: T = a mocked test (module), D = a module docstring, LIVE = the live suite. All
homes are planned until their unit is done.

| # | Fact | Source | Where |
| - | ---- | ------ | ----- |
| V2-1 | Base `https://tccna.resideo.com/WebAPI/emea/api/v1`; token at `/Auth/OAuth/Token` (off the base); its cert is for the hostname only | v2_urls, v2_urls_cred | D v2/vendor.py ✓ |
| V2-2 | Every entity has `installationInfo` & `status`; a TCS's include its zones/DHW; a loc's/gwy's include TCSs iff `includeTemperatureControlSystems=True` | v2_urls | T v2/test_get_entity ✓, D v2/vendor.py ✓; LIVE |
| V2-3 | An entity's installationInfo/status == the object nested in its parent's | v2_urls | T v2/test_get_entity ✓ (payloads derived by nesting), D ✓; LIVE |
| V2-4 | GET → 200; PUT → 201 + comm task `{"id": "1668279943"}` (a str) | v2_urls | T v2/test_comm_task ✓ |
| V2-5 | A PUT is sometimes answered with the comm task of an earlier, equivalent PUT (rule unknown) | v2_urls, common | D v2/test_comm_task ✓ |
| V2-6 | GET of a PUT-only URL → 405 JSON `{'message': "The requested resource does not support http method 'GET'."}`, except zone heatSetpoint → 404 HTML | v2_urls_auth | D v2/vendor.py ✓, v2/test_zone_put ✓; LIVE |
| V2-7 | Unknown path → 404 HTML (`<!DOCTYPE html PUBLIC …`); no/unknown query key → 404 JSON `{'message': "No HTTP resource was found that matches the request URI '…'."}` | v2_urls_auth | T v2/test_get ✓; LIVE |
| V2-8 | Responses camelCase; URL path (incl. base) & query keys, and request keys & enum values, case-insensitive (not snake_case: `permanent_override` → InvalidInput) | v2_urls, v2_urls_auth | D v2/vendor.py ✓; LIVE |
| V2-9 | TCS/zone TemporaryOverride needs `timeUntil`, DHW `untilTime` (the other key → 400 *TimeUntilNotSet / DHWUntilTimeNotSet) | v2_urls | T v2/test_tcs_put ✓, v2/test_zone_put ✓, v2/test_dhw_put ✓ |
| V2-10 | A 400 body is a list of `{code, message}` (+ `parameterName`, PascalCase, e.g. SystemMode, Permanent, Mode) | v2_urls_auth, common | T v2/test_tcs_put ✓ (and B1) |
| V2-11 | 400 codes: ParameterIsMissing, InvalidInput, SystemModeChangeTimeUntilNotSet, HeatSetpointChangeTimeUntilNotSet, HeatSetpointChangeTargetTemperatureNotSet ('Target temperature not specified when required'), DHWStateNotSet ('Domestic hot water state is not set when required'), DHWUntilTimeNotSet ('Domestic hot water until time is not set when required') | v2_urls_auth | T v2/test_tcs_put ✓, v2/test_zone_put ✓, v2/test_dhw_put ✓ |
| V2-12 | An enum-valid systemMode the TCS lacks (e.g. Cool), or a setpointMode int ≥ 4 → 500 `{'message': 'An error has occurred.'}` | v2_urls_auth, v2_urls_limits | T v2/test_tcs_put ✓, v2/test_zone_put ✓; LIVE |
| V2-13 | Any id not the user's (exists or not) → 401 `[{'code': 'Unauthorized', 'message': 'You are not allowed to perform this action.'}]`, any URL, GET or PUT | v2_urls_auth | T v2/test_get ✓ (GET), v2/test_*_put (PUT); LIVE |
| V2-14 | The user's id of the wrong type → 400 DHWNotFound ('Domestic Hot Water {id} not found.') / TemperatureZoneNotFound ('Temperature Zone {id} not found.') / ScheduleNotFound ('Schedule not found.') | v2_urls_auth | T v2/test_get_entity ✓ (DHWNotFound, TemperatureZoneNotFound), v2/test_schedule ✓ (ScheduleNotFound); LIVE |
| V2-15 | A non-numeric id → 400 | v2_urls_auth | D v2/vendor.py ✓; LIVE |
| V2-16 | `{"setpointMode": "PermanentOverride", "heatSetpointValue": x, "timeUntil": null}` accepted; FollowSchedule with a value (0.0) accepted; value 99 accepted | v2_urls_auth | D v2/test_zone_put ✓ |
| V2-17 | Without includeTemperatureControlSystems: gwy installationInfo keys == `[gatewayInfo]`; gwy status == `[activeFaults, gatewayId]` | v2_urls | T v2/test_get_entity ✓; LIVE |
| V2-18 | A location may have no gateways (newly created) | v2_urls | D v2/test_get ✓ (parsed by tests/tests/test_client_setup::test_v2_location_tcs_none) |
| V2-19 | A gateway's fault, e.g. `GatewayCommunicationLost`, `since` "2025-02-23T22:34:25.04" (fractional, TZ-naive) | v2_urls | T v2/test_get ✓ (LOC_STATUS_OVERRIDDEN) |
| V2-20 | Token POST (form): `grant_type=password, scope="EMEA-V1-Basic EMEA-V1-Anonymous", Username, Password`, Basic app-id header → 200 `{access_token, token_type: bearer, expires_in: 1799, refresh_token, scope?}`; bad → 400 `{"error": "invalid_grant"}`; rate limit → 429 `{"error": "attempt_limit_exceeded"}`; refresh grant likewise | v2_urls_cred | T v2/test_auth ✓; LIVE (cred flag) |
| V2-21 | Bad/expired bearer → 401 `[{"code": "Unauthorized", "message": "Unauthorized."}]`: differs from a foreign-id 401 only by message | v2_urls_cred, memory | T v2/test_auth ✓, D v2/vendor.py ✓; LIVE |
| V2-22 | commTasks `?commTaskId={id}` → 200 `{'commtaskId': '840367013', 'state': 'Created'}` (or Running / Succeeded / Failed); unknown numeric → 404 CommTaskNotFound 'Communication task not found.'; non-numeric → 400 InvalidInput 'Invalid Input.'; empty → 400 ParameterIsMissing; no query → 404 JSON; `0{id}` normalised; any user's task readable (no 401) | v2_urls_task, memory | T v2/test_comm_task ✓ (ParameterIsMissing's message assumed); LIVE |
| V2-23 | InvalidInput message names the .NET enum & JSON path (one error per bad field), e.g. `Error converting value 'Off' to type 'DomesticHotWater.Enums.EMEADomesticHotWaterSetpointMode'. Path 'mode', line 1, position 44.` | v2_urls_task | T v2/test_dhw_put ✓ |
| V2-24 | Schedule PUT: `null` → 400 ParameterIsMissing (`parameterName: request`); `{}` → 400 DayOfWeekMissing 'One or more days missing.'; valid → 201 | v2_urls_sked | T v2/test_schedule ✓; LIVE |
| V2-25 | Schedule GET camelCase; `dayOfWeek` a name ("Monday"), not an ordinal; `heatSetpoint` float; `dhwState` On/Off; `timeOfDay` "HH:MM:SS" | v2_urls_sked | T v2/test_schedule ✓; LIVE |
| V2-26 | An until beyond maxDuration / off timingResolution / ≤ now, or (TCS) not of the mode's timingMode, is accepted; status reports it truncated to the minute | v2_urls_limits | D v2/test_tcs_put ✓, v2/test_zone_put ✓, v2/test_dhw_put ✓ (probed 2026-11-04) |
| V2-27 | A heatSetpointValue outside min/max or off valueResolution is accepted and reported as sent | v2_urls_limits | D v2/test_zone_put ✓ |
| V2-28 | Zone setpointMode enum is 0-3 only (ints accepted); no Advance* mode (→ 400 InvalidInput) | v2_urls_limits, memory | T v2/test_zone_put ✓ (InvalidInput, 500), D ✓; LIVE |
| V2-29 | VacationHold (or 3) on a zone lacking it → 201, but its comm task fails | v2_urls_limits | T v2/test_comm_task ✓; D v2/test_zone_put ✓ |
| V2-30 | Status reports TCS `timeUntil`, zone `until`, DHW `until` (the DHW request says `untilTime`) | v2_urls_limits | T v2/test_get ✓ |
| V2-31 | The controller (by hand, 2026-11-04): clamps setpoints to min/max but uses 0.1-resolution values; honours zone/DHW untils beyond max/off res; ends Eco at its until; ignores past untils; runs an Away ending before midnight until midnight; shows >99d as '99d' | v2_urls_limits | D v2/test_tcs_put ✓, v2/test_zone_put ✓ |
| V1-1 | Base `https://tccna.resideo.com/WebAPI/api`; session at `/session`; its cert is for the hostname only | v1_urls, v1_urls_cred | D v1/vendor.py |
| V1-2 | allData=True adds children: a location's devices, oneTouchButtons (+ weather, contractor if any); a gateway's devices; a device's thermostat, alertSettings | v1_urls | D v1/vendor.py; LIVE |
| V1-3 | `locations?locationId=` returns a dict (not a list of one) | v1_urls | D v1/vendor.py; LIVE |
| V1-4 | An entity's own URL == object nested in its parent's, but a device's thermostat lacks changeableValues, and the changeableValues GET adds modeChangeSource / heatSetpointChangeSource `{partnerName: EMEA, changeTag: ""}` (absent for a lost device) | v1_urls | D v1/vendor.py; LIVE |
| V1-5 | ID key casing is inconsistent: userID, locationID, deviceID, gatewayID (of a gateway), but gatewayId (of a device), locationId (of a gateway); ids are ints; `outdootHumidityAvailable` (sic) | v1_urls | T v1/test_get ✓, D v1/vendor.py ✓ |
| V1-6 | URL path/base/query keys and request keys/enum values case-insensitive | v1_urls_auth | D v1/vendor.py; LIVE |
| V1-7 | Datetimes are the location's local time: NextTime returned without a Z; a Z sent is ignored | v1_urls, vx_until | T v1/test_zone_put |
| V1-8 | GET → 200; PUT → 201 + `{"id": 1234567890}` (an int); a list of one allowed by the 2014 client (never seen) | v1_urls, common | T v1/test_comm_task |
| V1-9 | GET of a PUT-only URL → 404 HTML (not 405), as is any unknown path; PUT of a GET URL (locations) → 404 | v1_urls, v1_urls_auth | T v1/test_tcs_put (404 HTML); LIVE |
| V1-10 | Foreign userId → 401; non-numeric (`'123456'`) → 400 | v1_urls_auth | T v1/test_get ✓ (401: its body assumed), D v1/vendor.py ✓; LIVE |
| V1-11 | PUT to a device not alive → 400 `[DeviceIsLost 'Device is lost.']`, whatever the body | v1_urls_auth | T v1/test_{zone,dhw}_put; LIVE |
| V1-12 | A PUT is sometimes answered with an earlier, equivalent PUT's (succeeded) task and not applied (e.g. revert within minutes); bodies need not be identical; detectable by task `started` < sent | v1_urls, common, memory | D v1/test_comm_task |
| V1-13 | A change appears via GET within ~1s of its task succeeding | v1_urls | D v1/test_comm_task |
| V1-14 | `evoTouchSystems?locationId=` (TCS mode) removed: 404 HTML (IIS '404 - File or directory not found') for GET and PUT | v1_urls, v1_apis | T v1/test_tcs_put; LIVE |
| V1-15 | Zone `.../heatSetpoint`: `{Value, Status: Hold/Temporary/Scheduled, NextTime}`, PUT-only; or via changeableValues `{Mode: Heat/Off, HeatSetpoint: {...}}` ("Allowed modes are Heat, Off." → ThermostatModeNotAllowed) | v1_urls | T v1/test_zone_put; D (changeableValues form) |
| V1-16 | DHW changeableValues `{Mode: DHWOn/DHWOff}`; on the test system a non-null Status/NextTime → 400 ForbiddenParameter ("'Status' is forbidden."), `{}`/Mode null → ParameterIsMissing ("'ThermostatMode' is required."), "Off" → ThermostatModeNotAllowed, "Auto" → InvalidInput; nulls & unknown keys ignored; a mode-only PUT is not applied (test system) | v1_urls_auth, memory | T v1/test_dhw_put; D |
| V1-17 | Hold w/o Value → 400 ParameterIsMissing "'Value' is required."; NoSuchStatus → InvalidInput | v1_urls_auth | T v1/test_zone_put; LIVE |
| V1-18 | commTasks: `{state, started, finished?, macId, gatewayId, deviceId, activityId}` (no task id; TZ-naive UTC); Succeeded is terminal; 12345678 → 404 CommTaskNotFound; ABC → 400 InvalidInput "The value 'ABC' is not valid for Int32"; '' → 400 InvalidInput (v2: ParameterIsMissing); no query → 404 JSON; zero-padded id = same task; any user's task readable (leaks mac/device ids) | v1_urls, common, memory | T v1/test_comm_task; LIVE |
| V1-19 | Session POST (form) `applicationId, username, password` → 200 `{sessionId (a GUID), userInfo{userID int, …}}`; bad → 401 `[EmailOrPasswordIncorrect 'The email or password provided is incorrect.']`; rate limit → 429 `[TooManyRequests 'Request count limitation exceeded, please try again later.']`; bad sessionId header → 401 `[Unauthorized 'Unauthorized']` (no full stop) | v1_urls_cred | T v1/test_auth ✓; LIVE (cred flag) |
| V1-20 | The older client sent PascalCase bodies, this library camelCase: both accepted | v1_urls_auth | T v1/test_*_put (camelCase); D |
| V1-21 | Honeywell TH9320WF3003 can send thermostatModelType as an int | common | D v1/test_get (or T, if the library handles it) |
| V1-22 | A v1 comm task once took 29 s (2026-10-07) | const | D tests_live conftest (or drop with `TIMEOUT_COMM_TASK_V1`) |
| VX-1 | v2 timeUntil is UTC (status `until` UTC with Z); v1 NextTime is local (Z ignored; `nextTime` local, no Z) | vx_until | T v1/test_zone_put & v2/test_zone_put (each its own half, no cross-reference) |
| VX-2 | The v1 client sent NextTime in UTC between v2.0.0 and v3.0.0 (so ended early by the UTC offset) | vx_until | D v1/test_zone_put |

## Debt found

- D1: `test_v2_urls.py` tests are all real-only: never run in CI.
- D2: `test_v2_urls_auth.py` tcs/zone/dhw/ids tests catch the fake's `NotImplementedError` and skip; the fake has no DHW, so DHW tests always skip.
- D3: `should_fail_v{1,2}` 'strict' asserts tie status to body shape loosely, and are skipped entirely with `_DBG_DISABLE_STRICT_ASSERTS`.
- D4: The unused-API code (`_DBG_TEST_UNUSED_APIS`) never runs by default.
- D5: Three v2 PUT-and-wait helpers (`_put` ×2, `should_work_v2`); two `error_codes` helpers.
- D6: `tests/conftest.py::client_session` imports the fake (`type: ignore[assignment]`); goes with the fake.
- D7: v2 `test_bad3` sends the refresh grant with **GET**, not POST: it does not test the refresh grant.
- D8: The fake's `ClientSession.put` does `data or json`, so a `{}` body becomes `None`: test_schedule_put's `{}` case passes for the wrong reason.
- D9: test_schedule_tsk / test_schedule_get_schema_zon on the fake test only the fake.
- D10: `GHOST_ZONE_ID = "0000000"` (was "3432521"), so test_zon_apis's ghost-zone branch never runs.
- D11: `assert SCH_*(x)` (test_usr_apis, v1 & v2) cannot fail: a validator raises, never returns falsy.
- D12: `_out_test_task_id_zone`, `_test_bad0` (×2) are disabled by name.
- D13: Every v2 PUT of a mode is untested in CI by tests_rf (the fake lacks them).
- D14: test_vx_until mixes v1 and v2.
- D15: The fake has no v1 (every handler raises NotImplementedError): all 26 v1 tests are real-only.
- D16: `USER_DATA`/`FULL_DATA` (end of test_v1_urls_auth.py) are unused.
- D17: v1 test_good: the accountInfo comment shows a *locations* list, and its final assert re-checks `user_auth`, not `user_info`.
- D18: Of 70 collected tests, 8 run in CI; the ~1.4k-line fake serves those 8, 3 of which test only the fake.
- D19: `pyproject.toml` has a mypy override for `tests.tests_rf.faked_server.vendor` (Q2).

## Bugs found

- B1 (documentation; not severe): `TccFailureResponseT` and `factory_failure_response()`
  (`src/evohomeasync2/schemas/account.py`) lack the vendor's optional `parameterName`,
  and the validator is PREVENT_EXTRA, so `TCC_FAILURE_RESPONSE` rejects a real
  ParameterIsMissing body, e.g. `[{"code": "ParameterIsMissing", "parameterName":
  "SystemMode", "message": "Parameter is missing."}]` (seen for a TCS PUT of `{}`, and a
  schedule PUT of `null`: `parameterName: request`). Not used at runtime by the
  library. Repro: `TCC_FAILURE_RESPONSE(_PARAMETERS_ARE_MISSING)` raises. Test:
  `v2/test_tcs_put.py::test_failure_response_schema` (xfail strict). The v1 schema may
  need the same (check at U17). Fix: `parameterName: NotRequired[str]` + `vol.Optional`.

Observations to check in Phase 3 (not bugs by the rules here: the library is
based on the older client & vendor docs, not on the test system's quirks):

- O1: v1 `HotWater.set_dhw_auto()` sends `{status: Scheduled, mode: null}`; the test system answers 400 (ParameterIsMissing / ForbiddenParameter).
- O2: v1 `ControlSystem.set_*()` all PUT the removed `evoTouchSystems` URL, so always fail (404).
- O3: v1 `ControlSystem.reset()` raises a bare `NotImplementedError` (CONTRIBUTING rule 4).

## Decisions / open questions

Ruled by the maintainer, 2026-11-13 (answers to the Phase 1 questions):

- Q1: keep `_DBG_USE_REAL_AIOHTTP` as the live switch. Remove `_DBG_TEST_UNUSED_APIS`
  and `_DBG_DISABLE_STRICT_ASSERTS`. Keep `_DBG_WAIT_FOR_COMM_TASKS` (Q5) and
  `_DBG_TEST_CRED_URLS` (Q7).
- Q2: yes: U20 removes the mypy override for `tests.tests_rf.faked_server.vendor`, and
  updates CONTRIBUTING's *Project structure*.
- Q3: split `test_vx_until.py` into a v1-only and a v2-only half; drop the cross-check.
- Q4: record from the fake's payloads and `tests/tests/fixtures_v{1,2}/` for now; the
  maintainer will give access to the real API for the final validation (U19), or sooner
  if needed.
- Q5: the live suite replays **all** PUTs (it ends by resetting the system to Auto /
  FollowSchedule). With `_DBG_WAIT_FOR_COMM_TASKS`, it polls each PUT's comm task and
  checks its outcome, especially of those expected to fail (their failure code/message).
- Q6: test **every known URL** (mocked, at L0, via `Auth.get()`/`put()`; NB:
  `Auth.get()` snake_cases the response before validating it, so its schema is the
  client's `SCH_*`/`factory_*(Case.PYTHONIC)`, not the vendor's `TCC_*`), and every URL wrapped in a method also at that method (e.g.
  `Location._get_config()`, `Zone/HotWater._get_status()`).
- Q7: add mocked auth tests (`v1/test_auth.py`: session; `v2/test_auth.py`: token), and
  live ones gated by `_DBG_TEST_CRED_URLS` (to avoid an account lockout).
- Q8 (superseded by Q7): the old real-only cred tests are ported, not dropped.
