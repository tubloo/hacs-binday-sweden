from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CREATE_PER_TYPE_SENSORS,
    CONF_MATCH_ID,
    CONF_MATCH_LABEL,
    CONF_PER_TYPE_SENSOR_CAP,
    CONF_UPCOMING_LIMIT,
    CONF_LAN,
    DEFAULT_CREATE_PER_TYPE_SENSORS,
    DEFAULT_PER_TYPE_SENSOR_CAP,
    DEFAULT_UPCOMING_LIMIT,
    DOMAIN,
)
from .coordinator import BinDayCoordinator
from .providers import ProviderEvent
from .util import slugify


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BinDayCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        BinDayNextCollectionDateSensor(coordinator, entry),
        BinDayNextCollectionTypeSensor(coordinator, entry),
        BinDayDaysUntilNextCollectionSensor(coordinator, entry),
    ]

    create_per_type = bool(
        entry.options.get(CONF_CREATE_PER_TYPE_SENSORS, DEFAULT_CREATE_PER_TYPE_SENSORS)
    )
    if create_per_type and coordinator.data:
        cap = int(entry.options.get(CONF_PER_TYPE_SENSOR_CAP, DEFAULT_PER_TYPE_SENSOR_CAP))
        per_type = _next_dates_by_type(coordinator.data.events)
        for type_formatted, next_date in list(per_type.items())[: max(cap, 0)]:
            entities.append(BinDayPerTypeNextDateSensor(coordinator, entry, type_formatted, next_date))

    async_add_entities(entities)


def _today_local() -> date:
    return dt_util.now().date()


def _next_event(events: list[ProviderEvent]) -> ProviderEvent | None:
    today = _today_local()
    for ev in events:
        if ev.date >= today:
            return ev
    return None


def _events_on_date(events: list[ProviderEvent], target: date) -> list[ProviderEvent]:
    return [ev for ev in events if ev.date == target]


def _display_type(ev: ProviderEvent) -> str | None:
    type_raw = (ev.type_raw or "").strip()
    type_formatted = (ev.type_formatted or "").strip()

    # Smart display:
    # - If provider indicates a container (e.g. "KÄRL 1"), show raw + formatted composition if present.
    # - Otherwise prefer formatted (often a nicer label), falling back to raw.
    if ev.container_number is not None or type_raw.upper().startswith("KÄRL"):
        if type_formatted and type_formatted != type_raw:
            return f"{type_raw} ({type_formatted})".strip()
        return type_raw or type_formatted or None

    return type_formatted or type_raw or None


def _next_dates_by_type(events: list[ProviderEvent]) -> dict[str, date]:
    today = _today_local()
    out: dict[str, date] = {}
    for ev in events:
        if ev.date < today:
            continue
        key = ev.type_formatted or ev.type_raw or "Unknown"
        if key not in out or ev.date < out[key]:
            out[key] = ev.date
    return dict(sorted(out.items(), key=lambda kv: (kv[1], kv[0].lower())))


class _BinDayBaseSensor(CoordinatorEntity[BinDayCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BinDayCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
        }

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data:
            return {
                "provider": None,
                "lan": self._entry.data.get(CONF_LAN),
                "match_id": self._entry.data.get(CONF_MATCH_ID),
                "match_label": self._entry.data.get(CONF_MATCH_LABEL),
            }

        limit = int(self._entry.options.get(CONF_UPCOMING_LIMIT, DEFAULT_UPCOMING_LIMIT))
        upcoming = []
        for ev in data.events[: max(limit, 0)]:
            upcoming.append(
                {
                    "date": ev.date.isoformat(),
                    "type_raw": ev.type_raw,
                    "type_formatted": ev.type_formatted,
                    "container_number": ev.container_number,
                }
            )

        next_ev = _next_event(data.events)
        next_date = next_ev.date if next_ev else None
        next_day_events = _events_on_date(data.events, next_date) if next_date else []
        next_day_types_display: list[str] = []
        seen: set[str] = set()
        for ev in next_day_events:
            display = _display_type(ev)
            if not display:
                continue
            if display in seen:
                continue
            seen.add(display)
            next_day_types_display.append(display)

        return {
            "provider": data.provider_name,
            "provider_id": data.provider_id,
            "lan": self._entry.data.get(CONF_LAN),
            "kommun": data.kommun,
            "address_query": data.address_query,
            "match_id": data.match_id,
            "match_label": data.match_label,
            "next_container_number": next_ev.container_number if next_ev else None,
            "next_type_raw": next_ev.type_raw if next_ev else None,
            "next_type_formatted": next_ev.type_formatted if next_ev else None,
            "next_day_date": next_date.isoformat() if next_date else None,
            "next_day_types_display": next_day_types_display,
            "next_day_events": [
                {
                    "date": ev.date.isoformat(),
                    "type_raw": ev.type_raw,
                    "type_formatted": ev.type_formatted,
                    "container_number": ev.container_number,
                }
                for ev in next_day_events
            ],
            "upcoming": upcoming,
        }


class BinDayNextCollectionDateSensor(_BinDayBaseSensor):
    entity_description = SensorEntityDescription(
        key="next_collection_date",
        name="Next collection date",
        device_class=SensorDeviceClass.DATE,
    )

    def __init__(self, coordinator: BinDayCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_collection_date"
        self._attr_suggested_object_id = "binday_sweden_next_collection_date"

    @property
    def native_value(self) -> date | None:
        data = self.coordinator.data
        if not data:
            return None
        ev = _next_event(data.events)
        return ev.date if ev else None


class BinDayNextCollectionTypeSensor(_BinDayBaseSensor):
    entity_description = SensorEntityDescription(
        key="next_collection_type",
        name="Next collection type",
    )

    def __init__(self, coordinator: BinDayCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_collection_type"
        self._attr_suggested_object_id = "binday_sweden_next_collection_type"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        ev = _next_event(data.events)
        if ev is None:
            return None

        day_events = _events_on_date(data.events, ev.date)
        displays: list[str] = []
        seen: set[str] = set()
        for item in day_events:
            d = _display_type(item)
            if not d:
                continue
            if d in seen:
                continue
            seen.add(d)
            displays.append(d)

        if not displays:
            return None
        if len(displays) == 1:
            return displays[0]
        return " + ".join(displays)


class BinDayDaysUntilNextCollectionSensor(_BinDayBaseSensor):
    entity_description = SensorEntityDescription(
        key="days_until_next_collection",
        name="Days until next collection",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
    )

    def __init__(self, coordinator: BinDayCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_days_until_next_collection"
        self._attr_suggested_object_id = "binday_sweden_days_until_next_collection"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if not data:
            return None
        ev = _next_event(data.events)
        if ev is None:
            return None
        return (ev.date - _today_local()).days


class BinDayPerTypeNextDateSensor(_BinDayBaseSensor):
    _attr_icon = "mdi:trash-can"

    def __init__(
        self,
        coordinator: BinDayCoordinator,
        entry: ConfigEntry,
        type_formatted: str,
        next_date: date,
    ) -> None:
        super().__init__(coordinator, entry)
        self._type_formatted = type_formatted
        self._type_slug = slugify(type_formatted)
        self._initial_next_date = next_date

        self.entity_description = SensorEntityDescription(
            key=f"type_{self._type_slug}_next_date",
            name=f"{type_formatted} next date",
            device_class=SensorDeviceClass.DATE,
        )
        self._attr_unique_id = f"{entry.entry_id}_type_{self._type_slug}_next_date"

    @property
    def native_value(self) -> date | None:
        data = self.coordinator.data
        if not data:
            return None
        per_type = _next_dates_by_type(data.events)
        return per_type.get(self._type_formatted, self._initial_next_date)
