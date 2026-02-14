# BinDay Sweden

> This project was created with the assistance of AI tooling (e.g., OpenAI Codex/ChatGPT).

A Sweden-only Home Assistant custom integration that exposes your next waste/bin collection date(s).

Waste collection is organized at the municipality (kommun) level and bin/fraction naming varies widely. This integration models collection types dynamically based on provider data (no fixed “bin_1/bin_2” assumptions).

## Privacy & Data Handling

- The integration stores your selected `län`, `kommun`, and the chosen provider match id locally in Home Assistant.
- Your address search string and selected match id are sent to the selected provider (e.g., NSR AB) to fetch your schedule.

## Disclaimer

- This is an unofficial, community project and is not affiliated with Home Assistant, municipalities, or any waste provider (e.g. NSR AB).
- Provider endpoints and data formats may change without notice. Schedules may be incomplete, delayed, or incorrect; always rely on official provider information for critical decisions.
- This integration is best-effort; always verify against official provider information if you have missed collections or special cases.

## Supported providers / municipalities

### NSR AB

Right now, only **NSR AB** is supported.

| Län | Kommun | Provider |
|---|---|---|
| Skåne län | Bjuvs (Bjuv) | NSR AB |
| Skåne län | Båstads (Båstad) | NSR AB |
| Skåne län | Helsingborgs (Helsingborg) | NSR AB |
| Skåne län | Höganäs | NSR AB |
| Skåne län | Åstorps (Åstorp) | NSR AB |
| Skåne län | Ängelholms (Ängelholm) | NSR AB |

If your municipality is not in the list, setup will show: “Your municipality is not supported yet.”

## Installation

### HACS (Custom Repository)

1. HACS → Integrations → 3 dots → **Custom repositories**
2. Add this repo as **Integration**
3. Install **BinDay Sweden**
4. Restart Home Assistant
5. Add the integration in **Settings → Devices & Services**

### Manual (advanced)

1. Copy `custom_components/binday_sweden` into your HA config:
   - `/config/custom_components/binday_sweden`
2. Restart Home Assistant
3. Add the integration in **Settings → Devices & Services**

## Configure

Settings → Devices & Services → Add Integration → **BinDay Sweden**

You will be asked for:
- `Län` (dropdown)
- `Kommun` (dropdown)
- `Address search` (free text; used against the provider’s search endpoint)
- If multiple matches are found: select the exact address/property
- Optional (Options): update interval (hours), upcoming event limit, and per-type sensors

## Features

- Län → kommun guided setup (reduces ambiguous matching)
- Address search + match selection (handles multiple results)
- Dynamic “collection types” derived from provider data (no fixed bin count)
- Multi-collection same day support (types are joined for the next pickup date)
- Optional per-type sensors (capped)

## Entities

- `sensor.<name>_next_collection_date` (date)
- `sensor.<name>_next_collection_type` (string; joins multiple types on the next date)
- `sensor.<name>_days_until_next_collection` (int)

Optional (Settings → Configure on the integration):
- Create one sensor per derived collection type, e.g. `sensor.<name>_mat_rest_next_date`

### Useful attributes

The main sensors expose attributes that are useful for automations and debugging:

- `next_day_types_display`: list of all collection types on the next pickup date
- `next_day_events`: list of event objects (includes `container_number` when the provider supplies it, e.g. `KÄRL 1`)
- `upcoming`: a limited list of upcoming events for automations

## Example automations

### Notify the day before (Mobile App)

```yaml
alias: Bin pickup tomorrow
trigger:
  - platform: time
    at: "18:00:00"
condition:
  - condition: state
    entity_id: sensor.binday_sweden_days_until_next_collection
    state: "1"
action:
  # Replace with your device notifier, e.g. notify.mobile_app_iphone or notify.mobile_app_pixel_7
  - service: notify.mobile_app_your_phone
    data:
      message: >
        Bin pickup tomorrow ({{ states('sensor.binday_sweden_next_collection_date') }}):
        {{ state_attr('sensor.binday_sweden_next_collection_type', 'next_day_types_display') | join(' + ') }}
```

### Notify the day before (Telegram)

```yaml
alias: Bin pickup tomorrow (Telegram)
trigger:
  - platform: time
    at: "18:00:00"
condition:
  - condition: state
    entity_id: sensor.binday_sweden_days_until_next_collection
    state: "1"
action:
  # Replace with your Telegram notifier, e.g. notify.telegram or notify.telegram_mychat
  - service: notify.telegram
    data:
      message: >
        Bin pickup tomorrow ({{ states('sensor.binday_sweden_next_collection_date') }}):
        {{ state_attr('sensor.binday_sweden_next_collection_type', 'next_day_types_display') | join(' + ') }}
```

### Notify on the morning of pickup

```yaml
alias: Bin pickup today
trigger:
  - platform: time
    at: "07:00:00"
condition:
  - condition: state
    entity_id: sensor.binday_sweden_days_until_next_collection
    state: "0"
action:
  - service: notify.notify
    data:
      message: >
        Bin pickup today: {{ states('sensor.binday_sweden_next_collection_type') }}
```

## Notes / TODO

- No HTML scraping; providers should use documented/undocumented JSON endpoints where available.
- Add more provider implementations and expand the kommun → provider mapping in `custom_components/binday_sweden/providers/routing.py`.

## License

MIT. See `LICENSE`.
