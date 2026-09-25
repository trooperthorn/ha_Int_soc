# mmWave radar presence sensor for Home Assistant

A standalone DIY build, separate from HA SOC itself; it pairs with the
physical-security tier in `SHOPPING-LIST.md`.

What the video shows: a 24 GHz mmWave radar module (the "12 mm" wavelength
the video mentions is 24 GHz) wired to a Raspberry Pi with a touchscreen. The
screen draws a live radar fan with a dot for each person and their distance
("0.8 m"), and it keeps working through a wall. The module that tracks
people as X/Y dots on a fan like that is the **Hi-Link HLK-LD2450**: up to 3
targets, about 6 m range, ±60° field of view.

The breadboard diagram in the video (Arduino Nano, HC-05 Bluetooth, TP4056
charger, 850 mAh LiPo) is a stock graphic. It isn't the radar build.

## Recommended build: ESP32 + LD2450 on ESPHome

Home Assistant supports this natively. ESPHome has a built-in `ld2450`
component, so the sensor shows up in HA with no code, and you draw the radar
view on an HA dashboard instead of on a separate Pi screen.

### Shopping list

| Item | Example | Approx. |
| --- | --- | --- |
| 24 GHz radar module | Hi-Link **HLK-LD2450** (get one that comes with its 4-pin cable) | $10–15 |
| Microcontroller | **ESP32-C5-DevKitC-1** for 5 GHz Wi-Fi (this build's choice: no screen, 2.4 GHz kept free); an ESP32-C6 or classic ESP32 works on 2.4 GHz, an ESP32-S3 if you want a screen (see "Which ESP32 chip" below) | $6–15 |
| Jumper wires | Female-female Dupont wires, if your LD2450 cable doesn't end in Dupont plugs | $5 |
| Power | 5 V USB power supply (1 A+) and a USB cable for the ESP32 | $8–10 |
| Enclosure (optional) | A small project box or a 3D-printed case. Leave the radar face uncovered, or behind thin plastic only (never metal) | $5 |

**About $30–45 per sensor.** You also need a Home Assistant install with the
ESPHome add-on (Settings → Add-ons → ESPHome Device Builder).

### Optional: a standalone screen like the one in the video

If you want the physical radar display as well as the HA dashboard, choose
one:

| Option | Items | Approx. |
| --- | --- | --- |
| ESP32 with a built-in screen (still ESPHome) | Waveshare or Guition **ESP32-S3 4.3"/5" touch display** board instead of the plain ESP32. ESPHome's LVGL support can draw the fan and dots | $30–50 |
| The video's Pi route | Raspberry Pi 4/5 (or Zero 2 W), official 5"/7" touchscreen, and a **USB-to-TTL adapter (CP2102/CH340)** for the LD2450. Needs your own Python app that sends data to HA over MQTT (Mosquitto add-on) | $120–180 |

### Off-the-shelf instead of DIY

- **Everything Presence Lite** (Everything Smart Home). Ships with ESPHome
  already set up, with an LD2450-style target-tracking option. About $45.
- **Aqara FP2** (60 GHz, zones, up to 5 people). Adds to HA through the
  HomeKit Device integration. About $80. Needs 2.4 GHz Wi-Fi.

## Which ESP32 chip

The LD2450 only needs one spare UART at 256000 baud and 5 V power, so any
Wi-Fi ESP32 that ESPHome supports can run it. The choice comes down to what
else you want the board to do. There is no ESP32-S6; the newer chips are
the C-series (C5, C6) and P4.

| Chip | Works? | Pick it when | Notes |
| --- | --- | --- | --- |
| **ESP32-S3** | Yes, recommended | You want the on-device radar screen, or one board for radar + Bluetooth proxy | Dual-core 240 MHz, boards with 8 MB PSRAM, and the touchscreen boards are S3. ESPHome's LVGL display support is most mature here |
| ESP32 (classic) | Yes | Cheapest headless sensor | What most LD2450 examples use. Wi-Fi 4, Bluetooth classic + BLE |
| **ESP32-C6** | Yes | Headless sensor on Wi-Fi 6, or you want the Thread/Zigbee radio for later | Single-core RISC-V 160 MHz, plenty for the LD2450. Needs the ESP-IDF framework. Few boards have PSRAM, so not a good fit for the screen build |
| ESP32-C3 | Yes | Tiny, cheap headless sensor | Single-core 160 MHz, Wi-Fi 4 + BLE |
| ESP32-C5 | Probably | You need 5 GHz Wi-Fi | Dual-band Wi-Fi 6. ESPHome support is newer; check the ESPHome docs for your version before buying |
| ESP32-S2 | Yes | Only if you already own one | No Bluetooth, so it can't also be a Bluetooth proxy |
| ESP32-H2 / P4 | No (alone) | — | No Wi-Fi. The H2 is Thread/Zigbee only; the P4 needs a companion Wi-Fi chip |

### Wi-Fi band

Only the **ESP32-C5** has 5 GHz (dual-band 2.4/5 GHz Wi-Fi 6, e.g. Espressif's
ESP32-C5-DevKitC-1). No ESP32 supports 6 GHz (Wi-Fi 6E/7). Every other chip
above is 2.4 GHz only. Wi-Fi 6 on the C6 means the Wi-Fi 6 protocol on
2.4 GHz, not 5 or 6 GHz.

For a sensor that sends a few bytes a second, 2.4 GHz is the better band: it
reaches further and gets through walls better. A 2.4 GHz-only IoT SSID on its
own VLAN is the usual setup. To avoid Wi-Fi altogether, use an ESP32
Ethernet/PoE board (Olimex ESP32-POE-ISO, WT32-ETH01); ESPHome supports
both through its `ethernet:` component.

To run the C5 on 5 GHz only, give it an SSID that is broadcast on 5 GHz
only (UniFi: Settings → WiFi → the network → WiFi Band: 5 GHz), rather than
relying on the device to choose a band. 5 GHz covers less distance through
walls, so check the sensor's signal strength in ESPHome's logs once it is
mounted and move it or add an access point if it is below about -75 dBm. The C5
pins above are a starting point: confirm GPIO4/GPIO5 are free on your board's
pinout before wiring, and that your ESPHome version lists the C5 as
supported.

Board settings and UART pins per chip (LD2450 TX goes to the ESP's RX pin):

| Chip | `esp32:` block | ESP RX pin | ESP TX pin |
| --- | --- | --- | --- |
| ESP32 | `board: esp32dev` | GPIO16 | GPIO17 |
| ESP32-S3 | `board: esp32-s3-devkitc-1`, `variant: esp32s3` | GPIO16 | GPIO17 |
| ESP32-C6 | `board: esp32-c6-devkitc-1`, `variant: esp32c6` | GPIO5 | GPIO4 |
| ESP32-C3 | `board: esp32-c3-devkitm-1`, `variant: esp32c3` | GPIO20 | GPIO21 |
| ESP32-C5 | `board: esp32-c5-devkitc-1`, `variant: esp32c5` | GPIO5 | GPIO4 |

On the C3, GPIO20/21 are the chip's console UART pins, so keep
`logger: baud_rate: 0` and flash and log over the board's USB port. Keep
`baud_rate: 0` on every chip anyway; the logger doesn't need the UART. Always use `framework: type: esp-idf` for the C-series.

## Wiring (ESP32 ↔ LD2450)

| LD2450 pin | ESP32 pin |
| --- | --- |
| 5V | 5V (VIN) |
| GND | GND |
| TX | GPIO16 (RX2), or your chip's RX pin from the table above |
| RX | GPIO17 (TX2), or your chip's TX pin from the table above |

TX goes to RX and RX to TX. The LD2450 needs 5 V power; its data lines are
3.3 V, so they connect straight to the ESP32 with no level shifter.

## ESPHome config

In ESPHome Device Builder, create a new device, choose ESP32, then replace
the generated YAML (keep your own `wifi`, `api` and `ota` keys) with this:

```yaml
esphome:
  name: radar-living-room

esp32:
  board: esp32dev
  framework:
    type: esp-idf

logger:
  baud_rate: 0   # keep the UART free for the radar

api:
  encryption:
    key: !secret radar_api_key
ota:
  - platform: esphome
    password: !secret ota_password
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

uart:
  id: uart_ld2450
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 256000
  parity: NONE
  stop_bits: 1

ld2450:
  id: ld2450_radar
  uart_id: uart_ld2450

binary_sensor:
  - platform: ld2450
    ld2450_id: ld2450_radar
    has_target:
      name: Presence
    has_moving_target:
      name: Moving target
    has_still_target:
      name: Still target

sensor:
  - platform: ld2450
    ld2450_id: ld2450_radar
    target_count:
      name: Target count
    target_1:
      x:
        name: Target 1 X
      y:
        name: Target 1 Y
      distance:
        name: Target 1 distance
      speed:
        name: Target 1 speed
    target_2:
      x:
        name: Target 2 X
      y:
        name: Target 2 Y
    target_3:
      x:
        name: Target 3 X
      y:
        name: Target 3 Y
```

Plug the ESP32 in over USB and click Install. HA then discovers it under
Settings → Devices & Services → ESPHome; click Configure to add it. Check
the exact option names against the current ESPHome `ld2450` docs if the
validator complains; the component gains options between releases.

## The radar view on a dashboard

Install **Plotly Graph Card** from HACS (Frontend) and add a manual card like
the one below. X/Y from the LD2450 are in millimetres, with the sensor at
(0, 0) facing +Y. Rename the entity IDs to match your device.

```yaml
type: custom:plotly-graph
title: Living room radar
refresh_interval: 1
hours_to_show: 1
layout:
  height: 360
  showlegend: false
  xaxis: { range: [-4500, 4500], zeroline: false, showgrid: true }
  yaxis: { range: [0, 6000], zeroline: false, showgrid: true, scaleanchor: x }
entities:
  - entity: ""
    name: Target 1
    mode: markers
    marker: { size: 16, color: "#20c997" }
    x: $ex [hass.states["sensor.radar_living_room_target_1_x"].state]
    y: $ex [hass.states["sensor.radar_living_room_target_1_y"].state]
  - entity: ""
    name: Target 2
    mode: markers
    marker: { size: 16, color: "#fd7e14" }
    x: $ex [hass.states["sensor.radar_living_room_target_2_x"].state]
    y: $ex [hass.states["sensor.radar_living_room_target_2_y"].state]
  - entity: ""
    name: Target 3
    mode: markers
    marker: { size: 16, color: "#6f42c1" }
    x: $ex [hass.states["sensor.radar_living_room_target_3_x"].state]
    y: $ex [hass.states["sensor.radar_living_room_target_3_y"].state]
```

Treat this card as a starting point. The Plotly card's `$ex` syntax is its
own, so if a dot doesn't draw, check the entity IDs first.

## What to use it for

- **Presence that doesn't drop out when you sit still**, which PIR motion
  sensors can't do. Use `binary_sensor.radar_living_room_presence` to keep
  lights on, or to turn them off after no presence for N minutes.
- **Zones.** Combine X/Y into template binary sensors ("on the couch", "at
  the desk") and trigger scenes from them.
- **People count** from `Target count`, for HVAC or for "someone's still
  home" in the alarm arming logic.

Example automation:

```yaml
alias: Living room lights follow presence
triggers:
  - trigger: state
    entity_id: binary_sensor.radar_living_room_presence
    to: "on"
    id: here
  - trigger: state
    entity_id: binary_sensor.radar_living_room_presence
    to: "off"
    for: { minutes: 5 }
    id: gone
actions:
  - choose:
      - conditions: [{ condition: trigger, id: here }]
        sequence: [{ action: light.turn_on, target: { area_id: living_room } }]
      - conditions: [{ condition: trigger, id: gone }]
        sequence: [{ action: light.turn_off, target: { area_id: living_room } }]
```

## What it can and can't do through walls

24 GHz passes through drywall, wood, glass and plastic at short range, with
reduced sensitivity. It is largely blocked by brick, concrete, tile with
mesh, metal, and foil-backed insulation. You get a dot and a distance, never
an image. Aim the sensor at the room you want to cover rather than relying
on seeing through a wall; mount it about 1.5–2 m high, and keep it away from
fans and curtains, which it sees as movement. Keep it pointed at your own
space.
