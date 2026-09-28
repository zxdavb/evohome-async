# fixtures_v2/hass_179414

Source: [Home Assistant core issue #179414](https://github.com/home-assistant/core/issues/179414)
(upstream: [evohome-async issue #145](https://github.com/zxdavb/evohome-async/issues/145))

## System

- Location: 5508661 (Australia)
- Gateway: 5231562
- TCS: 7171354 (`Saratoga`)
- 1 zone: THERMOSTAT (7171354, `Saratoga`)
- No DHW
- Timezone: `AUSEasternStandardTime` (UTC+10:00), without daylight saving switching

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4578816 (real), Australia |
| `user_locations.json` | From the original report (redacted); PII replaced |
| `status_5508661.json` | From later comments (including its two zone faults); PII replaced |
| `schedule_zone.json` | From a later comment; times and setpoints substituted by the reporter, structure (incl. `fanMode`) as returned |

## Notes

- The reason for this fixture: both the TCS and its zone report a `modelType` of
  `Saratoga`, and the zone's `allowedFanModes` include `Circulate`. None of these were
  known, so the schema rejected the whole `installationInfo` response, and the
  integration could not load at all.
- Once that was fixed, the zone's schedule was rejected too: each switchpoint has a
  `fanMode`, which the schedule schema did not allow.
- The zone has two active faults of types unknown to `TccFaultType` (`NeedToRegisterOnline`, since
  2022, with a 7-digit fraction of a second; and `ReminderTimerHumPad`), so they are passed
  through as str and logged as unknown.
- The zone status has a `fanStatus`, and a `targetHeatTemperature` of 4.5 (the zone's
  `minHeatSetpoint`), as the system is `Off`.
- The report arrived pre-redacted by the reporter, with masks that preserved the length
  of the original strings (e.g. `"TH********"`). These were replaced with synthesised
  values per the PII policy in the parent README; `mac`/`crc` were zero-filled, and the
  timezone `displayName` (not PII) was restored. The reporter's `username` mask had
  also dropped its opening quote, so their JSON was not valid as posted.
- The zone name `THERMOSTAT` is synthesised (as used by `hass_141882/`, also in
  Australia).
- The real IDs from the report are kept. The zone ID is the same as the TCS ID, as it is
  in `hass_141882/` (a `Sydney` system).
