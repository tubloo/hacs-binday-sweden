# BinDay Sweden (Home Assistant / HACS)

A Sweden-only Home Assistant custom integration that exposes your next waste/bin collection date(s).

Waste collection is organized at the municipality (kommun) level and bin/fraction naming varies widely. This integration models collection types dynamically based on provider data (no fixed “bin_1/bin_2” assumptions).

## Disclaimer

- This is an unofficial, community project and is not affiliated with Home Assistant, municipalities, or any waste provider (e.g. NSR AB).
- Provider endpoints and data formats may change without notice. Schedules may be incomplete, delayed, or incorrect; always rely on official provider information for critical decisions.
- Address searches and selected match IDs are sent to the provider you choose in order to fetch your schedule.

## Built with Codex

This integration was developed with help from Codex CLI (OpenAI).

## Supported providers / municipalities

### NSR AB (NSR)

Right now, only **NSR AB** is supported.

| Län | Kommun | Provider |
|---|---|---|
| Skåne län | Bjuv | NSR AB |
| Skåne län | Båstad | NSR AB |
| Skåne län | Helsingborg | NSR AB |
| Skåne län | Höganäs | NSR AB |
| Skåne län | Åstorp | NSR AB |
| Skåne län | Ängelholm | NSR AB |

If your municipality is not in the list, setup will show: “Your municipality is not supported yet.”

Note: In the UI, some municipalities may appear in the official form (e.g. `Helsingborgs`), but they still map to the same kommun.

## Install (HACS)

1. HACS → Integrations → 3 dots → **Custom repositories**
2. Add this repo as **Integration**
3. Install **BinDay Sweden**
4. Restart Home Assistant

## Configure

Settings → Devices & Services → Add Integration → **BinDay Sweden**

You will be asked for:
- `Län` (dropdown)
- `Kommun` (dropdown)
- `Address search` (free text; used against the provider’s search endpoint)
- If multiple matches are found: select the exact address/property
- Optional: update interval (hours)

## Entities

- `sensor.<name>_next_collection_date` (date)
- `sensor.<name>_next_collection_type` (string)
- `sensor.<name>_days_until_next_collection` (int)

Optional (Settings → Configure on the integration):
- Create one sensor per derived collection type, e.g. `sensor.<name>_mat_rest_next_date`

Each sensor exposes useful attributes like provider name, selected match id/label, and a list of upcoming events for automations.

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
