# Domovladelets for Home Assistant

A Home Assistant custom integration for a "Domovladelets" (homeowner) utility
account. It signs in with your account credentials and polls the account screen
for outstanding charges and recent payments, exposing them as Home Assistant
entities.

## Домовладелец для Home Assistant

Неофициальная интеграция Home Assistant для личного кабинета
«Домовладелец»: вход по логину и паролю вашего аккаунта, периодический опрос
экрана личного кабинета и публикация начислений и платежей в виде сущностей
Home Assistant.

> **Неофициальная интеграция.** Проект не связан с оператором приложения
> «Домовладелец», не одобрен и не спонсируется им. Используйте только со
> своим аккаунтом, на свой риск.

> **Unofficial.** This project is not affiliated with, endorsed by, or
> sponsored by the operator of the "Domovladelets" application. Use it with
> your own account only, at your own risk.

## Features

The integration polls the account screen on a schedule and exposes:

- **Account** — the account balance, shown as reported by the service. A
  negative value is the amount to pay; a positive value is an overpayment. Also
  carries the account identity, address, contacts, amounts and counts as
  attributes.
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
5. After setup, use *Configure* to choose the optional entities.

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
| Account | `sensor` | Account balance as reported (negative = to pay, positive = overpayment); also carries identity/address/contacts/amounts/counts attributes |
| Charged | `sensor` | Total charged for the current period; `period` and `payment_purpose` attributes |
| Paid | `sensor` | Total paid for the current period; `period`, `payment_purpose`, `last_payment_date` and `payments` attributes |
| Unpaid documents | `binary_sensor` | On when a document is unpaid |
| Last payment | `sensor` | Date of the latest payment (`amount` attribute) |

The account is represented as a single Home Assistant device named after the
management organization and the account code (`<organization> · <account>`,
falling back to the login, then to a constant); all entities belong to it.
Entity ids are stable and account-specific
(`<platform>.dmvl_<login-slug>_<suffix>`, e.g. `sensor.dmvl_user_example_com_paid`),
independent of the device name and area.

### Optional entities

The account options (*Settings → Devices & Services → Domovladelets →
Configure*) let you choose the entity set. **Account** and **Unpaid documents**
are always created; everything else is opt-in:

- **Charged**, **Paid**, **Last payment** — the per-period aggregates
  (enabled by default);
- **Meters** — one `sensor` per meter: the state is the reading the service
  marks as actual, falling back to the most recent period when none is marked;
  attributes include `volume`, `kind`, `period_start`/`period_end`, `checked`,
  `is_actual`, a `readings` history, and the monthly submission window
  (`submit_period_start`/`submit_period_end`/`submit_period_active`);
- **Receipts** — a `sensor` whose state is the number of receipts and whose
  `receipts` attribute lists `{kind, name, link}`
  (`utilities` and `capital_repair`);
- **Charge history** — a `sensor` whose state is the number of charge periods
  and whose `periods` attribute lists
  `{date, charged, charged_adjusted, benefit, difference, paid,
  debt_opening, debt_closing, is_paid}`;
- **Amount due by channel** — a `sensor` whose state is the number of payment
  segments and whose `segments` attribute breaks the amount due down by
  payment provider; a failed breakdown leaves the other entities available.

A meter added to the account after setup appears after a reload/restart.

## Data updates

Account data is read-only and refreshed:

- **on startup** — one fetch when the integration is set up;
- **on a schedule** — every 6 hours by default, configurable from 1 to 24 hours
  in the account options;
- **on demand** — the `dmvl.refresh` action fetches immediately, for example
  after a payment:

  ```yaml
  action: dmvl.refresh
  target:
    entity_id: sensor.dmvl_user_example_com_account
  ```

  Without a target the action refreshes every configured account.

  The action stays available across a config entry reload (options change or
  `homeassistant.reload_config_entry`); a reload no longer drops it. It is
  registered while an account is configured, so callers do not need to restart
  Home Assistant to use it.

## Removal

1. In Home Assistant, go to *Settings → Devices & Services*, select
   **Domovladelets**, open the entry menu and choose **Delete**. This removes
   the config entry and the credentials stored with it.
2. If you installed through HACS, uninstall **Domovladelets** from HACS.
   Otherwise delete the `custom_components/dmvl/` directory.
3. Restart Home Assistant.

## Roadmap

- Submitting meter readings and other account-changing actions (needs an
  explicit confirmation and a separate design).
- Verification-date reminders for meters.

## License

MIT — see [LICENSE](LICENSE).
