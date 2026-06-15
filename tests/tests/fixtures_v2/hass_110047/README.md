# fixtures_v2/hass_110047

Source: [Home Assistant core issue #110047](https://github.com/home-assistant/core/issues/110047)

## System

- Location: 6992390 (Spain)
- Gateway: 6613390
- TCS: 8942494
- 9 zones: Comedor (8942485), Cocina (8942486), Hab nosotros (8942487),
  Hab Mapi (8942488), Hab visitas (8942489), Bano (8942490), Apagar (8942491),
  Secador toalla (8942492), Sala (8942493)
- No DHW
- Timezone: `RomanceStandardTime` (UTC+01:00) — zone names reveal Spain, not Belgium

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000005, Spain |
| `user_locations.json` | Migrated from `schemas_0/hass_110047/config.json`; PII replaced |
| `status_6992390.json` | From `schemas_0/hass_110047/status.json` |
| `schedules.py.txt` | Schedule data from original report (informational) |

## Notes

- `RomanceStandardTime` covers Belgium, France, Spain, and others. Zone names (Spanish)
  confirm Spain; city/postcode overridden to Madrid/28001 and language to `esES`.
- Supersedes the former `system_005/` synthesised fixture which covered the same location.
- Migrated from `schemas_0` format.
