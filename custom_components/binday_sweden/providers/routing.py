from __future__ import annotations

from homeassistant.core import HomeAssistant

from .nsr import NsrProvider


_NSR_KOMMUNER = {
    # Common municipality names (without "kommun").
    "Bjuv",
    "Båstad",
    "Helsingborg",
    "Höganäs",
    "Åstorp",
    "Ängelholm",
}

# TODO: Add more provider implementations under `custom_components/binday_sweden/providers/`
# and extend kommun -> provider routing here. Keep routing data-driven and avoid
# hardcoding any fixed set/number of bin types; derive types dynamically from provider data.


def _kommun_variants(kommun: str) -> set[str]:
    """Return a small set of matching variants for a kommun name."""
    kommun = kommun.strip()
    variants = {kommun}
    if kommun.endswith("s") and len(kommun) > 1:
        variants.add(kommun[:-1])
    return variants


def get_provider_for_kommun(
    hass: HomeAssistant,
    kommun: str,
    *,
    use_demo_data: bool = False,
):
    """Return a Provider instance for a kommun, or None if unsupported."""
    if _kommun_variants(kommun) & _NSR_KOMMUNER:
        return NsrProvider(hass, use_demo_data=use_demo_data)
    return None
