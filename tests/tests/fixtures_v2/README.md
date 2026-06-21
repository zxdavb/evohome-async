# fixtures_v2/

Test fixtures for the `evohomeasync2` package (Resideo v2 API).

## File format (gen-3, current)

Each subdirectory contains:

| File | Description |
|------|-------------|
| `user_account.json` | `/userAccount` response |
| `user_locations.json` | `/location/installationInfo?...` response — array of location objects |
| `status_{locId}.json` | `/location/{locId}/status?...` response |
| `schedule_zone.json` | Generic zone schedule (fallback) |
| `schedule_dhw.json` | Generic DHW schedule (fallback) |
| `schedule_{zoneId}.json` | Per-zone schedule where available |

Keys are camelCase/PascalCase as returned by the vendor API.

`locationId` appears **only** inside `locationInfo`, not at the top level of the location object.

`gatewayInfo` always includes `mac`, `crc`, and `isWiFi` (synthesised to `"000000000000"`,
`"0000"`, `false` when not in original source data).

`locationInfo` always includes `locationType: "Residential"` and `useDaylightSaveSwitching`.

## Subdirectories

| Directory | Location ID | Timezone | Source |
|-----------|-------------|----------|--------|
| `default/` | 2738909 | GMT | Synthesised default system (UK, 9 zones + DHW) |
| `system_002/` | 2738909 | GMT | Same system as default, different test scenario |
| `system_004/` | 2664492 | CET | Synthesised multi-status system (Czech Republic) |
| `system_006/` | 0001 | Romance | Synthesised minimal system (Belgium) |
| `evohome_017/` | 6390479 | WEurope | evohome-async issue [#17](https://github.com/zxdavb/evohome-async/issues/17) |
| `hass_000000/` | 2738909 | GMT | HA core issue [#000000](https://github.com/home-assistant/core/issues/000000) |
| `hass_000001/` | 2738909 | GMT | HA core issue [#000001](https://github.com/home-assistant/core/issues/000001) |
| `hass_000002/` | 2738909 | GMT | HA core issue [#000002](https://github.com/home-assistant/core/issues/000002) |
| `hass_030945/` | 1234567 | GMT | HA core issue [#30945](https://github.com/home-assistant/core/issues/30945) |
| `hass_032585/` | 111111 | GMT | HA core issue [#32585](https://github.com/home-assistant/core/issues/32585) (VisionProWifi) |
| `hass_067822/` | 3184115 | GMT | HA core issue [#67822](https://github.com/home-assistant/core/issues/67822) (12 zones + DHW) |
| `hass_094805/` | 1111111 | AUSEastern | HA core issue [#94805](https://github.com/home-assistant/core/issues/94805) (FocusProWifi) |
| `hass_099625/` | 4000014 | FLE | HA core issue [#99625](https://github.com/home-assistant/core/issues/99625) (config only) |
| `hass_101355/` | 1111111 | GMT | HA core issue [#101355](https://github.com/home-assistant/core/issues/101355) |
| `hass_102505/` | 678433 | GMT | HA core issue [#102505](https://github.com/home-assistant/core/issues/102505) (12 zones) |
| `hass_102815/` | 4000016 | Romance | HA core issue [#102815](https://github.com/home-assistant/core/issues/102815) (config only) |
| `hass_110047/` | 6992390 | Romance | HA core issue [#110047](https://github.com/home-assistant/core/issues/110047) (Spain, 9 zones) |
| `hass_110065/` | 4655156 | Romance | HA core issue [#110065](https://github.com/home-assistant/core/issues/110065) (Belgium, Dutch zones) |
| `hass_112884/` | 2049339 | WEurope | HA core issue [#112884](https://github.com/home-assistant/core/issues/112884) (9 Dutch zones) |
| `hass_118169/` | 2730000 | AUSEastern | HA core issue [#118169](https://github.com/home-assistant/core/issues/118169) (FocusProWifi) |
| `hass_139906/` | 2727366 | WEurope | HA core issue [#139906](https://github.com/home-assistant/core/issues/139906) |
| `hass_139945/` | 2080024 | WEurope | HA core issue [#139945](https://github.com/home-assistant/core/issues/139945) |
| `hass_140194/` | 3886561 | Argentina | HA core issue [#140194](https://github.com/home-assistant/core/issues/140194) |
| `hass_141882/` | 7680795 | AUSEastern | HA core issue [#141882](https://github.com/home-assistant/core/issues/141882) |
| `hass_157546/` | 7647411 | GMT | HA core issue [#157546](https://github.com/home-assistant/core/issues/157546) |

Config-only dirs (no status file, xfail in tests): `hass_099625/`, `hass_102815/`

## PII policy

- Names → `"John"` / `"Smith"`; usernames → `"user_{userId}@gmail.com"`
- Addresses → `"1 Main Street"` / city matching the system's timezone/country
- MAC addresses → `"000000000000"`; CRC → `"0000"`
- Real location/gateway/system/zone IDs are kept from the original reports
- Synthesised IDs use the range 4000001+ to avoid collisions with real IDs
