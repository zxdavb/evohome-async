# fixtures_v2/evohome_145

Source: [evohome-async issue #145](https://github.com/zxdavb/evohome-async/issues/145)
(downstream: [HA core issue #179414](https://github.com/home-assistant/core/issues/179414))

## System

Wholly synthesised: the report included only the error message, not a debug dump. The
shape is based on `hass_141882/` (a `Sydney` system, also in Australia).

- Location 4001011 — gateway 4001012, TCS 4001013 (`Saratoga`), 1 zone (4001014)
- Location 4001018 — gateway 4001015, TCS 4001016, 1 zone (4001017)
- No DHW
- Timezone: `AUSEasternStandardTime` (UTC+10:00, Sydney)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised |
| `user_locations.json` | Synthesised |
| `status_4001011.json` | Synthesised |
| `status_4001018.json` | Synthesised |

## Notes

- The TCS `modelType` of `Saratoga` is as reported in the issue.
- These values are deliberately not members of their `Tcc*` enums (and never will be),
  so that the vendor's enums being incomplete is exercised by the existing tests:
  - zone 4001014: `modelType` of `NoSuchModelType`
  - TCS 4001016: `modelType` of `NoSuchModelType`
  - zone 4001017: `zoneType` of `NoSuchZoneType`

  Each should be passed through as a (snake_case) str, and logged as unknown. Do not
  "fix" them by adding them to the enums, as that would silently remove this coverage.
- There are two locations only because the snapshot tests assume at most one gateway
  per location.
