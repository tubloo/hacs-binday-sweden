from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ADDRESS_QUERY,
    CONF_KOMMUN,
    CONF_MATCH_ID,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_USE_DEMO_DATA,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
)
from .providers import ProviderData, get_provider_for_kommun

_LOGGER = logging.getLogger(__name__)


class BinDayCoordinator(DataUpdateCoordinator[ProviderData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}:{entry.entry_id}",
            update_interval=timedelta(
                hours=float(
                    entry.options.get(
                        CONF_SCAN_INTERVAL_HOURS,
                        entry.data.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS),
                    )
                )
            ),
        )

    async def _async_update_data(self) -> ProviderData:
        kommun = str(self.entry.data[CONF_KOMMUN]).strip()
        address_query = str(self.entry.data[CONF_ADDRESS_QUERY]).strip()
        match_id = str(self.entry.data[CONF_MATCH_ID]).strip()
        use_demo_data = bool(self.entry.options.get(CONF_USE_DEMO_DATA, False))

        provider = get_provider_for_kommun(self.hass, kommun, use_demo_data=use_demo_data)
        if provider is None:
            raise UpdateFailed("Unsupported municipality/provider")

        try:
            return await provider.async_fetch(
                kommun=kommun,
                address_query=address_query,
                match_id=match_id,
            )
        except (ClientError, TimeoutError, RuntimeError, ValueError) as err:
            raise UpdateFailed(str(err)) from err

