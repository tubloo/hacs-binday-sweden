from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class ProviderAddressMatch:
    id: str
    label: str
    raw: dict


@dataclass(frozen=True)
class ProviderEvent:
    date: date
    type_raw: str
    type_formatted: str
    container_number: str | None = None


@dataclass(frozen=True)
class ProviderData:
    provider_id: str
    provider_name: str
    kommun: str
    address_query: str
    match_id: str
    match_label: str
    events: list[ProviderEvent]


class Provider(Protocol):
    provider_id: str
    provider_name: str

    async def async_search(self, query: str) -> list[ProviderAddressMatch]:
        """Search for addresses/properties by free text."""

    async def async_fetch(self, *, kommun: str, address_query: str, match_id: str) -> ProviderData:
        """Fetch and return schedule data for a selected match."""
