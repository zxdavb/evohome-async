# Ledger: rebuild `tests/tests_rf` as `tests/tests_api` (+ `tests/tests_live`)

Working document (prompt: `.vscode/18-vendor-api-test-suite-prompt.md`). Deleted at the
end (Phase 5), once its lasting content is in module docstrings.

## Next step

Phase 1 (audit) in progress: finish the inventory (modules not yet read are marked
`TODO` below), then write the module breakdown & open questions, commit, push, STOP.

## Status

| Phase | Unit | State |
| ----- | ---- | ----- |
| 1 | Audit: inventory, vendor facts, debt, plan | doing |

## Inventory

Layer: L0 = URL (raw `Auth` request), L1 = `_put_*`, L2 = public method.
"real-only" = skipped unless `_DBG_USE_REAL_AIOHTTP` (the fake can't serve it).

### test_v2_urls.py (all real-only)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_tcs_urls | L0 | GET userAccount, usr locations, loc status (+ unused: loc/gwy/tcs config & status, without-TCSs variants; nested == standalone); PUT tcs mode Away/temp + Auto; Away with `untilTime` → 400 SystemModeChangeTimeUntilNotSet | none | — | TODO |
| test_zon_urls | L0 | PUT heatSetpoint Temp/Perm(PascalCase key)/Follow; `untilTime` → 400 HeatSetpointChangeTimeUntilNotSet; GET+PUT zone schedule (round trip) | none | — | TODO |
| test_dhw_urls | L0 | PUT dhw state Temp/Perm/Follow; `timeUntil` → 400 DHWUntilTimeNotSet; GET+PUT dhw schedule | none | — | TODO |

### test_v2_urls_auth.py

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_usr_account | L0 | GET userAccount ok; PUT → 405 JSON; `userXxxxxxx` → 404 HTML | usr_account, 404 HTML | — | TODO |
| test_usr_locations | L0 | GET installationInfo?userId=&incTCS ok; PUT → 405; no query → 404 (JSON); userId=1230000 → 401; userId=xxxxxxx → 400; unknown query key → 404 | all_config, validate_id_of_url | — | TODO |
| test_loc_status | L0 | GET loc status ok; PUT → 405; `location/{id}` → 404 HTML; 1230000 → 401; xxxxxxx → 400; `/{id}/xxxxxxx` → 404 HTML | loc_status | — | TODO |
| test_tcs_status | L0 | GET mode → 405; PUT `{}` → 400 ParameterIsMissing ×2 (SystemMode, Permanent; PascalCase parameterName); systemMode xxxxx → 400 InvalidInput; Cool (not allowed) → **500** `{'message': 'An error has occurred.'}`; Auto/Away ok; restore; foreign id → 401 Unauthorized; `/systemMode` → 404 HTML | **tcs_mode NotImplemented → skipped on fake** | — | TODO |
| test_zone_status | L0 | GET heatSetpoint → **404 HTML** (not 405); PermOverride w/o value → 400 HeatSetpointChangeTargetTemperatureNotSet; Perm + `"timeUntil": None` ok; value 99 accepted; Temp w/o timeUntil → 400 HeatSetpointChangeTimeUntilNotSet; mode xxxxx → InvalidInput; Follow + value 0.0 ok | **zon_mode NotImplemented → skipped on fake** | — | TODO |
| test_dhw_status | L0 | (unused) PUT status → 405; GET state → 405; `{}` → 400 ParameterIsMissing (Mode); mode xxxxx / state xxxxx → InvalidInput; Perm w/o state → DHWStateNotSet; Temp w/o until → DHWUntilTimeNotSet; PascalCase keys ok; Follow (no state) ok; foreign id → 401; `/mode` → 404 HTML | **dhw_mode NotImplemented; fake has no DHW → skipped** | — | TODO |
| test_ids_not_the_users | L0 | foreign id (1234567, 999999999) → 401 Unauthorized for GET loc/tcs/zon/dhw status & schedules, PUT schedules, PUT mode/heatSetpoint/state, GET loc installationInfo; user's id of wrong type → 400 DHWNotFound / TemperatureZoneNotFound / ScheduleNotFound | PUT modes raise NotImplemented → skipped on fake | test_v2_urls_task? (no) | TODO |
| test_url_case_insensitive | L0 | path & base path & query keys case-insensitive; no include → no TCSs; no userId → 404 JSON; unknown path → 404 HTML | real-only | — | TODO |
| test_case_insensitive | L0 | PUT body keys & enum values case-insensitive (Pascal/upper/lower/camel), snake_case value → InvalidInput | real-only | — | TODO |

### test_v2_urls_cred.py (all real-only)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| _test_bad0 (disabled: `_` prefix) | L0 | POST to the host's IP → ClientConnectorCertificateError | — | — | TODO |
| test_bad1 | L0 | POST token, password grant, bad user → 400 `{"error": "invalid_grant"}` | — | tests/test_v2_urls_cred::test_bad1 | TODO |
| test_bad2 | L0 | GET userAccount, bad bearer → 401 `[{"code": "Unauthorized", "message": "Unauthorized."}]` | — | tests/…::test_bad2 | TODO |
| test_bad3 | L0 | refresh grant, bad token → 400 invalid_grant (**sent as GET, not POST**: D7) | — | tests/…::test_bad3 | TODO |
| test_good | L0 | password grant → 200 token (expires_in 1799, scope optional); bearer → userAccount 200; refresh grant → 200 | `_DBG_TEST_CRED_URLS` | tests/…::test_good | TODO |

### test_setup.py (all real-only)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_update_v1 | L2 | `user_account` raises NotFetchedError before `get_status()`, set after | — | tests/test_client_setup? | TODO |
| test_update_v2 | L2 | same, via `setup()` | — | tests/test_client_setup? | TODO |

### test_v2_urls_task.py

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_task_id_dhw | L0 | real-only (in-body skip); DHW PUT Temp → 201 `{'id': '840367013'}`; Pascal keys ok; swapped mode/state values → 400 InvalidInput ×2 (`Error converting value 'TemporaryOverride' to type 'DomesticHotWater.Enums.EMEADomesticHotWaterState'. Path 'state'…`); commTaskId=ABC → 400 InvalidInput 'Invalid Input.'; 12345678 → 404 CommTaskNotFound 'Communication task not found.' | — | — | TODO |
| _out_test_task_id_zone (disabled) | — | only GETs the zone status | — | — | TODO |
| test_comm_task_ids | L0 | 12345678 → 404 CommTaskNotFound (list); ABC → 400 InvalidInput; '' → 400 ParameterIsMissing; `commTasks` (no query) → 404 JSON dict; `0{id}` → 200, commtaskId normalised (no leading 0) | real-only | tests/test_v2_comm_task | TODO |

### test_v2_urls_sked.py

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_schedule_put | L0 | GET zone schedule; PUT `null` → 400 ParameterIsMissing parameterName `request`; PUT `{}` → 400 DayOfWeekMissing 'One or more days missing.'; PUT valid → 201 | **runs on fake**, but the fake turns `{}` into None (`data or json`), so `{}` passes for the wrong reason (D8) | — | TODO |
| test_schedule_tsk | L0 | PUT changed schedule, GET shows it; restore | runs on fake (fake stores PUTs) — tests the fake (D9) | — | TODO |
| test_schedule_get_schema_zon | L0 | GET schedule keys camelCase; dayOfWeek is "Monday" (not ordinal); heatSetpoint float; timeOfDay str | runs on fake (tests the fake's canned JSON) | tests/test_schedules? | TODO |
| test_schedule_get_schema_dhw | L0 | same for DHW (dhwState On/Off) | fake has no DHW → skip | — | TODO |

### test_v2_urls_limits.py (all real-only; every PUT waits for its task)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_tcs_until_outside_config[×5] | L0 | Eco beyond max / off resolution / under resolution / in the past; Away not at midnight: accepted, status reports until truncated to the minute | — | tests/test_v2_apis (client-side checks) | TODO |
| test_zon_setpoint_outside_config[×6] | L0 | zone until beyond max / off res; setpoint below min / above max / off res; past: accepted, reported as sent (until to the minute) | — | — | TODO |
| test_zon_setpoint_rejected | L0 | Temp w/o timeUntil → 400 HeatSetpointChangeTimeUntilNotSet; AdvancedOverride/AdvanceOverride/Advance/NextPeriod → 400 InvalidInput; int 4 → 500 'An error has occurred.' | — | — | TODO |
| test_zon_vacation_hold_task_fails | L0 | VacationHold (name, and int 3) accepted (201), task → CommTaskFailedError; status not VacationHold | — | — | TODO |
| test_dhw_until_outside_config[×3] | L0 | DHW until beyond max / off res / past accepted; status `until` (not untilTime) to the minute; Temp w/o untilTime → 400 DHWUntilTimeNotSet | — | — | TODO |

### test_v2_apis.py

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_usr_apis | L2 | `setup()` + `loc.get_status()`; re-validates with SCH_* (asserts truthiness of a validator's output only) | **runs on fake** (usr_account, all_config, loc_status) | tests/test_v2_installs, test_client_setup | TODO |
| test_tcs | L2 | set_mode Away, Eco +1h duration, Away 1-day period, restore; no request asserted | tcs_mode NotImplemented → skip | tests/test_v2_apis (thorough) | TODO |
| test_dhw_apis | L2 | dhw get_schedule/set_schedule round trip | no DHW → skip | tests/test_schedules? | TODO |
| test_dhw_mode | L2 | set_off, set_mode Temp+duration, reset | no DHW → skip | tests/test_v2_apis | TODO |
| test_zon_apis | L2 | zone get_schedule/set_schedule; ghost zone get_schedule → InvalidGetScheduleError | **runs on fake**; ghost branch is dead (D10) | tests/test_schedules? | TODO |
| test_zon_mode | L2 | set_temperature(min), set_mode Temp+duration, reset | zon_mode NotImplemented → skip | tests/test_v2_apis | TODO |

### test_vx_until.py (real-only; uses BOTH v1 and v2: conflicts with "v1/v2 separate")

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_v1_next_time | L0 | v1 NextTime (with/without Z) is local time; v1 nextTime as sent sans Z; v2 until = sent − offset | — | tests/test_v1_next_time | TODO |
| test_v2_time_until | L0 | v2 timeUntil is UTC; v1 nextTime = sent + offset | — | — | TODO |
| test_v1_client_until | L2 | v1 `Zone.set_temperature(until=)` sends local NextTime, so v2 until == instant | — | tests/test_v1_next_time | TODO |

### test_v1_urls.py (all real-only)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_loc_urls | L0 | accountInfo; locations?userId (±allData: adds devices, oneTouchButtons, [contractor, weather]); locations?locationId (a dict, not a list; same keys); gateways?locationId (gatewayID set == devices' gatewayId; allData adds `devices`); devices?locationId (±allData: adds alertSettings, thermostat); devices/{id} == sans-allData; thermostat sans changeableValues; changeableValues adds modeChangeSource/heatSetpointChangeSource | — | — | TODO |
| test_tcs_urls | L0 | PUT evoTouchSystems → 404 (removed by the vendor; IIS HTML) | — | — | TODO |
| test_zon_urls | L0 | PUT heatSetpoint Scheduled (no-op); PUT changeableValues `{Mode, HeatSetpoint: {...}}` | — | — | TODO |
| test_dhw_urls | L0 | PUT changeableValues `{Mode}` (current mode, no-op) | — | — | TODO |
| test_comm_task_ids | L0 | 12345678 → 404 CommTaskNotFound; ABC → 400 InvalidInput ('not valid for Int32'); '' → 400 **InvalidInput** (v2: ParameterIsMissing); no query → 404 JSON dict | — | tests/test_v1_comm_task | TODO |

### test_v1_urls_auth.py (all real-only; fake has no v1 at all)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_usr_locations | L0 | locations?userId&allData ok; PUT → **404** (not 405); sans allData ok; userId=123456 → 401; `'123456'` → 400; `xxxxxxx` → 404 HTML | v1_locations NotImplemented → skip | — | TODO |
| test_evo_systems | L0 | evoTouchSystems GET and PUT → 404 HTML | — | — | TODO |
| test_zon_heat_setpoint | L0 | Temporary override with Pascal keys and with camel keys, applied (status Temporary); GET nextTime == sent sans Z; revert Scheduled (if not stale) | — | — | TODO |
| test_dhw_changeable_values | L0 | PUT `{Mode}` and `{mode}` accepted | — | — | TODO |
| test_dhw_forbidden_params | L0 | (test system) `{}` / `{Mode: null}` → 400 ParameterIsMissing; Status / NextTime (non-null) → 400 ForbiddenParameter; older client's full revert body → ForbiddenParameter (Status); same sans Status → 201; Mode "Off" → ThermostatModeNotAllowed; "Auto" → InvalidInput | — | — | TODO |
| test_url_case_insensitive | L0 | as v2: path, base path, query keys case-insensitive; controls (no allData → no devices; no userId → 404 JSON; unknown path → 404 HTML) | — | — | TODO |
| test_case_insensitive | L0 | PUT keys & values case-insensitive (`Hold`/`hold`/`HOLD`; `status`/`Status`/`STATUS`): ParameterIsMissing ('Value' is required); NoSuchStatus → InvalidInput | — | — | TODO |
| test_zon_lost | L0 | PUT to a lost zone → 400 DeviceIsLost 'Device is lost.' | — | — | TODO |
| test_dhw_lost | L0 | same for a lost DHW | — | — | TODO |
| (USER_DATA, FULL_DATA) | — | **unused** module-level payloads (session / location) (D16) | — | — | TODO |

### test_v1_urls_cred.py (all real-only)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| _test_bad0 (disabled) | L0 | IP → cert error | — | — | TODO |
| test_bad1 | L0 | POST session, form `applicationId/username/password`, bad → 401 `[EmailOrPasswordIncorrect 'The email or password provided is incorrect.']` | — | tests/test_v1_urls_cred::test_bad1 | TODO |
| test_bad2 | L0 | GET accountInfo, bad `sessionId` header → 401 `[Unauthorized 'Unauthorized']` (no full stop; v2 has one) | — | tests/…::test_bad2 | TODO |
| test_good | L0 | POST session → 200 `{sessionId, userInfo{userID int, …}}`; accountInfo 200 (D17) | `_DBG_TEST_CRED_URLS` | tests/…::test_good | TODO |

### test_v1_apis.py (all real-only)

| Test | L | Asserts | Fake relied on | Overlap | Verdict |
| ---- | - | ------- | -------------- | ------- | ------- |
| test_usr_apis | L2 | `get_status()`; SCH_* truthiness (D11); `tcs.get_temperatures(dont_update_status=True)` keys == zone ids; DHW temp float/None | — | tests/test_v1_status, test_v1_installs | TODO |
| test_tcs_apis | L2 | `tcs.set_auto()` → ApiCallFailedError 404 (evoTouchSystems removed) | — | — | TODO |
| test_dhw_apis | L2 | set_dhw_on/off(until=) (xfail on ForbiddenParameter), set_dhw_auto() | — | — | TODO |
| test_zon_apis | L2 | set_temperature(until=), set_temperature(), set_zone_auto() (sends no Value) | — | tests/test_v1_next_time | TODO |

## Vendor facts

Where: T = a mocked test (module), D = a module docstring, LIVE = the live suite. `?` = not yet placed.

| # | Fact | Source | Where |
| - | ---- | ------ | ----- |
| V2-1 | v2 base `https://tccna.resideo.com/WebAPI/emea/api/v1`; token at `/Auth/OAuth/Token` (off the base) | v2_urls | ? |
| V2-2 | Every entity has `installationInfo` and `status`; a TCS's include its zones/DHW; a loc's/gwy's include TCSs iff `includeTemperatureControlSystems=True` | v2_urls | ? |
| V2-3 | An entity's installationInfo/status == the object nested in its parent's | v2_urls | ? |
| V2-4 | GET → 200; PUT → 201 + comm task `{"id": "1668279943"}` (str) | v2_urls | ? |
| V2-5 | A PUT is sometimes answered with the comm task of an earlier, equivalent PUT (rule unknown) | v2_urls, common | ? |
| V2-6 | GET of a PUT-only URL → 405 JSON `{'message': "The requested resource does not support http method 'GET'."}`, **except** zone heatSetpoint → 404 HTML | v2_urls_auth | ? |
| V2-7 | Unknown path → 404 **HTML** (`<!DOCTYPE html PUBLIC ...`); missing/unknown query key (no userId) → 404 **JSON** `{'message': "No HTTP resource was found that matches the request URI '...'."}` | v2_urls_auth | ? |
| V2-8 | Responses camelCase; URL path (incl. base path) & query keys case-insensitive; request keys & enum values case-insensitive, but not snake_case (`permanent_override` → InvalidInput) | v2_urls, v2_urls_auth | ? |
| V2-9 | TCS/zone TemporaryOverride needs `timeUntil`; DHW needs `untilTime` (the other key → 400 *TimeUntilNotSet / DHWUntilTimeNotSet) | v2_urls | ? |
| V2-10 | 400 error body is a list of `{code, message}` (+ optional `parameterName`, PascalCase e.g. `SystemMode`, `Permanent`, `Mode`) | v2_urls_auth, common | ? |
| V2-11 | 400 codes: ParameterIsMissing, InvalidInput (`Error converting value "xxxxx" to ...`), SystemModeChangeTimeUntilNotSet, HeatSetpointChangeTimeUntilNotSet, HeatSetpointChangeTargetTemperatureNotSet ('Target temperature not specified when required'), DHWStateNotSet ('Domestic hot water state is not set when required'), DHWUntilTimeNotSet | v2_urls_auth | ? |
| V2-12 | A systemMode valid in the enum but not allowed for the TCS (e.g. Cool) → **500** `{'message': 'An error has occurred.'}` | v2_urls_auth | ? |
| V2-13 | Any id not the user's (exists or not) → 401 `[{'code': 'Unauthorized', 'message': 'You are not allowed to perform this action.'}]`, any URL, GET or PUT | v2_urls_auth | ? |
| V2-14 | The user's id of the wrong type → 400 DHWNotFound ('Domestic Hot Water {id} not found.') / TemperatureZoneNotFound ('Temperature Zone {id} not found.') / ScheduleNotFound ('Schedule not found.' — zone schedule with a TCS id) | v2_urls_auth | ? |
| V2-15 | Non-numeric id (`xxxxxxx`) → 400 | v2_urls_auth | ? |
| V2-16 | `{"setpointMode": "PermanentOverride", "HeatSetpointValue": x, "timeUntil": null}` accepted; FollowSchedule with a heatSetpointValue (0.0) accepted; heatSetpointValue 99 accepted (no range check) | v2_urls_auth | ? |
| V2-17 | Without includeTemperatureControlSystems: gwy installationInfo keys == `[gatewayInfo]`; gwy status keys == `[activeFaults, gatewayId]` | v2_urls | ? |
| V2-18 | A location may have no gateways (newly created) | v2_urls | ? |
| V2-19 | Gateway status may carry `GatewayCommunicationLost` fault with `since` "2025-02-23T22:34:25.04" (fractional, TZ-naive) | v2_urls | ? |
| V2-20 | Token POST: password grant, form data `grant_type/scope("EMEA-V1-Basic EMEA-V1-Anonymous")/Username/Password`, Basic app-id header; 200 `{access_token, token_type: bearer, expires_in: 1799, refresh_token, scope?}`; bad creds → 400 `{"error": "invalid_grant"}`; rate limit → 429 `{"error": "attempt_limit_exceeded"}` | v2_urls_cred | ? |
| V2-21 | Bad/expired bearer → 401 `[{"code": "Unauthorized", "message": "Unauthorized."}]` (differs from foreign-id 401 only by message) | v2_urls_cred | ? |
| V2-22 | Refresh grant `grant_type=refresh_token, scope, refresh_token` → 200 token; bad → 400 invalid_grant | v2_urls_cred | ? |
| V2-23 | Token endpoint cert is for the hostname only (an IP fails cert verification) | v2_urls_cred | ? |
| V2-24 | commTasks: `?commTaskId={id}` → 200 `{'commtaskId': '840367013', 'state': 'Created'}` (or Running / Succeeded) (note lower-case t in commtaskId); unknown numeric → 404 `[CommTaskNotFound 'Communication task not found.']`; non-numeric → 400 InvalidInput 'Invalid Input.'; empty → 400 ParameterIsMissing; no query → 404 JSON dict; id normalised (`0{id}` → `{id}`); any user's task readable (no 401) | v2_urls_task, memory | ? |
| V2-25 | InvalidInput message names the .NET enum & JSON path, e.g. `Error converting value 'Off' to type 'DomesticHotWater.Enums.EMEADomesticHotWaterSetpointMode'. Path 'mode', line 1, position 44.`; one error per bad field | v2_urls_task | ? |
| V2-26 | Schedule PUT: `null` body → 400 ParameterIsMissing (`parameterName: request`); `{}` → 400 DayOfWeekMissing 'One or more days missing.'; valid → 201 task | v2_urls_sked | ? |
| V2-27 | Schedule GET is camelCase throughout; `dayOfWeek` is a name ("Monday"), not an ordinal; `heatSetpoint` float, `dhwState` "On"/"Off", `timeOfDay` "HH:MM:SS" | v2_urls_sked | ? |
| V2-28 | A PUT of an until beyond maxDuration / off timingResolution / ≤ now, or (TCS) not of the mode's timingMode, is accepted; the status then reports the until truncated to the minute | v2_urls_limits | ? |
| V2-29 | A heatSetpointValue outside min/max or off valueResolution is accepted and reported as sent | v2_urls_limits | ? |
| V2-30 | Zone setpointMode enum is 0-3 only (ints accepted): unknown name → 400 InvalidInput; int 4 → 500 'An error has occurred.'; no Advance* mode | v2_urls_limits | ? |
| V2-31 | VacationHold (or 3) on a zone lacking it → 201, but the comm task fails | v2_urls_limits | ? |
| V2-32 | DHW status reports `until` (the request says `untilTime`); TCS status `timeUntil`; zone status `until` | v2_urls_limits | ? |
| V2-33 | Controller (by hand, 2026-11-04): clamps setpoint to min/max but uses 0.1-resolution values as is; honours zone/DHW until beyond max/off res; ends Eco at its until to the minute; ignores past untils; runs an Away ending before midnight until midnight; shows >99d as '99d' | v2_urls_limits | ? |
| V2-34 | A Cool (or other enum-valid, not allowed) systemMode → 500 (see V2-12) | v2_urls_auth | ? |
| V1-1 | v1 base `https://tccna.resideo.com/WebAPI/api`; session at `/session` | v1_urls | ? |
| V1-2 | allData=True adds children: a location's devices, oneTouchButtons (+ weather, contractor if any); a gateway's devices; a device's thermostat, alertSettings | v1_urls | ? |
| V1-3 | `locations?locationId=` returns a dict (not a list of one) | v1_urls | ? |
| V1-4 | An entity's own URL == object nested in its parent's, except a device's thermostat lacks changeableValues, and changeableValues GET adds modeChangeSource / heatSetpointChangeSource `{partnerName: EMEA, changeTag: ""}` (absent for a lost device) | v1_urls | ? |
| V1-5 | ID key casing is inconsistent: userID, locationID, deviceID, gatewayID (of a gateway), but gatewayId (of a device), locationId (of a gateway); userID is an int; thermostat key `outdootHumidityAvailable` (sic) | v1_urls | ? |
| V1-6 | URL path/base/query keys and request keys/enum values case-insensitive (incl. lower-case enum values) | v1_urls_auth | ? |
| V1-7 | Datetimes are the location's local time: NextTime is returned without a Z; a Z sent is ignored | v1_urls, vx_until | ? |
| V1-8 | GET → 200; PUT → 201 + `{"id": 1234567890}` (an **int**); the 2014 client allowed a list of one (never seen) | v1_urls, common | ? |
| V1-9 | GET of a PUT-only URL → 404 HTML (not 405), as is any unknown path; PUT of a GET URL (locations) → 404 | v1_urls, v1_urls_auth | ? |
| V1-10 | Foreign userId → 401; non-numeric (`'123456'`) → 400 | v1_urls_auth | ? |
| V1-11 | PUT to a device not alive → 400 `[DeviceIsLost 'Device is lost.']`, whatever the body | v1_urls_auth | ? |
| V1-12 | A PUT is sometimes answered with an earlier, equivalent PUT's (succeeded) task and not applied (e.g. revert-to-schedule within minutes); bodies need not be identical (casing, null vs absent); detect by task `started` < sent | v1_urls, common, memory | ? |
| V1-13 | A change appears via GET within ~1s of its task succeeding | v1_urls | ? |
| V1-14 | `evoTouchSystems?locationId=` (TCS mode) removed: 404 HTML (IIS '404 - File or directory not found') for GET and PUT; no v1 way to set a TCS mode | v1_urls, v1_apis | ? |
| V1-15 | Zone PUT `.../heatSetpoint`: `{Value, Status: Hold/Temporary/Scheduled, NextTime}`; PUT-only; same via changeableValues `{Mode, HeatSetpoint: {...}}` | v1_urls | ? |
| V1-16 | DHW PUT changeableValues `{Mode: DHWOn/DHWOff}`; on the test system Status/NextTime (non-null) → 400 ForbiddenParameter ("'Status' is forbidden."); `{}` / Mode null → ParameterIsMissing ("'ThermostatMode' is required."); Mode "Off" → ThermostatModeNotAllowed; "Auto" → InvalidInput; nulls & unknown keys ignored; mode-only PUT not applied (test system) | v1_urls_auth, memory | ? |
| V1-17 | Zone changeableValues Mode: "Heat"/"Off" ("Allowed modes are Heat, Off.") → ThermostatModeNotAllowed | v1_urls | ? |
| V1-18 | Hold w/o Value → 400 ParameterIsMissing "'Value' is required."; NoSuchStatus → InvalidInput | v1_urls_auth | ? |
| V1-19 | commTasks: `{state, started, finished?, macId, gatewayId, deviceId, activityId}` (no task id; TZ-naive; started is UTC); states Succeeded (terminal), Failed?; 12345678 → 404 CommTaskNotFound; ABC → 400 InvalidInput "The value 'ABC' is not valid for Int32" (> 2147483647 invalid too); '' → 400 InvalidInput; no query → 404 JSON; zero-padded id = same task; any user's task readable (leaks mac/device ids) | v1_urls, common, memory | ? |
| V1-20 | Session POST (form): `applicationId, username, password` → 200 `{sessionId (GUID), userInfo{…}}`; bad → 401 `[EmailOrPasswordIncorrect]`; rate limit → 429 `[TooManyRequests 'Request count limitation exceeded, please try again later.']`; bad `sessionId` header → 401 `[Unauthorized 'Unauthorized']` | v1_urls_cred | ? |
| V1-21 | Old non-async client sent PascalCase bodies; this library sends camelCase; both accepted | v1_urls_auth | ? |
| V1-22 | Honeywell TH9320WF3003 can send thermostatModelType as an int | common | ? |
| V1-23 | A v1 comm task once took 29 s (2026-10-07) | const | ? |
| VX-1 | v2 timeUntil is UTC; v1 NextTime is local time (Z ignored); v2 status `until` is UTC with Z; v1 `nextTime` is local w/o Z | vx_until | ? |
| VX-2 | v1 client sent NextTime in UTC between v2.0.0 and v3.0.0 (ended early by the UTC offset) | vx_until | ? |

## Debt found

- D1: `test_v2_urls.py` tests are all real-only: on the fake they never run (zero coverage in CI).
- D2: `test_v2_urls_auth.py` tcs/zone/dhw/ids tests catch `NotImplementedError` from the fake and skip: in CI they never run. Fake has no DHW, so DHW tests always skip.
- D3: `should_fail_v2` 'strict' asserts tie status to body shape (dict vs list) loosely; with `_DBG_DISABLE_STRICT_ASSERTS` they are skipped entirely.
- D4: `test_v2_urls.py` docstring says the unused APIs are tested "only if _DBG_TEST_UNUSED_APIS": that flag is False, so never run anywhere by default.
- D5: Three v2 PUT-and-wait helpers (`_put` in v2_urls, `_put` in v2_urls_limits, `should_work_v2` in common); two `error_codes` helpers (common, `_error_codes` in limits).
- D6: tests/conftest.py `client_session` fixture imports the fake (`type: ignore[assignment]`) — goes when the fake goes.
- D7: tests_rf/test_v2_urls_cred.py::test_bad3 sends the refresh grant with **GET**, not POST: so it does not test the refresh grant at all.
- D8: The fake's `ClientSession.put` does `data or json`, so a `{}` body becomes `None`: test_schedule_put's `{}` case passes for the wrong reason (the fake's dict-shaped 400 would fail `should_fail_v2`).
- D9: test_schedule_tsk / test_schedule_get_schema_zon on the fake only test the fake's canned JSON / its PUT store.
- D10: `GHOST_ZONE_ID = "0000000"` (was "3432521"), so test_zon_apis's ghost-zone branch never runs.
- D11: test_usr_apis asserts `SCH_*(x)` truthiness: cannot fail (a validator raises, never returns falsy).
- D12: `_DBG_TEST_UNUSED_APIS` gated code never runs by default (and `_out_test_task_id_zone`, `_test_bad0` are disabled by name).
- D13: test_tcs on the fake: `tcs.set_mode(AWAY)` hits `tcs_mode` → NotImplementedError → skip; every v2 PUT of a mode is untested in CI by tests_rf.
- D14: test_vx_until mixes v1 and v2 (against the v1/v2-separation rule).
- D15: The fake has **no v1 at all** (every `v1_*` handler raises NotImplementedError): all 26 v1 tests are real-only.
- D16: `USER_DATA`/`FULL_DATA` at the end of test_v1_urls_auth.py are unused.
- D17: v1 test_good: the comment for accountInfo shows a *locations* list (wrong), and its final assert re-checks `user_auth`, not `user_info`.
- D18: Of 70 collected tests_rf tests, only 8 run in CI (fake); 62 skip. The fake (`faked_server/`, ~1.4k lines) therefore exists to serve 8 tests, 3 of which only test the fake (D9).

## Bugs found

(none yet)

## Decisions / open questions

(to come)
