# fixtures_v2/evohome_017

Source: [evohome-async issue #17](https://github.com/zxdavb/evohome-async/issues/17)

## System

- Location: 6390479 (Netherlands)
- Gateway: 6008600
- TCS: 8222003
- 7 zones: Woonkamer (8222000), MBR (8222001), BK (8222002), Kantoor (8403459),
  Sauna (8403460), Hut (8403596), (unnamed) (8222004)
- Timezone: `WEuropeStandardTime` (UTC+01:00, Amsterdam)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000018, Netherlands |
| `user_locations.json` | Migrated from HA debug JSON (schemas_1 format); PII replaced |
| `status_6390479.json` | From original report |
| `schedules.py.txt` | Schedule data from original report (informational) |

## Notes

- Migrated from `schemas_1/evohome_017/` (had `locationId` and `gatewayId` but missing
  `mac`/`crc`/`isWiFi` and `useDaylightSaveSwitching`; added during migration).
- Zone 8222004 has an empty name in the original data.
