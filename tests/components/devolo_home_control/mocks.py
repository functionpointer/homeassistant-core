"""Mocks for tests."""

from typing import Any
from unittest.mock import MagicMock

from devolo_home_control_api.devices.zwave import Zwave
from devolo_home_control_api.homecontrol import HomeControl
from devolo_home_control_api.properties.binary_sensor_property import (
    BinarySensorProperty,
)
from devolo_home_control_api.properties.multi_level_sensor_property import (
    MultiLevelSensorProperty,
)
from devolo_home_control_api.properties.multi_level_switch_property import (
    MultiLevelSwitchProperty,
)
from devolo_home_control_api.properties.settings_property import SettingsProperty
from devolo_home_control_api.publisher.publisher import Publisher


class BinarySensorPropertyMock(BinarySensorProperty):
    """devolo Home Control binary sensor mock."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        self._logger = MagicMock()
        self.element_uid = "Test"
        self.key_count = 1
        self.sensor_type = "door"
        self.sub_type = ""
        self.state = False


class MultiLevelSensorPropertyMock(MultiLevelSensorProperty):
    """devolo Home Control multi level sensor mock."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        self.element_uid = "Test"
        self.sensor_type = "temperature"
        self._unit = "°C"
        self._value = 20
        self._logger = MagicMock()


class MultiLevelSwitchPropertyMock(MultiLevelSwitchProperty):
    """devolo Home Control multi level switch mock."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        self.element_uid = "Test"
        self.min = 4
        self.max = 24
        self.switch_type = "temperature"
        self._value = 20
        self._logger = MagicMock()


class SirenPropertyMock(MultiLevelSwitchProperty):
    """devolo Home Control siren mock."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        self.element_uid = "Test"
        self.max = 0
        self.min = 0
        self.switch_type = "tone"
        self._value = 0
        self._logger = MagicMock()


class SettingsMock(SettingsProperty):
    """devolo Home Control settings mock."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        self._logger = MagicMock()
        self.name = "Test"
        self.zone = "Test"
        self.tone = 1


class DeviceMock(Zwave):
    """devolo Home Control device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        self.status = 0
        self.brand = "devolo"
        self.name = "Test Device"
        self.uid = "Test"
        self.settings_property = {"general_device_settings": SettingsMock()}
        self.href = "https://www.mydevolo.com"


class BinarySensorMock(DeviceMock):
    """devolo Home Control binary sensor device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        super().__init__()
        self.binary_sensor_property = {"Test": BinarySensorPropertyMock()}


class BinarySensorMockOverload(DeviceMock):
    """devolo Home Control disabled binary sensor device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        super().__init__()
        self.binary_sensor_property = {"Overload": BinarySensorPropertyMock()}
        self.binary_sensor_property["Overload"].sensor_type = "overload"


class ClimateMock(DeviceMock):
    """devolo Home Control climate device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        super().__init__()
        self.device_model_uid = "devolo.model.Room:Thermostat"
        self.multi_level_switch_property = {"Test": MultiLevelSwitchPropertyMock()}
        self.multi_level_sensor_property = {"Test": MultiLevelSensorPropertyMock()}


class RemoteControlMock(DeviceMock):
    """devolo Home Control remote control device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        super().__init__()
        self.remote_control_property = {"Test": BinarySensorPropertyMock()}


class DisabledBinarySensorMock(DeviceMock):
    """devolo Home Control disabled binary sensor device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        super().__init__()
        self.binary_sensor_property = {
            "devolo.WarningBinaryFI:Test": BinarySensorPropertyMock()
        }


class SirenMock(DeviceMock):
    """devolo Home Control siren device mock."""

    def __init__(self) -> None:
        """Initialize the mock."""
        super().__init__()
        self.device_model_uid = "devolo.model.Siren"
        self.multi_level_switch_property = {
            "devolo.SirenMultiLevelSwitch:Test": SirenPropertyMock()
        }
        self.settings_property["tone"] = SettingsMock()


class HomeControlMock(HomeControl):
    """devolo Home Control gateway mock."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        self.devices = {}
        self.publisher = MagicMock()

    def websocket_disconnect(self, event: str):
        """Mock disconnect of the websocket."""


class HomeControlMockBinarySensor(HomeControlMock):
    """devolo Home Control gateway mock with binary sensor devices."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        super().__init__()
        self.devices = {
            "Test": BinarySensorMock(),
            "Overload": BinarySensorMockOverload(),
        }
        self.publisher = Publisher(self.devices.keys())
        self.publisher.unregister = MagicMock()


class HomeControlMockClimate(HomeControlMock):
    """devolo Home Control gateway mock with climate devices."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        super().__init__()
        self.devices = {
            "Test": ClimateMock(),
        }
        self.publisher = Publisher(self.devices.keys())
        self.publisher.unregister = MagicMock()


class HomeControlMockRemoteControl(HomeControlMock):
    """devolo Home Control gateway mock with remote control device."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        super().__init__()
        self.devices = {"Test": RemoteControlMock()}
        self.publisher = Publisher(self.devices.keys())
        self.publisher.unregister = MagicMock()


class HomeControlMockDisabledBinarySensor(HomeControlMock):
    """devolo Home Control gateway mock with disabled device."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        super().__init__()
        self.devices = {"Test": DisabledBinarySensorMock()}


class HomeControlMockSiren(HomeControlMock):
    """devolo Home Control gateway mock with siren device."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mock."""
        super().__init__()
        self.devices = {"Test": SirenMock()}
        self.publisher = Publisher(self.devices.keys())
        self.publisher.unregister = MagicMock()
