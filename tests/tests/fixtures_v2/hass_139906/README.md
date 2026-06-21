# fixtures_v2/hass_139906

Source: [Home Assistant core issue #139906](https://github.com/home-assistant/core/issues/139906)

## System

- Location: 2727366 (Netherlands)
- Gateway: 2513794
- TCS: 3454856
- 2 zones: Thermostat (3454854), Thermostat 2 (3454855)
- No DHW
- Timezone: `WEuropeStandardTime` (UTC+01:00, Amsterdam)

## Files

| File | Source |
|------|--------|
| `user_account.json` | From original report; PII replaced (names, address) |
| `user_locations.json` | From `installation_info.json` in original report; MAC/CRC fixed |
| `status_2727366.json` | From original report |
| `schedule_3454854.json` | Zone 1 schedule from original report |
| `schedule_3454855.json` | Zone 2 schedule from original report |

## Notes

- Real userId 2276512 and locationId 2727366 kept from original.
- v0 counterpart: `fixtures_v0/hass_139906/`
