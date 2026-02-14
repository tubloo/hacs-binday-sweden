from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform

DOMAIN = "binday_sweden"

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_KOMMUN = "kommun"
CONF_LAN = "lan"
CONF_ADDRESS_QUERY = "address_query"
CONF_PROVIDER = "provider"
CONF_MATCH_ID = "match_id"
CONF_MATCH_LABEL = "match_label"

CONF_SCAN_INTERVAL_HOURS = "scan_interval_hours"
CONF_CREATE_PER_TYPE_SENSORS = "create_per_type_sensors"
CONF_PER_TYPE_SENSOR_CAP = "per_type_sensor_cap"
CONF_UPCOMING_LIMIT = "upcoming_limit"
CONF_USE_DEMO_DATA = "use_demo_data"

DEFAULT_LOOKAHEAD_DAYS = 90
DEFAULT_SCAN_INTERVAL_HOURS = 12

DEFAULT_UPCOMING_LIMIT = 10
DEFAULT_CREATE_PER_TYPE_SENSORS = False
DEFAULT_PER_TYPE_SENSOR_CAP = 10


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    name: str
