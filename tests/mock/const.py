MOCK_AUTH_RESPONSE = {  # can use this for all
    "access_token": "-- REDACTED --",
    "token_type": "bearer",
    "expires_in": 1800,
    "refresh_token": "-- REDACTED --",
}


MOCK_FULL_CONFIG = [  # of a specific user account
    {
        "locationInfo": {
            "locationId": "2738909",
            "name": "My Home",
            "streetAddress": "1 Main Street",
            "city": "London",
            "country": "UnitedKingdom",
            "postcode": "E1 1AA",
            "locationType": "Residential",
            "useDaylightSaveSwitching": True,
            "timeZone": {
                "timeZoneId": "GMTStandardTime",
                "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
                "offsetMinutes": 0,
                "currentOffsetMinutes": 60,
                "supportsDaylightSaving": True,
            },
            "locationOwner": {
                "userId": "2263181",
                "username": "john.smith@gmail.com",
                "firstname": "John",
                "lastname": "Smith",
            },
        },
        "gateways": [
            {
                "gatewayInfo": {
                    "gatewayId": "2499896",
                    "mac": "00D02DEE1234",
                    "crc": "9999",
                    "isWiFi": False,
                },
                "temperatureControlSystems": [
                    {
                        "systemId": "3432522",
                        "modelType": "EvoTouch",
                        "zones": [
                            {
                                "zoneId": "3432521",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Dead Zone",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3432576",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Main Room",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3432577",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Front Room",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3432578",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Kitchen",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3432579",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Bathroom Dn",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3432580",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Main Bedroom",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3449703",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Spare Room",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3449740",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Bathroom Up",
                                "zoneType": "RadiatorZone",
                            },
                            {
                                "zoneId": "3450733",
                                "modelType": "HeatingZone",
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        "PermanentOverride",
                                        "FollowSchedule",
                                        "TemporaryOverride",
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Kids Room",
                                "zoneType": "RadiatorZone",
                            },
                        ],
                        "allowedSystemModes": [
                            {
                                "systemMode": "Auto",
                                "canBePermanent": True,
                                "canBeTemporary": False,
                            },
                            {
                                "systemMode": "AutoWithEco",
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "1.00:00:00",
                                "timingResolution": "01:00:00",
                                "timingMode": "Duration",
                            },
                            {
                                "systemMode": "AutoWithReset",
                                "canBePermanent": True,
                                "canBeTemporary": False,
                            },
                            {
                                "systemMode": "Away",
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "99.00:00:00",
                                "timingResolution": "1.00:00:00",
                                "timingMode": "Period",
                            },
                            {
                                "systemMode": "DayOff",
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "99.00:00:00",
                                "timingResolution": "1.00:00:00",
                                "timingMode": "Period",
                            },
                            {
                                "systemMode": "HeatingOff",
                                "canBePermanent": True,
                                "canBeTemporary": False,
                            },
                            {
                                "systemMode": "Custom",
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "99.00:00:00",
                                "timingResolution": "1.00:00:00",
                                "timingMode": "Period",
                            },
                        ],
                    }
                ],
            }
        ],
    }
]  # NOTE: no activeFaults as is config


MOCK_LOCN_STATUS = {  # of a specific location
    "locationId": "2738909",
    "gateways": [
        {
            "gatewayId": "2499896",
            "temperatureControlSystems": [
                {
                    "systemId": "3432522",
                    "zones": [
                        {
                            "zoneId": "3432521",
                            "temperatureStatus": {"isAvailable": False},
                            "activeFaults": [
                                {
                                    "faultType": "TempZoneSensorCommunicationLost",
                                    "since": "2023-10-09T01:45:00",
                                }
                            ],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "PermanentOverride",
                            },
                            "name": "Dead Zone",
                        },
                        {
                            "zoneId": "3432576",
                            "temperatureStatus": {
                                "temperature": 19.5,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "FollowSchedule",
                            },
                            "name": "Main Room",
                        },
                        {
                            "zoneId": "3432577",
                            "temperatureStatus": {
                                "temperature": 18.0,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "PermanentOverride",
                            },
                            "name": "Front Room",
                        },
                        {
                            "zoneId": "3432578",
                            "temperatureStatus": {"isAvailable": False},
                            "activeFaults": [
                                {
                                    "faultType": "TempZoneSensorLowBattery",
                                    "since": "2023-06-03T21:05:32",
                                },
                                {
                                    "faultType": "TempZoneSensorCommunicationLost",
                                    "since": "2023-09-02T12:34:46",
                                },
                            ],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "FollowSchedule",
                            },
                            "name": "Kitchen",
                        },
                        {
                            "zoneId": "3432579",
                            "temperatureStatus": {"isAvailable": False},
                            "activeFaults": [
                                {
                                    "faultType": "TempZoneSensorCommunicationLost",
                                    "since": "2023-10-09T01:45:04",
                                }
                            ],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "FollowSchedule",
                            },
                            "name": "Bathroom Dn",
                        },
                        {
                            "zoneId": "3432580",
                            "temperatureStatus": {
                                "temperature": 18.0,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "PermanentOverride",
                            },
                            "name": "Main Bedroom",
                        },
                        {
                            "zoneId": "3449703",
                            "temperatureStatus": {
                                "temperature": 18.0,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "PermanentOverride",
                            },
                            "name": "Spare Room",
                        },
                        {
                            "zoneId": "3449740",
                            "temperatureStatus": {
                                "temperature": 18.0,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "FollowSchedule",
                            },
                            "name": "Bathroom Up",
                        },
                        {
                            "zoneId": "3450733",
                            "temperatureStatus": {
                                "temperature": 18.5,
                                "isAvailable": True,
                            },
                            "activeFaults": [
                                {
                                    "faultType": "TempZoneActuatorCommunicationLost",
                                    "since": "2023-09-18T22:54:17",
                                }
                            ],
                            "setpointStatus": {
                                "targetHeatTemperature": 5.0,
                                "setpointMode": "PermanentOverride",
                            },
                            "name": "Kids Room",
                        },
                    ],
                    "activeFaults": [],
                    "systemModeStatus": {"mode": "HeatingOff", "isPermanent": True},
                }
            ],
            "activeFaults": [],
        }
    ],
}


MOCK_SCHEDULE_ZONE = {  # of any zone (no zoneId)
    "dailySchedules": [
        {
            "dayOfWeek": "Monday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0000, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": "Tuesday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0000, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": "Wednesday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0000, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": "Thursday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0000, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": "Friday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0000, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": "Saturday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "07:30:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "10:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": "Sunday",
            "switchpoints": [
                {"heatSetpoint": 19.0000, "timeOfDay": "07:30:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "10:00:00"},
                {"heatSetpoint": 18.5000, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9000, "timeOfDay": "21:30:00"},
            ],
        },
    ]
}


MOCK_SCHEDULE_DHW = {}  # TODO
