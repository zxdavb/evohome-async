# fixtures_v2/hass_118169

Source: [Home Assistant core issue #118169](https://github.com/home-assistant/core/issues/118169)

## System

- Location: 2730000 (Australia)
- Gateway: 2750000
- TCS: 2760000
- 1 zone: THERMOSTAT (2770000)
- No DHW
- Timezone: `AUSEasternStandardTime` (UTC+10:00, Sydney)
- Device type: FocusProWifi

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 2512649, Australia |
| `user_locations.json` | From original report; real MAC address replaced with `000000000000` |
| `status_2730000.json` | From original report |

## Notes

- FocusProWifi device — single-zone thermostat without `scheduleCapabilities` in config.
- The original report had a real MAC address; replaced with `"000000000000"` per PII policy.
- The `@REDACTED.com` username in the original was replaced with the synthesised form.
- The real userId 2512649 is kept from the original report.
