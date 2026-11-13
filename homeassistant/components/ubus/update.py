"""Support for reporting OpenWrt firmware updates."""

from typing import override

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import UBUS_KEY
from .const import DOMAIN
from .coordinator import UbusConfigEntry
from .update_coordinator import UbusFirmwareCoordinator

DESCRIPTION = UpdateEntityDescription(
    key="firmware",
    device_class=UpdateDeviceClass.FIRMWARE,
    has_entity_name=True,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UbusConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the firmware update entity for a ubus config entry."""

    releases = hass.data[UBUS_KEY]
    if (releases_coordinator := releases.get(repo)) is None:
        releases_coordinator = releases[repo] = WLEDReleasesDataUpdateCoordinator(
            hass, repo
        )
        await releases_coordinator.async_request_refresh()

    async_add_entities([UbusFirmwareUpdateEntity(config_entry.runtime_data[1])])


class UbusFirmwareUpdateEntity(
    CoordinatorEntity[UbusFirmwareCoordinator], UpdateEntity
):
    """Report an available OpenWrt firmware update for the router.

    The update is installed on the router itself, through the web Attended
    Sysupgrade page linked from the release notes, so this entity only reports
    that an update exists and never installs it.
    """

    entity_description = DESCRIPTION
    _attr_title = "OpenWrt"

    def __init__(self, coordinator: UbusFirmwareCoordinator) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.host
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)}
        )

    @property
    @override
    def installed_version(self) -> str | None:
        """Version installed on the router."""
        data = self.coordinator.data
        return data.installed if data else None

    @property
    @override
    def latest_version(self) -> str | None:
        """Newest release of the router's branch, or the installed version."""
        data = self.coordinator.data
        return data.latest if data else None

    @property
    @override
    def release_summary(self) -> str | None:
        """Point to the web upgrade page when an update is available."""
        data = self.coordinator.data
        return data.release_summary if data else None
