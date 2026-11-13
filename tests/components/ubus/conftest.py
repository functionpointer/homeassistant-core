"""Fixtures for the OpenWrt (ubus) integration tests."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from homeassistant.components.ubus.const import (
    CONF_DHCP_SOFTWARE,
    DEFAULT_DHCP_SOFTWARE,
    DOMAIN,
)
from homeassistant.components.ubus.update_coordinator import DEFAULT_ASU_SERVER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

MOCK_HOST = "192.168.1.1"

MOCK_CONFIG = {
    CONF_HOST: MOCK_HOST,
    CONF_USERNAME: "root",
    CONF_PASSWORD: "password",
    CONF_DHCP_SOFTWARE: DEFAULT_DHCP_SOFTWARE,
}

MAC_PHONE = "AA:BB:CC:DD:EE:FF"
MAC_LAPTOP = "11:22:33:44:55:66"
MAC_GUEST = "99:88:77:66:55:44"

OVERVIEW_URL = f"{DEFAULT_ASU_SERVER}/api/v1/overview"


def make_overview(**branches: list[str]) -> dict[str, Any]:
    """Build an ASU /api/v1/overview response from branch version lists."""
    return {
        "latest": [next(iter(versions)) for versions in branches.values()],
        "branches": {
            branch: {
                "name": branch,
                "enabled": True,
                "snapshot": branch == "SNAPSHOT",
                "path": "snapshots" if branch == "SNAPSHOT" else "releases/{version}",
                "versions": versions,
            }
            for branch, versions in branches.items()
        },
    }


@pytest.fixture(autouse=True)
def firmware_board() -> dict[str, Any]:
    """Return the ``system board`` response the firmware coordinator reads."""
    return {
        "board_name": "x86/64",
        "hostname": "OpenWrt",
        "release": {
            "distribution": "OpenWrt",
            "version": "24.10.5",
            "revision": "r27252-1e0f0f0f0f",
            "target": "x86/64",
            "description": "OpenWrt 24.10.5",
        },
    }


@pytest.fixture(autouse=True)
def mock_asu_overview(aioclient_mock: AiohttpClientMocker) -> None:
    """Stub the default ASU overview so no test performs a real HTTP request.

    The stubbed branch matches the default installed version, so the firmware
    entity is up to date unless a test overrides it.
    """
    aioclient_mock.get(
        OVERVIEW_URL,
        json=make_overview(**{"24.10": ["24.10.8", "24.10.5", "24.10.0"]}),
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.ubus.async_setup_entry", return_value=None
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def dhcp_software() -> str:
    """Return the DHCP software the mock config entry is created with."""
    return DEFAULT_DHCP_SOFTWARE


@pytest.fixture
def mock_config_entry(dhcp_software: str) -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={**MOCK_CONFIG, CONF_DHCP_SOFTWARE: dhcp_software},
        title=MOCK_HOST,
    )


@pytest.fixture(autouse=True)
def mock_ubus(firmware_board: dict[str, Any]) -> Generator[MagicMock]:
    """Mock the Ubus client with the raw router API responses."""
    with (
        patch("homeassistant.components.ubus.coordinator.Ubus", autospec=True) as mock,
        patch("homeassistant.components.ubus.update_coordinator.py.Ubus", new=mock),
        patch("homeassistant.components.ubus.config_flow.Ubus", new=mock),
    ):
        instance = mock.return_value
        instance.session_id = None

        def _connect() -> str:
            instance.session_id = "session-id"
            return "session-id"

        instance.connect.side_effect = _connect
        instance.get_hostapd.return_value = {"hostapd.wlan0": {}}
        instance.get_hostapd_clients.return_value = {
            "clients": {
                MAC_PHONE: {"authorized": True},
                MAC_LAPTOP: {"authorized": True},
                MAC_GUEST: {"authorized": False},
            }
        }
        instance.system_board.return_value = firmware_board
        instance.get_uci_config.side_effect = _uci_config
        instance.file_read.return_value = {
            "data": (
                "1600000000 aa:bb:cc:dd:ee:ff 192.168.1.10 my-phone *\n"
                "1600000000 11:22:33:44:55:66 192.168.1.11 my-laptop *"
            )
        }
        instance.get_dhcp_method.return_value = {
            "device": {
                "br-lan": {
                    "leases": [
                        {"mac": "aabbccddeeff", "hostname": "my-phone"},
                        {"mac": "112233445566", "hostname": "my-laptop"},
                    ]
                }
            }
        }
        yield mock


def _uci_config(config: str, _type: str) -> dict[str, Any]:
    """Serve the DHCP leasefile config and no custom ASU server URL."""
    if config == "dhcp" and _type == "dnsmasq":
        return {
            "values": {"cfg01": {"leasefile": "/var/dhcp/dnsmasq.leases"}}
        }
    return {"values": {}}
