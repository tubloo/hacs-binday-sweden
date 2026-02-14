from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import logging
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .base import ProviderAddressMatch, ProviderData, ProviderEvent

_LOGGER = logging.getLogger(__name__)

_KARL_RE = re.compile(r"\bKÄRL\s*(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class _NsrExec:
    dates: list[str]
    type_raw: list[str]
    type_formatted: list[str]
    date_formatted: list[str]


class NsrProvider:
    provider_id = "nsr"
    provider_name = "NSR AB"

    def __init__(self, hass: HomeAssistant, *, use_demo_data: bool = False) -> None:
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._use_demo_data = use_demo_data
        self._demo_cache: dict[str, Any] | None = None

    async def async_search(self, query: str) -> list[ProviderAddressMatch]:
        payload = await self._async_request(query=query)
        matches: list[ProviderAddressMatch] = []
        for item in payload.get("fp", []) or []:
            match_id = str(item.get("id", "")).strip()
            address = str(item.get("Adress", "")).strip()
            city = str(item.get("Ort", "")).strip()
            if not match_id or not address:
                continue
            label = address if not city else f"{address}, {city}"
            matches.append(ProviderAddressMatch(id=match_id, label=label, raw=item))
        return matches

    async def async_fetch(self, *, kommun: str, address_query: str, match_id: str) -> ProviderData:
        payload = await self._async_request(query=address_query)
        matches = payload.get("fp", []) or []
        selected: dict[str, Any] | None = None
        for item in matches:
            if str(item.get("id", "")).strip() == match_id:
                selected = item
                break

        if selected is None:
            raise ValueError("Selected address/property no longer found in provider results")

        match_label = _format_label(selected)
        events = _parse_exec_events(selected.get("Exec"), limit=0)

        return ProviderData(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            kommun=kommun,
            address_query=address_query,
            match_id=match_id,
            match_label=match_label,
            events=events,
        )

    async def _async_request(self, *, query: str) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return {"fp": [], "q": query}

        # NOTE: NSR endpoint appears undocumented; be polite with update intervals + caching.
        url = "https://nsr.se/api/wastecalendar/search?" + urlencode({"query": query})

        # Developer ergonomics: allow demo fixture without hitting endpoint.
        if self._use_demo_data:
            return await self._async_load_demo_fixture()

        try:
            async with self._session.get(url, raise_for_status=False) as resp:
                if resp.status == 429:
                    raise RuntimeError("Rate limited by provider (HTTP 429)")
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"Provider error (HTTP {resp.status}): {text[:200]}")
                return await resp.json(content_type=None)
        except (ClientError, TimeoutError, json.JSONDecodeError) as err:
            raise RuntimeError(f"Failed to fetch NSR data: {err}") from err

    async def _async_load_demo_fixture(self) -> dict[str, Any]:
        if self._demo_cache is None:
            self._demo_cache = await _async_load_fixture(self._hass)
        return self._demo_cache


def _read_fixture_text() -> str:
    path = Path(__file__).resolve().parent.parent / "fixtures" / "nsr_demo.json"
    return path.read_text(encoding="utf-8")


async def _async_load_fixture(hass: HomeAssistant) -> dict[str, Any]:
    text = await hass.async_add_executor_job(_read_fixture_text)
    return json.loads(text)


def _format_label(item: dict[str, Any]) -> str:
    address = str(item.get("Adress", "")).strip()
    city = str(item.get("Ort", "")).strip()
    if address and city:
        return f"{address}, {city}"
    return address or city or "Unknown"


def _parse_exec(exec_obj: Any) -> _NsrExec:
    if not isinstance(exec_obj, dict):
        return _NsrExec(dates=[], type_raw=[], type_formatted=[], date_formatted=[])

    dates = [str(x) for x in (exec_obj.get("Datum") or [])]
    type_raw = [str(x) for x in (exec_obj.get("AvfallsTyp") or [])]
    type_formatted = [str(x) for x in (exec_obj.get("AvfallsTypFormaterat") or [])]
    date_formatted = [str(x) for x in (exec_obj.get("DatumFormaterat") or [])]

    return _NsrExec(
        dates=dates,
        type_raw=type_raw,
        type_formatted=type_formatted,
        date_formatted=date_formatted,
    )


def _parse_exec_events(exec_obj: Any, *, limit: int) -> list[ProviderEvent]:
    exec_ = _parse_exec(exec_obj)
    n = min(len(exec_.dates), len(exec_.type_raw), len(exec_.type_formatted))
    if n == 0:
        return []

    events: list[ProviderEvent] = []
    for i in range(n):
        d = _parse_date(exec_.dates[i])
        if d is None:
            continue
        type_raw = str(exec_.type_raw[i]).strip()
        m = _KARL_RE.search(type_raw)
        container_number = m.group(1) if m else None
        events.append(
            ProviderEvent(
                date=d,
                type_raw=type_raw,
                type_formatted=str(exec_.type_formatted[i]).strip(),
                container_number=container_number,
            )
        )

    events.sort(key=lambda e: e.date)
    if limit > 0:
        return events[:limit]
    return events


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        # NSR uses YYYY-MM-DD in Datum.
        return date.fromisoformat(value[:10])
    except ValueError:
        _LOGGER.debug("Failed to parse date from provider value: %s", value)
        return None
