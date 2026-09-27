# fixtures_v2/system_009

Synthesised: coverage of enum values that are unknown to this library, or are the
vendor's literal `Unknown`.

## System

- Location: 4001021 (UK) — based on `default/`
- Gateway: 4001022
- TCS: 4001023
- 3 zones (4001024-4001026)
- No DHW
- Timezone: `GMTStandardTime`

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised |
| `user_locations.json` | Synthesised |
| `status_4001021.json` | Synthesised |

## Notes

The vendor's enums are incompletely documented, so an unexpected value must not reject
the entire `installationInfo` response (see: evohome-async
[#145](https://github.com/zxdavb/evohome-async/issues/145)). Each of these should be
passed through as a (snake_case) str, and logged as unknown:

| Entity | Field | Value |
|--------|-------|-------|
| TCS 4001023 | `modelType` | `NoSuchModelType` |
| zone 4001024 | `modelType` | `NoSuchModelType` |
| zone 4001025 | `zoneType` | `NoSuchZoneType` |

These values are deliberately not members of their `Tcc*` enums (and never will be). Do
not "fix" them by adding them to the enums, as that would silently remove this coverage.

Zone 4001026 is a ghost zone with a known `modelType`, but a `zoneType` of `Unknown` (the
vendor's own value, see: [HA core #30945](https://github.com/home-assistant/core/issues/30945)).
It should be ignored as invalid. Other fixtures' ghost zones have a `modelType` of
`Unknown` too, so are rejected before their `zoneType` is checked.
