# WeightWatchers for Home Assistant

Custom Home Assistant integration for reading WeightWatchers points data.

Maintained by [`Xenolphthalein`](https://github.com/Xenolphthalein).

## Features

- Config flow setup from the Home Assistant UI
- Automatic reauthentication when session cookies expire
- Multiple account support (one config entry per WW account)
- Cloud polling via official WeightWatchers web endpoints

## Sensors

- `daily_points_remaining`
- `daily_points_used`
- `daily_activity_points_earned`
- `weekly_points_remaining`

Entity IDs default to email-based naming, for example:

- `sensor.weightwatchers_jane_example_com_daily_activity_points_earned`

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant.
2. Add `https://github.com/Xenolphthalein/ha-weightwatchers` as a custom repository.
3. Select category: `Integration`.
4. Install `WeightWatchers`.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/weightwatchers` into your Home Assistant config directory under `custom_components`.
2. Restart Home Assistant.
3. Go to **Settings -> Devices & Services -> Add Integration**.
4. Search for **WeightWatchers**.

## Configuration

Setup fields:

- Region (for example: `DE`, `US`, `UK`)
- Username / email
- Password

Options:

- Region

## Development

### Lint and format (Ruff)

```bash
ruff format .
ruff check .
```

CI workflows included:

- Ruff lint/format check
- HACS validation
- Hassfest validation

## License

This project is licensed under the Unlicense. See `LICENSE`.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by WeightWatchers.
