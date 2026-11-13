"""The OpenWrt (ubus) integration."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import AnyDeviceEntry

from .coordinator import UbusConfigEntry, UbusDataUpdateCoordinator
from .update_coordinator import UbusFirmwareCoordinator

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.UPDATE]


UBUS_KEY: HassKey[dict[str, UbusReleasesDataUpdateCoordinator]] = HassKey(DOMAIN)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the UBUS integration.

    Releases are fetched by one coordinator, shared
    across all OpenWrt config entries using it, to avoid fetching
    the same data multiple times for each.
    """
    hass.data[UBUS_KEY] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: UbusConfigEntry) -> None:
    """Set up ubus from a config entry."""
    coordinator = UbusDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    firmware_coordinator = UbusFirmwareCoordinator(hass, entry)
    await firmware_coordinator.async_config_entry_first_refresh()
    entry.runtime_data.update_coordinator = coordinator
    entry.runtime_data.firmware_coordinator = firmware_coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: UbusConfigEntry) -> None:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: UbusConfigEntry, device_entry: AnyDeviceEntry
) -> bool:
    """Allow removing a client device which is not currently connected."""
    if not isinstance(device_entry, dr.DeviceEntry):
        # This integration does not create child devices.
        return False
    if config_entry.state is not ConfigEntryState.LOADED:
        return True
    connected = {dr.format_mac(mac) for mac in config_entry.runtime_data.update_coordinator.data}
    return not any(
        connection in connected
        for connection_type, connection in device_entry.connections
        if connection_type == dr.CONNECTION_NETWORK_MAC
    )
