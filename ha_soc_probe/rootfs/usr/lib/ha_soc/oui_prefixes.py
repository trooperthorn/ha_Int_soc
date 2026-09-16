"""Static MAC-address vendor prefix table for netscan's host labels.

This is a small, hand-picked, EXPLICITLY NON-EXHAUSTIVE set of common
IEEE OUI (Organizationally Unique Identifier) prefixes seen on typical
home/small-office LANs (routers, NAS boxes, phones, IoT devices). It is
not a substitute for the full IEEE registry (tens of thousands of
entries) and is never treated as identity: it produces a best-effort
"vendor" label only, shown to the owner alongside the scanned host,
never used for any access decision.

Keys are the first three octets of a MAC address, uppercase hex with no
separators (e.g. the prefix of 3C:22:FB:xx:xx:xx is "3C22FB").
"""
from __future__ import annotations

OUI_PREFIXES: dict[str, str] = {
    # Apple
    "3C22FB": "Apple",
    "F0189E": "Apple",
    "A45E60": "Apple",
    "AC87A3": "Apple",
    "D8BB2C": "Apple",
    # Google / Nest
    "F4F5D8": "Google",
    "1C53F9": "Google",
    "544A00": "Google",
    # Amazon
    "F0D2F1": "Amazon",
    "747548": "Amazon",
    "68374E": "Amazon",
    # Samsung
    "8C7712": "Samsung",
    "FC426B": "Samsung",
    # Raspberry Pi Foundation
    "B827EB": "Raspberry Pi",
    "DCA632": "Raspberry Pi",
    "E45F01": "Raspberry Pi",
    # Ubiquiti / UniFi
    "24A43C": "Ubiquiti",
    "F09FC2": "Ubiquiti",
    "788A20": "Ubiquiti",
    # TP-Link
    "50C7BF": "TP-Link",
    "A42BB0": "TP-Link",
    # Netgear
    "A040A0": "Netgear",
    "2C3033": "Netgear",
    # Sonos
    "5CAAFD": "Sonos",
    "949F3E": "Sonos",
    # Espressif (ESP32/ESP8266 IoT modules)
    "246F28": "Espressif",
    "A020A6": "Espressif",
    "84CCA8": "Espressif",
    # Intel
    "3C5282": "Intel",
    "A0A8CD": "Intel",
    # Dell
    "F8B156": "Dell",
    "B8CA3A": "Dell",
    # HP / HPE
    "3C4A92": "HP",
    # Synology
    "0011D8": "Synology",
    "001132": "Synology",
    # Microsoft
    "60453C": "Microsoft",
    "0003FF": "Microsoft",
    # Roku
    "B02A43": "Roku",
    "D83134": "Roku",
    # Sonoff / Itead (common budget IoT)
    "2CF432": "Itead/Sonoff",
    # VMware (common for virtualized test hosts)
    "005056": "VMware",
    "000C29": "VMware",
}


def vendor_for_mac(mac: str | None) -> str | None:
    """Best-effort vendor label for a colon-separated MAC, or None.

    Never raises; an unrecognized or malformed address returns None
    rather than a guess.
    """
    if not mac:
        return None
    prefix = mac.replace(":", "").replace("-", "").upper()[:6]
    if len(prefix) != 6:
        return None
    return OUI_PREFIXES.get(prefix)
