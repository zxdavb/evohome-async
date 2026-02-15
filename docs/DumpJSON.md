# Dump Command JSON Structure

The `dump` command outputs a JSON structure containing the complete configuration and current status of a location. This document describes the structure of this JSON output.

## Overview

The dump output contains two main sections:
- `config`: Static configuration data about the location
- `status`: Current state information including zone temperatures, setpoints, and system mode

## Top-Level Structure

```json
{
    "config": { ... },
    "status": { ... }
}
```

## Config Section

The `config` section contains location metadata and settings:

```json
{
    "config": {
        "location_id": "3800177",
        "name": "Home2",
        "street_address": "********",
        "city": "********",
        "country": "Netherlands",
        "postcode": "********",
        "location_type": "Residential",
        "use_daylight_save_switching": true,
        "time_zone": {
            "time_zone_id": "WEuropeStandardTime",
            "display_name": "(UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna",
            "offset_minutes": 60,
            "current_offset_minutes": 60,
            "supports_daylight_saving": true
        },
        "location_owner": {
            "user_id": "3194795",
            "username": "******@obfuscated.com",
            "firstname": "FirstName",
            "lastname": "********"
        }
    }
}
```

### Config Fields

| Field | Type | Description |
|-------|------|-------------|
| `location_id` | string | Unique identifier for the location |
| `name` | string | Location name |
| `street_address` | string | Street address (may be obfuscated) |
| `city` | string | City name (may be obfuscated) |
| `country` | string | Country name |
| `postcode` | string | Postal code (may be obfuscated) |
| `location_type` | string | Type of location (e.g., "Residential") |
| `use_daylight_save_switching` | boolean | Whether daylight saving time is used |
| `time_zone` | object | Time zone information (see below) |
| `location_owner` | object | Owner information (see below) |

### Time Zone Object

| Field | Type | Description |
|-------|------|-------------|
| `time_zone_id` | string | Time zone identifier |
| `display_name` | string | Human-readable time zone name |
| `offset_minutes` | number | UTC offset in minutes |
| `current_offset_minutes` | number | Current UTC offset (accounts for DST) |
| `supports_daylight_saving` | boolean | Whether time zone supports DST |

### Location Owner Object

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | Unique user identifier |
| `username` | string | User email/username (may be obfuscated) |
| `firstname` | string | Owner's first name (may be obfuscated) |
| `lastname` | string | Owner's last name (may be obfuscated) |

## Status Section

The `status` section contains current state information:

```json
{
    "status": {
        "location_id": "3800177",
        "gateways": [ ... ]
    }
}
```

### Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `location_id` | string | Unique identifier for the location |
| `gateways` | array | Array of gateway objects (see below) |

## Gateway Structure

Each gateway contains temperature control systems:

```json
{
    "gateway_id": "3795953",
    "temperature_control_systems": [ ... ],
    "active_faults": [ ... ]
}
```

### Gateway Fields

| Field | Type | Description |
|-------|------|-------------|
| `gateway_id` | string | Unique identifier for the gateway |
| `temperature_control_systems` | array | Array of TCS objects (see below) |
| `active_faults` | array | Array of active fault objects (see below) |

## Temperature Control System (TCS) Structure

Each TCS contains zones and system mode information:

```json
{
    "system_id": "5262687",
    "zones": [ ... ],
    "active_faults": [ ... ],
    "system_mode_status": {
        "mode": "HeatingOff",
        "is_permanent": true
    }
}
```

### TCS Fields

| Field | Type | Description |
|-------|------|-------------|
| `system_id` | string | Unique identifier for the TCS |
| `zones` | array | Array of zone objects (see below) |
| `active_faults` | array | Array of active fault objects (see below) |
| `system_mode_status` | object | Current system mode (see below) |

### System Mode Status

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Current system mode (e.g., "HeatingOff", "Auto", "Away", "DayOff") |
| `is_permanent` | boolean | Whether the mode is permanent or temporary |

## Zone Structure

Each zone contains temperature, setpoint, and fault information:

```json
{
    "zone_id": "5262675",
    "temperature_status": {
        "temperature": 16.5,
        "is_available": true
    },
    "active_faults": [ ... ],
    "setpoint_status": {
        "target_heat_temperature": 5.0,
        "setpoint_mode": "PermanentOverride"
    },
    "name": "Livingroom"
}
```

### Zone Fields

| Field | Type | Description |
|-------|------|-------------|
| `zone_id` | string | Unique identifier for the zone |
| `temperature_status` | object | Current temperature information (see below) |
| `active_faults` | array | Array of active fault objects (see below) |
| `setpoint_status` | object | Current setpoint information (see below) |
| `name` | string | Zone name |

### Temperature Status

| Field | Type | Description |
|-------|------|-------------|
| `temperature` | number | Current temperature in Celsius (only present if `is_available` is true) |
| `is_available` | boolean | Whether temperature reading is available |

**Note**: If `is_available` is `false`, the `temperature` field will be absent from the object.

### Setpoint Status

| Field | Type | Description |
|-------|------|-------------|
| `target_heat_temperature` | number | Target heating temperature in Celsius |
| `setpoint_mode` | string | Current setpoint mode (see below) |
| `until` | string | ISO 8601 timestamp for temporary overrides (optional) |

### Setpoint Modes

Common setpoint modes include:
- `"FollowSchedule"`: Zone follows its schedule
- `"TemporaryOverride"`: Temporary temperature override
- `"PermanentOverride"`: Permanent temperature override

## Active Faults

Faults are represented as objects with the following structure:

```json
{
    "fault_type": "TempZoneActuatorCommunicationLost",
    "since": "2025-11-14T02:04:14"
}
```

### Fault Fields

| Field | Type | Description |
|-------|------|-------------|
| `fault_type` | string | Type of fault (see below) |
| `since` | string | ISO 8601 timestamp when the fault started |

### Common Fault Types

- `"TempZoneActuatorCommunicationLost"`: Actuator communication lost
- `"TempZoneSensorCommunicationLost"`: Sensor communication lost
- `"TempZoneSensorLowBattery"`: Sensor battery low
- `"TempZoneActuatorLowBattery"`: Actuator battery low

## Complete Example

Here is a complete example showing the structure with multiple zones:

```json
{
    "config": {
        "location_id": "3800177",
        "name": "Home2",
        "country": "Netherlands",
        "location_type": "Residential",
        "use_daylight_save_switching": true,
        "time_zone": {
            "time_zone_id": "WEuropeStandardTime",
            "display_name": "(UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna",
            "offset_minutes": 60,
            "current_offset_minutes": 60,
            "supports_daylight_saving": true
        },
        "location_owner": {
            "user_id": "3194795",
            "username": "******@obfuscated.com"
        }
    },
    "status": {
        "location_id": "3800177",
        "gateways": [
            {
                "gateway_id": "3795953",
                "temperature_control_systems": [
                    {
                        "system_id": "5262687",
                        "zones": [
                            {
                                "zone_id": "5262675",
                                "temperature_status": {
                                    "temperature": 16.5,
                                    "is_available": true
                                },
                                "active_faults": [
                                    {
                                        "fault_type": "TempZoneActuatorCommunicationLost",
                                        "since": "2025-11-14T02:04:14"
                                    }
                                ],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Livingroom"
                            },
                            {
                                "zone_id": "5262676",
                                "temperature_status": {
                                    "temperature": 17.5,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Hall upstairs"
                            },
                            {
                                "zone_id": "5262677",
                                "temperature_status": {
                                    "temperature": 14.5,
                                    "is_available": true
                                },
                                "active_faults": [
                                    {
                                        "fault_type": "TempZoneSensorLowBattery",
                                        "since": "2025-10-24T08:27:40"
                                    },
                                    {
                                        "fault_type": "TempZoneActuatorLowBattery",
                                        "since": "2025-10-24T08:27:40"
                                    }
                                ],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 1"
                            },
                            {
                                "zone_id": "5262678",
                                "temperature_status": {
                                    "temperature": 14.0,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Kitchen"
                            },
                            {
                                "zone_id": "5262679",
                                "temperature_status": {
                                    "is_available": false
                                },
                                "active_faults": [
                                    {
                                        "fault_type": "TempZoneActuatorCommunicationLost",
                                        "since": "2025-11-18T02:04:27"
                                    },
                                    {
                                        "fault_type": "TempZoneSensorCommunicationLost",
                                        "since": "2025-11-18T02:04:27"
                                    }
                                ],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 2"
                            },
                            {
                                "zone_id": "5262680",
                                "temperature_status": {
                                    "temperature": 16.5,
                                    "is_available": true
                                },
                                "active_faults": [
                                    {
                                        "fault_type": "TempZoneSensorLowBattery",
                                        "since": "2025-02-14T15:14:18"
                                    },
                                    {
                                        "fault_type": "TempZoneActuatorLowBattery",
                                        "since": "2025-03-03T07:48:09"
                                    },
                                    {
                                        "fault_type": "TempZoneActuatorCommunicationLost",
                                        "since": "2025-11-13T17:22:41"
                                    }
                                ],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Dining"
                            },
                            {
                                "zone_id": "5262681",
                                "temperature_status": {
                                    "temperature": 15.5,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 3"
                            },
                            {
                                "zone_id": "5262682",
                                "temperature_status": {
                                    "temperature": 16.5,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 4"
                            },
                            {
                                "zone_id": "5262683",
                                "temperature_status": {
                                    "temperature": 15.5,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 5"
                            },
                            {
                                "zone_id": "5262684",
                                "temperature_status": {
                                    "temperature": 15.5,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 6"
                            },
                            {
                                "zone_id": "5262685",
                                "temperature_status": {
                                    "temperature": 14.5,
                                    "is_available": true
                                },
                                "active_faults": [],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Laundry room"
                            },
                            {
                                "zone_id": "5262686",
                                "temperature_status": {
                                    "is_available": false
                                },
                                "active_faults": [
                                    {
                                        "fault_type": "TempZoneActuatorCommunicationLost",
                                        "since": "2025-11-14T02:04:25"
                                    },
                                    {
                                        "fault_type": "TempZoneSensorCommunicationLost",
                                        "since": "2025-11-14T02:04:25"
                                    }
                                ],
                                "setpoint_status": {
                                    "target_heat_temperature": 5.0,
                                    "setpoint_mode": "PermanentOverride"
                                },
                                "name": "Room 7"
                            }
                        ],
                        "active_faults": [],
                        "system_mode_status": {
                            "mode": "HeatingOff",
                            "is_permanent": true
                        }
                    }
                ],
                "active_faults": []
            }
        ]
    }
}
```

## Notes

- **Temperature Availability**: When `temperature_status.is_available` is `false`, the `temperature` field is not present in the object. This typically indicates a communication issue with the zone sensor.

- **Fault Arrays**: The `active_faults` arrays can be empty (`[]`) if there are no active faults. Multiple faults can be present for a single zone.

- **Setpoint Modes**: The `setpoint_mode` field indicates how the zone's target temperature is being controlled. Temporary overrides may include an `until` timestamp.

- **System Mode**: The `system_mode_status.mode` applies to the entire temperature control system and affects all zones.

- **Obfuscated Data**: Some fields (like addresses and usernames) may be obfuscated in the output for privacy reasons.

