# Domovladelets for Home Assistant

A Home Assistant custom integration for a "Domovladelets" (homeowner) utility
account. It signs in with your account credentials and polls the account screen
for outstanding charges and recent payments, exposing them as Home Assistant
entities.

> **Unofficial.** This project is not affiliated with, endorsed by, or
> sponsored by the operator of the "Domovladelets" application. Use it with
> your own account only, at your own risk.

## Features

The integration polls the account screen on a schedule and exposes:

- **Amount due** — the outstanding balance shown as "to pay".
- **Charged** — the total charged for the current period.
- **Paid** — the total paid for the current period.
- **Unpaid documents** — a `binary_sensor` that turns on when any document is
  unpaid.
- **Last payment** — the date of the most recent payment, with the amount as an
  attribute.
- **Diagnostics** — a redacted account snapshot for bug reports
  (*Settings → Devices & Services → Domovladelets → Download diagnostics*).

All values are read-only. The integration never performs payments or sends
meter readings.

## Requirements

- Home Assistant 2025.1 or newer.
- A working "Domovladelets" account.
- The `pydmvl` Python package (installed automatically from PyPI by Home
  Assistant).

## Installation

### HACS

1. Add this repository to HACS as a custom repository
   (category: *Integration*).
2. Install **Domovladelets** and restart Home Assistant.

### Manual

Copy `custom_components/dmvl/` from this repository into your Home Assistant
`config/custom_components/` directory and restart Home Assistant.

## Configuration

1. Go to *Settings → Devices & Services → Add Integration*.
2. Search for **Domovladelets**.
3. Enter your account login and password.
4. Optionally enable **Verify TLS certificate**.

The service sends the credentials with every request, so the login and password
are stored in the Home Assistant config entry and are never written to logs or
diagnostics. The login is used as the config-entry unique identifier.

### Verify TLS certificate

The service may present an incomplete certificate chain, which makes strict TLS
verification fail on some systems. The option therefore defaults to **off**.
Turn it on to require a valid certificate chain if your setup supports it.

## Entities

| Entity | Type | Description |
|---|---|---|
| Amount due | `sensor` | Outstanding balance ("to pay") |
| Charged | `sensor` | Total charged for the current period |
| Paid | `sensor` | Total paid for the current period |
| Unpaid documents | `binary_sensor` | On when a document is unpaid |
| Last payment | `sensor` | Date of the latest payment (`amount` attribute) |

The account is represented as a single Home Assistant device; all entities
belong to it.

## Removal

1. In Home Assistant, go to *Settings → Devices & Services*, select
   **Domovladelets**, open the entry menu and choose **Delete**. This removes
   the config entry and the credentials stored with it.
2. If you installed through HACS, uninstall **Domovladelets** from HACS.
   Otherwise delete the `custom_components/dmvl/` directory.
3. Restart Home Assistant.

## Roadmap

- Meter readings (read-only) and their submission period.
- Per-segment amount due and receipt links.
- Options flow to select the visible entity set.

## License

MIT — see [LICENSE](LICENSE).
