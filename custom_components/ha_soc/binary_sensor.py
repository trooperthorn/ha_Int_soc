"""binary_sensor.ha_soc_suspicious_activity — on while any open detection is
high/critical severity. Meant to be the one entity most users automate on
("notify me the instant this trips") without needing to understand the
whole detection catalog.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HaSocConfigEntry
from .const import DOMAIN, SIGNAL_UPDATE
from .sensor import _device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: HaSocConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SuspiciousActivityBinarySensor(entry.runtime_data)])


class SuspiciousActivityBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "suspicious_activity"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_unique_id = f"{DOMAIN}_suspicious_activity"

    def __init__(self, runtime) -> None:
        self._runtime = runtime
        self._attr_device_info = _device_info()
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        self._unsub = async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATE}_detections", self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _handle_update(self, *_args) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return any(
            d.get("status") == "open" and d.get("severity") in ("high", "critical")
            for d in self._runtime.store.data["detections"].values()
        )

    @property
    def extra_state_attributes(self) -> dict:
        open_high = [
            d
            for d in self._runtime.store.data["detections"].values()
            if d.get("status") == "open" and d.get("severity") in ("high", "critical")
        ]
        return {"open_high_severity_count": len(open_high)}
