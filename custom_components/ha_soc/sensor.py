"""Sensors exposing HA SOC's analysis output as entities so users can
automate on them (e.g. notify when sensor.ha_soc_posture_score drops below
a threshold, or when a specific user's risk sensor goes critical).
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HaSocConfigEntry
from .const import DOMAIN, SIGNAL_UPDATE


def _device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, "ha_soc")},
        name="HA SOC",
        manufacturer="HA SOC",
        entry_type="service",
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: HaSocConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    async_add_entities(
        [
            PostureScoreSensor(runtime),
            OpenDetectionsSensor(runtime),
            UsersAtRiskSensor(runtime),
        ]
    )

    added_user_ids: set[str] = set()

    @callback
    def _sync_user_sensors() -> None:
        results = runtime.risk.last_risk_results or {}
        new_entities = [
            UserRiskSensor(runtime, user_id)
            for user_id in results
            if user_id not in added_user_ids
        ]
        if new_entities:
            added_user_ids.update(e.user_id for e in new_entities)
            async_add_entities(new_entities)

    _sync_user_sensors()
    entry.async_on_unload(
        async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_dashboard", _sync_user_sensors)
    )


class _BaseSocSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, runtime) -> None:
        self._runtime = runtime
        self._attr_device_info = _device_info()
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        self._unsub = async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATE}_dashboard", self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _handle_update(self, *_args) -> None:
        self.async_write_ha_state()


class PostureScoreSensor(_BaseSocSensor):
    _attr_translation_key = "posture_score"
    _attr_icon = "mdi:shield-check"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_unique_id = f"{DOMAIN}_posture_score"

    @property
    def native_value(self) -> int | None:
        posture = self._runtime.risk.last_posture_result
        return posture["score"] if posture else None

    @property
    def extra_state_attributes(self) -> dict:
        posture = self._runtime.risk.last_posture_result or {}
        return {"grade": posture.get("grade"), "breakdown": posture.get("breakdown")}


class OpenDetectionsSensor(_BaseSocSensor):
    _attr_translation_key = "open_detections"
    _attr_icon = "mdi:alert-decagram"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_unique_id = f"{DOMAIN}_open_detections"

    @property
    def native_value(self) -> int:
        return len(
            [
                d
                for d in self._runtime.store.data["detections"].values()
                if d.get("status") == "open"
            ]
        )


class UsersAtRiskSensor(_BaseSocSensor):
    _attr_translation_key = "users_at_risk"
    _attr_icon = "mdi:account-alert"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_unique_id = f"{DOMAIN}_users_at_risk"

    @property
    def native_value(self) -> int:
        results = self._runtime.risk.last_risk_results or {}
        return len([r for r in results.values() if r.get("score", 0) >= 60])


class UserRiskSensor(_BaseSocSensor):
    _attr_translation_key = "user_risk"
    _attr_icon = "mdi:account-lock"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, runtime, user_id: str) -> None:
        super().__init__(runtime)
        self.user_id = user_id
        self._attr_unique_id = f"{DOMAIN}_risk_{user_id}"

    @property
    def native_value(self) -> int | None:
        result = (self._runtime.risk.last_risk_results or {}).get(self.user_id)
        return result["score"] if result else None

    @property
    def extra_state_attributes(self) -> dict:
        result = (self._runtime.risk.last_risk_results or {}).get(self.user_id) or {}
        return {"band": result.get("band"), "top_factors": result.get("factors", [])[:3]}

    @property
    def available(self) -> bool:
        return self.user_id in (self._runtime.risk.last_risk_results or {})
