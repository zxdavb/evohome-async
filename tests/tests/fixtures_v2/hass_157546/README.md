# fixtures_v2/hass_157546

Source: [Home Assistant core issue #157546](https://github.com/home-assistant/core/issues/157546)

## System

- Location: 7647411 (United Kingdom)
- Gateway: 7539089
- TCS: 10090510
- 5 zones: Zone 1 (10090505), Zone 2 (10090506), Zone 3 (10090507),
  Zone 4 (10090508), Zone 5 (10090509)
- No DHW
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000007, UK |
| `user_locations.json` | Synthesised from status zones (status-only report) |
| `status_7647411.json` | From original report (renamed from `status_10090510.json`) |

## Notes

- Status-only fixture: `user_locations.json` was synthesised from status zone data.
- The status file was originally named after the system ID (10090510); renamed to use the
  correct location ID (7647411) per the gen-3 naming convention.
