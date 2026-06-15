# fixtures_v2/hass_094805

Source: [Home Assistant core issue #94805](https://github.com/home-assistant/core/issues/94805)

## System

- Location: 1111111 (Australia)
- Gateway: 2222222
- TCS: 3333333
- 1 zone: THERMOSTAT (3333333)
- No DHW
- Timezone: `AUSEasternStandardTime` (UTC+10:00, Sydney)
- Device type: FocusProWifi

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000012, Australia |
| `user_locations.json` | Migrated from `schemas_0/hass_094805/config.json`; PII replaced |
| `status_1111111.json` | From `schemas_0/hass_094805/status.json` |

## Notes

- FocusProWifi device — single-zone thermostat without `scheduleCapabilities` in config.
  The `Zone.schedule_capabilities` property raises `KeyError` for this device type;
  `serializable_attrs()` in `common.py` catches this correctly.
- Location/gateway/system IDs (1111111, 2222222, 3333333) are likely placeholders; kept from original.
- Migrated from `schemas_0` format.
