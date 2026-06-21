# fixtures_v2/hass_140194

Source: [Home Assistant core issue #140194](https://github.com/home-assistant/core/issues/140194)

## System

- Location: 3886561 (Buenos Aires, Argentina)
- Gateway: 3387815
- TCS: 5522075
- 8 zones: Comedor (5522074), Living (5522705), Escritorio (5522706),
  Dorm. Atras (5522707), Dorm. Frente (5522708), Hall PA (5522709),
  Dorm. Princ. (5522710), Baño Princ. (5522711)
- Timezone: `ArgentinaStandardTime` (UTC-03:00, no DST)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised (real country/language from log) |
| `user_locations.json` | Converted from HA debug log (camelCase, vendor structure) |
| `status_3886561.json` | Converted from HA debug log (Away mode, real temperatures) |
| `schedule_zone.json` | Conftest generic schedule (Comedor schedule, from log) |
| `schedule_5522074.json` | Comedor — from HA debug log |
| `schedule_5522705.json` | Living — from HA debug log |
| `schedule_5522706.json` | Escritorio — from HA debug log |
| `schedule_5522707.json` | Dorm. Atras — from HA debug log |
| `schedule_5522708.json` | Dorm. Frente — from HA debug log |
| `schedule_5522709.json` | Hall PA — from HA debug log |
| `schedule_5522710.json` | Dorm. Princ. — from HA debug log |
| `schedule_5522711.json` | Baño Princ. — from HA debug log |

## Notes

- `user_account.json` is synthesised: `userId`, `username`, and `streetAddress` are
  placeholders; `country: "Argentina"` and `language: "esAR"` are inferred from timezone.
- Zone name encoding: zone 5522711 appears as `Ba?o Princ.` in the raw log (mojibake);
  corrected to `Baño Princ.` in all files here.
- The original `config.json` (snake_case, wrong TCS structure) has been deleted and replaced
  by `user_locations.json` in vendor camelCase format.
