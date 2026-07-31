"""Schema for the vendor's TCC v2 API.

The API is undocumented, so the TypedDicts (Tcc*T) defined across the submodules of this
package (account.py, config.py, status.py, state.py, schedule.py) are the best known
description of the vendor's schema and are the source of truth for static typing.

JSON key names use camelCase throughout; the OAuth token endpoint is an accepted
exception as it natively returns snake_case.

JSON value StrEnums (Tcc*) use PascalCase, except for TccEntityType, which is
camelCase, and is used for URL construction.

The voluptuous schemas (TCC_*) are derived from those TypedDicts and serve a different
purpose: runtime validation and coercion of the data returned by the API endpoints.

Installation (of a user Account)
└── 0-many Locations
    └── 0-1 Gateway (although schema is 0-many)
        └── 0-1 Controller (although schema is 0-many)
            ├── 1-many Zones (max 16, although schema is 0-many)
            └── 0-1 DHW
"""
