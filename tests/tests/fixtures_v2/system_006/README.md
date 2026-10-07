# fixtures_v2/system_006

Synthesised fixture — minimal single-zone system (Belgium).

## System

- Location: 0001 (Belgium, placeholder IDs)
- Gateway: 0002
- TCS: 0003
- 1 zone: Main Room (0004)
- No DHW
- Timezone: `RomanceStandardTime` (UTC+01:00, Brussels)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000006, Belgium |
| `user_locations.json` | Synthesised; fixed `-REDACTED-` values from original |
| `status_0001.json` | Synthesised status for location 0001 |
| `status_0002.json` | Synthesised secondary status |
| `schedule_zone.json` | Synthesised — as `default/`, but with an invalid setpoint (see below) |

## Notes

- Placeholder IDs (0001, 0002, 0003, 0004) — this is a minimal test system.
- Original `user_locations.json` had `-REDACTED-` placeholder values for mac, crc, and
  locationOwner; replaced with synthesised values per PII policy.
- The zone schedule has a `heatSetpoint` of 4.0 (Monday, 08:00), below the schema's
  minimum of 4.5, so it fails validation: `Zone.get_schedule()` raises
  `InvalidScheduleError` (not `BadApiResponseError`), and `ControlSystem.get_schedules()`
  returns an empty schedule for the zone. The value is valid per `TccZonSwitchpointT`
  (a float), so the fixture still passes `test_schemas.py`.
