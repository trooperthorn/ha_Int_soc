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
| 24 GHz radar module | Hi-Link **HLK-LD2450** (get one that comes with its 4-pin cable) | $10–12 |
| Microcontroller | **ESP32-C5-DevKitC-1-N8R8** for 5 GHz Wi-Fi (this build's choice: no screen, 2.4 GHz kept free). Not the N8R4, which DigiKey lists as obsolete. An ESP32-C6 or classic ESP32 works on 2.4 GHz, an ESP32-S3 if you want a screen (see "Which ESP32 chip" below) | $15–25 |
| Jumper wires | Female-female Dupont wires, if your LD2450 cable doesn't end in Dupont plugs | $5 |
| Power | 5 V USB power supply (1 A+) and a USB cable for the ESP32 | $8–10 |
| Enclosure (optional) | A small project box or a 3D-printed case. Leave the radar face uncovered, or behind thin plastic only (never metal) | $5 |

**About $40–55 per sensor** with the C5. Sellers are listed under
"Where to buy" below. You also need a Home Assistant install with the
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

## Where to buy

Prices seen in September 2026 searches; check the listing before ordering.

| Part | Seller | Notes |
| --- | --- | --- |
| ESP32-C5-DevKitC-1-N8R8 | [DigiKey](https://www.digikey.com/en/products/detail/espressif-systems/ESP32-C5-DEVKITC-1-N8R8/28718162) | Authorized distributor, was showing in stock. Best choice for a genuine board |
| | [Mouser](https://www.mouser.com/en/ProductDetail/Espressif-Systems/ESP32-C5-DevKitC-1-N8R8?qs=6avfeC6zeS67aD1hu9NHBw%3D%3D) | Authorized distributor |
| | [Amazon (Espressif listing)](https://www.amazon.com/Espressif-ESP32-C5-DevKitC-1-N8R8-Development-Board/dp/B0G4CY619B) | Faster shipping. Check the seller is Espressif or a known distributor; third-party "C5 DevKitC" clones exist |
| Alternative C5 board | [SparkFun Thing Plus ESP32-C5](https://www.sparkfun.com/sparkfun-thing-plus-esp32-c5.html) | $24.95. Feather layout, Qwiic, LiPo charger. Needs its own pin mapping |
| HLK-LD2450 | [ShillehTek](https://shillehtek.com/products/hlk-ld2450-24ghz-mmwave-radar-human-body-tracking-sensor-module) | $11.99, header pins pre-soldered, US seller |
| | [eBay](https://www.ebay.com/itm/395097848306) | From about $10.33, volume discounts |
| | [Amazon (1 pc)](https://www.amazon.com/JMT-HLK-LD2450-Trajectory-Induction-Measurement/dp/B0CGNMCTRC) / [5 pcs](https://www.amazon.com/JMT-HLK-LD2450-Trajectory-Induction-Measurement/dp/B0CQ2JX4HC) | Multi-packs if you're doing several rooms |
| | [AliExpress](https://www.aliexpress.us/item/3256805663484615.html) | Cheapest, slowest. Choose the option that includes the cable |
| | [Hi-Link (manufacturer)](https://www.hlktech.net/index.php?id=1157) | Product page and official manual downloads |

Jumper wires, USB-C cable and a 5 V 1 A+ USB power supply can come from
anywhere. Use a USB-C cable that carries data, not a charge-only one, for the
first flash.

## Datasheets and verified facts

| Fact | Value | Source |
| --- | --- | --- |
| LD2450 supply | 5 V, supply able to deliver more than 200 mA | LD2450 manual |
| LD2450 UART | 256000 baud, 8 data bits, no parity, 1 stop bit; 3.3 V I/O | LD2450 manual |
| LD2450 coverage | Up to 6 m; ±60° azimuth, ±35° pitch; up to 3 targets | LD2450 manual |
| LD2450 mounting | Wall-mounted, 1.5–2 m high | LD2450 manual |
| LD2450 firmware for ESPHome | V2.02.23090617 or later | ESPHome `ld2450` docs |
| ESP32-C5 radio | 2.4 and 5 GHz Wi-Fi 6, Bluetooth LE 5, Zigbee 3.0, Thread 1.4 | ESP32-C5 datasheet |
| ESP32-C5 in ESPHome | ESP-IDF framework only; `band_mode` since 2026.3.0 | ESPHome changelog, PR #14148 |
| DevKitC-1 UART0 | GPIO11 TX, GPIO12 RX (to the USB-to-UART bridge) | DevKitC-1 user guide |
| DevKitC-1 strapping pins | GPIO2, 3, 7, 25, 26, 27, 28 | DevKitC-1 user guide |

Documents:

- LD2450 instruction manual: [TinyTronics PDF](https://www.tinytronics.nl/product_files/006000_HLK-LD2450-Instruction-Manual.pdf), [ManualsLib](https://www.manualslib.com/manual/3439736/Hi-Link-Hlk-Ld2450.html)
- [ESP32-C5 datasheet](https://documentation.espressif.com/esp32-c5_datasheet_en.pdf) and [ESP32-C5-WROOM-1 module datasheet](https://documentation.espressif.com/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf)
- [ESP32-C5-DevKitC-1 user guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c5/esp32-c5-devkitc-1/user_guide.html) ([source on GitHub](https://github.com/espressif/esp-dev-kits/blob/master/docs/en/esp32-c5-devkitc-1/user_guide.rst))
- [ESP32-C5 hardware design guidelines](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c5/esp-hardware-design-guidelines-en-master-esp32c5.pdf)
- ESPHome: [LD2450 component](https://esphome.io/components/sensor/ld2450/), [Wi-Fi component (`band_mode`)](https://esphome.io/components/wifi/), [2026.3.0 changelog](https://esphome.io/changelog/2026.3.0/), [issue #15015](https://github.com/esphome/esphome/issues/15015), [PR #15152](https://github.com/esphome/esphome/pull/15152)

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
| **ESP32-C5** | Yes | You need 5 GHz Wi-Fi | Dual-band 2.4/5 GHz Wi-Fi 6, 240 MHz RISC-V. ESPHome supports it on ESP-IDF only (not Arduino); `band_mode` needs ESPHome 2026.3.0 or later |
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

To keep the C5 on 5 GHz, set `band_mode: 5GHZ` under `wifi:` (ESPHome
2026.3.0 or later; the config below does this). In 2026.3.0, `fast_connect`
and `post_connect_roaming` could still pull the device back onto 2.4 GHz;
ESPHome PR #15152, shipped in the 2026.3 series, made them respect
`band_mode`, so use a current release. A 5 GHz-only SSID (UniFi: Settings →
WiFi → the network → WiFi Band: 5 GHz) is a good second safeguard. 5 GHz
covers less distance through walls, so check the sensor's signal strength in
ESPHome's logs once it is mounted and move it or add an access point if it
is below about -75 dBm.

Board settings and UART pins per chip (LD2450 TX goes to the ESP's RX pin):

| Chip | `esp32:` block | ESP RX pin | ESP TX pin |
| --- | --- | --- | --- |
| ESP32 | `board: esp32dev` | GPIO16 | GPIO17 |
| ESP32-S3 | `board: esp32-s3-devkitc-1`, `variant: esp32s3` | GPIO16 | GPIO17 |
| ESP32-C6 | `board: esp32-c6-devkitc-1`, `variant: esp32c6` | GPIO5 | GPIO4 |
| ESP32-C3 | `board: esp32-c3-devkitm-1`, `variant: esp32c3` | GPIO20 | GPIO21 |
| ESP32-C5 | `board: esp32-c5-devkitc-1`, `variant: esp32c5` | GPIO4 | GPIO5 |

On the C3, GPIO20/21 are the chip's console UART pins, so keep
`logger: baud_rate: 0` and flash and log over the board's USB port. Keep
`baud_rate: 0` on every chip anyway; the logger doesn't need the UART.

On the ESP32-C5-DevKitC-1, GPIO4 and GPIO5 are header J3 pins 8 and 9. They
are the JTAG MTCK/MTDO pins, not strapping pins, and their alternate
functions are the low-power UART's RXD/TXD, which is why RX is GPIO4 and TX is
GPIO5. Avoid the strapping pins (GPIO2, 3, 7, 25, 26, 27, 28), GPIO27 (it
also drives the on-board RGB LED), GPIO13/14 (USB), GPIO11/12 (UART0, wired
to the USB-to-UART bridge), and GPIO15 (used by the PSRAM on the N8R8).
The 5 V pin is J1 pin 14. Always use `framework: type: esp-idf` for the C-series.

## Wiring (ESP32 ↔ LD2450)

| LD2450 pin | ESP32 pin |
| --- | --- |
| 5V | 5V (VIN) |
| GND | GND |
| TX | GPIO16 (RX2), or your chip's RX pin from the table above |
| RX | GPIO17 (TX2), or your chip's TX pin from the table above |

TX goes to RX and RX to TX. On the C5 board that is LD2450 TX → GPIO4,
LD2450 RX → GPIO5, 5V → J1 pin 14, GND → GND. The LD2450 needs 5 V at more
than 200 mA; its data lines are 3.3 V, so they connect straight to the ESP32
with no level shifter. Power the board from a 1 A+ USB supply so the 5 V
pin can feed the radar.

## ESPHome config

In ESPHome Device Builder, create a new device, choose ESP32, then replace
the generated YAML (keep your own `wifi`, `api` and `ota` keys) with this:

```yaml
esphome:
  name: radar-living-room

esp32:
  board: esp32-c5-devkitc-1
  variant: esp32c5
  framework:
    type: esp-idf   # the C5 is ESP-IDF only

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
  band_mode: 5GHZ   # ESP32-C5 only; ESPHome 2026.3.0+

uart:
  id: uart_ld2450
  tx_pin: GPIO5   # to LD2450 RX
  rx_pin: GPIO4   # from LD2450 TX
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
