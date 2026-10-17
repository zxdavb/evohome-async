# fixtures_v0/hass_141882

Source: [Home Assistant core issue #141882](https://github.com/home-assistant/core/issues/141882)

## System

- Location: 7680795 (Australia)
- User: 6324020 (en-AU, real userId from report)

## Files

| File | Source |
|------|--------|
| `user_info.json` | Constructed from `account_info.json` in report; PII replaced, no sessionId |
| `user_locs.json` | From `locations.json` in report; serial/PCB numbers zeroed, PII replaced |

## Notes

- v2 counterpart: `fixtures_v2/hass_141882/`
- Original `locations.json` had masked MAC addresses (`************`); kept as-is.
- Serial numbers (`serialNumber`, `pcbNumber`) zeroed to `"000000000000"` / `"00000000000000"`.
