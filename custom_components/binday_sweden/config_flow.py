from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ADDRESS_QUERY,
    CONF_CREATE_PER_TYPE_SENSORS,
    CONF_KOMMUN,
    CONF_LAN,
    CONF_MATCH_ID,
    CONF_MATCH_LABEL,
    CONF_PER_TYPE_SENSOR_CAP,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_UPCOMING_LIMIT,
    CONF_USE_DEMO_DATA,
    DEFAULT_CREATE_PER_TYPE_SENSORS,
    DEFAULT_PER_TYPE_SENSOR_CAP,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_UPCOMING_LIMIT,
    DOMAIN,
)
from .providers import ProviderAddressMatch, get_provider_for_kommun

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _KommunOption:
    value: str
    label: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


async def _async_load_json(hass: HomeAssistant, path: Path):
    text = await hass.async_add_executor_job(_read_text, path)
    return json.loads(text)


class BinDaySwedenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._lan: str | None = None
        self._kommun: str | None = None
        self._address_query: str | None = None
        self._scan_interval_hours: float | None = None
        self._matches: list[ProviderAddressMatch] = []
        self._lan_options: list[_KommunOption] | None = None
        self._kommun_by_lan: dict[str, list[dict]] | None = None

    async def _async_get_lan_options(self) -> list[_KommunOption]:
        if self._lan_options is not None:
            return self._lan_options

        path = Path(__file__).resolve().parent / "data" / "lans.json"
        data = await _async_load_json(self.hass, path)
        options: list[_KommunOption] = []
        for item in data:
            value = str(item.get("id", "")).strip()
            label = str(item.get("label", value)).strip()
            if value:
                options.append(_KommunOption(value=value, label=label))
        self._lan_options = options
        return options

    async def _async_get_kommun_options_for_lan(self, lan: str) -> list[_KommunOption]:
        if self._kommun_by_lan is None:
            path = Path(__file__).resolve().parent / "data" / "kommuner_by_lan.json"
            self._kommun_by_lan = await _async_load_json(self.hass, path)

        items = (self._kommun_by_lan or {}).get(lan, []) or []
        options: list[_KommunOption] = []
        for item in items:
            value = str(item.get("id", "")).strip()
            label = str(item.get("label", value)).strip()
            if value:
                options.append(_KommunOption(value=value, label=label))
        return options

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        try:
            lan_options = await self._async_get_lan_options()
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Failed to load län list: %s", err)
            errors["base"] = "cannot_load_data"
            lan_options = []
        lan_values = [o.value for o in lan_options]

        if user_input is not None:
            lan = str(user_input[CONF_LAN]).strip()
            if lan not in lan_values:
                errors["base"] = "invalid_lan"
            else:
                self._lan = lan
                return await self.async_step_kommun()

        schema = vol.Schema(
            {
                vol.Required(CONF_LAN): SelectSelector(
                    SelectSelectorConfig(
                        options=[{"label": o.label, "value": o.value} for o in lan_options],
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_kommun(self, user_input=None):
        errors: dict[str, str] = {}
        if self._lan is None:
            return await self.async_step_user()

        try:
            kommun_options = await self._async_get_kommun_options_for_lan(self._lan)
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Failed to load kommun list for län %s: %s", self._lan, err)
            errors["base"] = "cannot_load_data"
            kommun_options = []
        kommun_values = [o.value for o in kommun_options]

        if user_input is not None:
            kommun = str(user_input[CONF_KOMMUN]).strip()
            if kommun not in kommun_values:
                errors["base"] = "invalid_kommun"
            else:
                provider = get_provider_for_kommun(self.hass, kommun)
                if provider is None:
                    errors["base"] = "unsupported_municipality"
                else:
                    self._kommun = kommun
                    return await self.async_step_address()

        schema = vol.Schema(
            {
                vol.Required(CONF_KOMMUN): SelectSelector(
                    SelectSelectorConfig(
                        options=[{"label": o.label, "value": o.value} for o in kommun_options],
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                )
            }
        )
        return self.async_show_form(step_id="kommun", data_schema=schema, errors=errors)

    async def async_step_address(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None and self._kommun is not None:
            address_query = str(user_input[CONF_ADDRESS_QUERY]).strip()
            scan_interval_hours = float(user_input.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS))

            provider = get_provider_for_kommun(self.hass, self._kommun)
            if provider is None:
                return self.async_abort(reason="unsupported_municipality")

            try:
                matches = await provider.async_search(address_query)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Provider search failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not matches:
                    errors["base"] = "no_matches"
                elif len(matches) == 1:
                    self._address_query = address_query
                    self._scan_interval_hours = scan_interval_hours
                    return await self._async_create_entry(selected=matches[0])
                else:
                    self._address_query = address_query
                    self._scan_interval_hours = scan_interval_hours
                    self._matches = matches
                    return await self.async_step_select()

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS_QUERY): TextSelector(TextSelectorConfig(type="text")),
                vol.Optional(CONF_SCAN_INTERVAL_HOURS, default=DEFAULT_SCAN_INTERVAL_HOURS): NumberSelector(
                    NumberSelectorConfig(min=1, max=168, step=1, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="address", data_schema=schema, errors=errors)

    async def async_step_select(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            match_id = str(user_input[CONF_MATCH_ID]).strip()
            selected = next((m for m in self._matches if m.id == match_id), None)
            if selected is None:
                errors["base"] = "match_not_found"
            else:
                return await self._async_create_entry(selected=selected)

        schema = vol.Schema(
            {
                vol.Required(CONF_MATCH_ID): SelectSelector(
                    SelectSelectorConfig(
                        options=[{"label": m.label, "value": m.id} for m in self._matches],
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                )
            }
        )
        return self.async_show_form(step_id="select", data_schema=schema, errors=errors)

    async def _async_create_entry(self, *, selected: ProviderAddressMatch):
        assert self._lan is not None
        assert self._kommun is not None
        assert self._address_query is not None

        # This integration is designed for a single configured household.
        # Keeping a single config entry allows stable default entity_ids.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="BinDay Sweden",
            data={
                CONF_LAN: self._lan,
                CONF_KOMMUN: self._kommun,
                CONF_ADDRESS_QUERY: self._address_query,
                CONF_MATCH_ID: selected.id,
                CONF_MATCH_LABEL: selected.label,
                CONF_SCAN_INTERVAL_HOURS: self._scan_interval_hours or DEFAULT_SCAN_INTERVAL_HOURS,
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return BinDaySwedenOptionsFlowHandler(config_entry)


class BinDaySwedenOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL_HOURS,
                    default=self.entry.options.get(
                        CONF_SCAN_INTERVAL_HOURS,
                        self.entry.data.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS),
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=168, step=1, mode=NumberSelectorMode.BOX)),
                vol.Optional(
                    CONF_UPCOMING_LIMIT,
                    default=self.entry.options.get(CONF_UPCOMING_LIMIT, DEFAULT_UPCOMING_LIMIT),
                ): NumberSelector(NumberSelectorConfig(min=1, max=50, step=1, mode=NumberSelectorMode.BOX)),
                vol.Optional(
                    CONF_CREATE_PER_TYPE_SENSORS,
                    default=self.entry.options.get(
                        CONF_CREATE_PER_TYPE_SENSORS,
                        DEFAULT_CREATE_PER_TYPE_SENSORS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_PER_TYPE_SENSOR_CAP,
                    default=self.entry.options.get(
                        CONF_PER_TYPE_SENSOR_CAP,
                        DEFAULT_PER_TYPE_SENSOR_CAP,
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1, max=50, step=1, mode=NumberSelectorMode.BOX)),
                vol.Optional(
                    CONF_USE_DEMO_DATA,
                    default=self.entry.options.get(CONF_USE_DEMO_DATA, False),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
