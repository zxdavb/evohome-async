# fixtures_v2/hass_102505

Source: [Home Assistant core issue #102505](https://github.com/home-assistant/core/issues/102505)

## System

- Location: 678433 (United Kingdom)
- Gateway: 689757
- TCS: 745047
- 12 zones: Landing (745059), Kitchen (745060), Matts bedroom (745061),
  Guest Bedroom (745062), Bathroom (745063), Sues Bedroom (770656),
  Basement One (786904), Sitting Room (790431), Basement Two (2136063),
  Dining room (2136064), Hall (2136171), Dressing Room (8573729)
- No DHW
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000015, UK |
| `user_locations.json` | Migrated from `schemas_0/hass_102505/config.json`; PII replaced |
| `status_678433.json` | From `schemas_0/hass_102505/status.json` |
| `temperatures.json` | Temperature log from original report (informational) |
| `schedules.py.txt` | Schedule data from original report (informational) |

## Notes

- 12-zone system, the maximum supported by EvoTouch.
- Migrated from `schemas_0` format.
