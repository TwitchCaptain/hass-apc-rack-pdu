# Home Assistant — APC Metered Rack PDU

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Custom Home Assistant integration for **APC metered rack PDUs** (AP88xx / PowerNet-MIB `rPDU2`), including models like the **AP8858** with an optional temperature/humidity probe.

This is a proper **device** integration (UI config flow), not a pile of YAML SNMP sensors. It is the Home Assistant successor to the Indigo plugin [indigoplugins-apc-metered-rack-pdu](https://github.com/davidnewhall/indigoplugins-apc-metered-rack-pdu).

> **Note:** Metered PDUs (AP8858 and friends) report aggregate power only. They do **not** switch individual outlets. For switched PDUs, use a switched-outlet integration instead. Or open a pull request.

## Features

| Capability | Details |
|---|---|
| **Device** | One HA device per PDU (model, serial, firmware, config URL) |
| **Power** | Real-time watts, peak watts, load %, load state |
| **Energy** | Cumulative kWh (`total_increasing` — Energy dashboard ready) |
| **Electrical** | Current (A), voltage (V), apparent power (VA), power factor |
| **Environment** | Optional probe: temperature (°F) and humidity (% RH) |
| **Safety** | Binary sensors for near-overload and overload |
| **Actions** | Reset energy / reset peak power (SNMP SET); identify / blink LCD (SSH) |

Polling is pure **SNMP** (fast, no SSH for telemetry). SSH is only used for the optional LCD identify button.

## Screenshots / entities

After setup you get entities such as:

- `sensor.rack_pdu_power`, `sensor.rack_pdu_energy`, `sensor.rack_pdu_current`, `sensor.rack_pdu_voltage`
- `sensor.rack_pdu_temperature`, `sensor.rack_pdu_humidity` (when a probe is attached)
- `binary_sensor.rack_pdu_overload`, `binary_sensor.rack_pdu_near_overload`
- `button.rack_pdu_reset_energy`, `button.rack_pdu_reset_peak_power`, `button.rack_pdu_identify_blink_lcd`

Entity IDs follow the device name you choose in the config flow (default: **Rack PDU**).

## Requirements

- Home Assistant 2024.1+ (developed against 2026.x)
- APC metered rack PDU with SNMP enabled (SNMPv1 community auth)
- Network reachability from the HA host to the PDU (`UDP/161`)
- Write community (often `private`) for energy / peak reset buttons
- Optional: SSH credentials (often `apc` / `apc`) for LCD identify; `expect` on the HA host

## Install

### Manual

1. Copy `custom_components/apc_rack_pdu` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → APC Metered Rack PDU**.
4. Enter host and SNMP communities.

### HACS (custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add `https://github.com/TwitchCaptain/hass-apc-rack-pdu` as category **Integration**
3. Install **APC Metered Rack PDU**, then restart HA and add the integration as above.

## Configuration

| Field | Default | Purpose |
|---|---|---|
| Host | — | Hostname or IP of the PDU |
| Name | `Rack PDU` | Device / entity name prefix |
| SNMP read community | `public` | Telemetry |
| SNMP write community | `private` | Energy / peak resets |
| Port | `161` | SNMP |
| Poll interval | `30` | Seconds |
| SSH username / password | optional | LCD identify |

Options (after setup): poll interval, env-probe toggle, write community.

## Example: rack cooling automation

Drive a rack AC from the PDU’s closet temperature probe:

```yaml
automation:
  - id: cool_rack_on
    alias: Cool Rack
    triggers:
      - trigger: numeric_state
        entity_id: sensor.rack_pdu_temperature
        above: 86
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.rack_ac

  - id: cool_rack_off
    alias: Cool Rack Off
    triggers:
      - trigger: numeric_state
        entity_id: sensor.rack_pdu_temperature
        below: 73
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.rack_ac
```

A full package example lives in [`examples/rack_ac.yaml`](examples/rack_ac.yaml).

## SNMP notes

Uses PowerNet-MIB under `1.3.6.1.4.1.318.1.1.26` (`rPDU2`):

| Metric | OID (index `.1`) | Scale |
|---|---|---|
| Power | `…26.4.3.1.5` | hundredths of kW → W |
| Peak power | `…26.4.3.1.6` | hundredths of kW → W |
| Energy | `…26.4.3.1.9` | tenths of kWh |
| Current / voltage | `…26.6.3.1.5` / `…26.6.3.1.6` | tenths A / volts |
| Temp °F | `…26.10.2.2.1.7` | tenths °F |
| Humidity | `…26.10.2.2.1.10` | % RH (not tenths) |
| Reset energy | `…26.4.1.1.11` | SET `2` = reset |

**Gotcha:** OID `…10.2.2.1.8` is temperature in **°C**, not humidity. Humidity is `…1.10`.

## Related

- Indigo plugin (SSH-based): https://github.com/davidnewhall/indigoplugins-apc-metered-rack-pdu
- APC PowerNet MIB / rPDU2 documentation from Schneider Electric

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements_test.txt
pytest -q tests
ruff check custom_components/apc_rack_pdu tests
```

CI runs pytest, ruff, [hassfest](https://github.com/home-assistant/actions), and HACS validation on every push/PR.

## License

[MIT](LICENSE) © 2026 [Go Lift Technologies LLC](https://golift.io)
