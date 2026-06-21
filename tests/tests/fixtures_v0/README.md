# fixtures_v0/

Test fixtures for the `evohomeasync` package (Resideo v0 API).

## File format

Each subdirectory contains two files:

| File | Description |
|------|-------------|
| `user_info.json` | `/userAccount` response — wrapped in `{"userInfo": {...}}` |
| `user_locs.json` | `/locations?userId=...` response — array of location objects |

Keys are camelCase. Notable v0-specific field names: `userID` (not `userId`),
`zipcode` (not `postcode`), `userLanguage` (not `language`).

`user_info.json` does **not** include a `sessionId` field — it is an ephemeral auth
token that should never be hardcoded in test fixtures.

## Subdirectories

| Directory | Location ID | Country | Source |
|-----------|-------------|---------|--------|
| `default/` | 2738909 | GB | Synthesised — real IDs, placeholder personal fields |
| `minimal/` | 2738909 | GB | Synthesised — minimal v0 response, same location as default |
| `hass_139906/` | 2727366 | NL | HA core issue [#139906](https://github.com/home-assistant/core/issues/139906) |
| `hass_139945/` | 2080024 | NL | HA core issue [#139945](https://github.com/home-assistant/core/issues/139945) |
| `hass_141882/` | 7680795 | AU | HA core issue [#141882](https://github.com/home-assistant/core/issues/141882) |

## PII policy

All personally identifiable data has been removed or replaced:
- Names → `"John"` / `"Smith"`
- Usernames → `"user_{userId}@gmail.com"`
- Addresses → `"1 Main Street"` / city from timezone
- Real user IDs are kept where they exist in the original report

## Cross-API coverage

Systems that appear in both `fixtures_v0/` and `fixtures_v2/`:

| System | v0 dir | v2 dir |
|--------|--------|--------|
| 2738909 | `default/`, `minimal/` | `default/`, `hass_000000/`, `hass_000001/`, `hass_000002/`, `system_002/` |
| 2727366 | `hass_139906/` | `fixtures_v2/hass_139906/` |
| 2080024 | `hass_139945/` | `fixtures_v2/hass_139945/` |
| 7680795 | `hass_141882/` | `fixtures_v2/hass_141882/` |
