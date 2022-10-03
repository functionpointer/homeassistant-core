"""Platform for sensor integration."""
from __future__ import annotations

from chargecloudapi import Location

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ChargeCloudDataUpdateCoordinator
from .const import DOMAIN, EvseId


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a Geocaching sensor entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ChargeCloudRealtimeSensor(
                evse_id=entry.data["evse_id"], coordinator=coordinator
            )
        ]
    )


class ChargeCloudRealtimeSensor(
    CoordinatorEntity[ChargeCloudDataUpdateCoordinator], SensorEntity
):
    """Main feature of this integration. This sensor represents an EVSE and shows its realtime availability status."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        evse_id: EvseId,
        coordinator: ChargeCloudDataUpdateCoordinator,
    ) -> None:
        """Initialize the Sensor."""
        super().__init__(coordinator)
        self.evse_id = evse_id
        self.coordinator = coordinator
        self._attr_unique_id = f"{evse_id}-realtime"
        self._attr_attribution = f"chargecloud.de"
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_state_class = None
        self._attr_device_info = DeviceInfo(
            name=self.evse_id,
            identifiers={(DOMAIN, self.evse_id)},
            entry_type=None,
        )

    @property
    def icon(self):
        iconmap: dict[str, str] = {
            "IEC_62196_T2": "mdi:ev-plug-type2",
            "IEC_62196_T2_COMBO": "mdi:ev-plug-ccs2",
            "CHADEMO": "mdi:ev-plug-chademo",
            "TESLA": "mdi:ev-plug-tesla",
            "DOMESTIC_F": "mdi:power-socket-eu",
        }
        standard = "asdf"
        return iconmap.get(standard, "mdi:ev-station")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for l in self.coordinator.data:
            loc: Location = l
            for evse in loc.evses:
                if evse.id == self.evse_id:
                    self._attr_native_value = evse.status
        self.async_write_ha_state()
