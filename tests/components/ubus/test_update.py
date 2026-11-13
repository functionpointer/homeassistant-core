"""Tests for the OpenWrt (ubus) firmware update entity."""

from typing import Any
from unittest.mock import MagicMock

import aiohttp
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from homeassistant.components.update import DOMAIN as UPDATE_DOMAIN
from homeassistant.components.ubus.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import MOCK_HOST, OVERVIEW_URL, make_overview


def board_version(firmware_board: dict[str, Any], version: str) -> None:
    """Set the installed version the ``system board`` mock reports."""
    firmware_board["release"]["version"] = version


def register_overview(
    aioclient_mock: AiohttpClientMocker, overview: dict[str, Any]
) -> None:
    """Replace the ASU overview with a custom one."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(OVERVIEW_URL, json=overview)


def firmware_entity_id(
    entity_registry: er.EntityRegistry,
) -> str | None:
    """Return the entity id of the firmware update entity."""
    return entity_registry.async_get_entity_id(UPDATE_DOMAIN, DOMAIN, MOCK_HOST)


async def test_update_available(
    hass: HomeAssistant,
    mock_ubus: MagicMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the entity reports an available update with an upgrade link."""
    # Default board is 24.10.5 and the default overview offers 24.10.8.
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = firmware_entity_id(entity_registry)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["installed_version"] == "24.10.5"
    assert state.attributes["latest_version"] == "24.10.8"
    assert state.attributes["title"] == "OpenWrt"
    assert state.attributes["device_class"] == "firmware"
    assert state.attributes["release_url"] is None
    link = f"http://{MOCK_HOST}/cgi-luci/admin/system/attendedsysupgrade"
    assert f"[Attended Sysupgrade page]({link})" in state.attributes[
        "release_summary"
    ]

    entry = entity_registry.async_get(entity_id)
    assert entry is not None
    assert entry.unique_id == MOCK_HOST
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
    assert entry.device_id is not None
    device = device_registry.async_get(entry.device_id)
    assert device is not None
    assert device.identifiers == {(DOMAIN, MOCK_HOST)}


async def test_up_to_date(
    hass: HomeAssistant,
    firmware_board: dict[str, Any],
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the entity is off when the installed version is the newest."""
    board_version(firmware_board, "24.10.8")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(firmware_entity_id(entity_registry))
    assert state is not None
    assert state.state == STATE_OFF
    assert state.attributes["installed_version"] == "24.10.8"
    assert state.attributes["latest_version"] == "24.10.8"
    assert state.attributes["release_summary"] is None


@pytest.mark.parametrize(
    ("installed", "overview", "expected_latest", "expected_state"),
    [
        pytest.param(
            "24.10.5",
            make_overview(**{"25.12": ["25.12.6"], "24.10": ["24.10.8", "24.10.5"]}),
            "24.10.8",
            STATE_ON,
            id="stays_on_same_branch",
        ),
        pytest.param(
            "24.10.8",
            make_overview(**{"25.12": ["25.12.6"], "24.10": ["24.10.8"]}),
            "24.10.8",
            STATE_OFF,
            id="newer_major_is_ignored",
        ),
    ],
)
async def test_branch_aware_latest(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    firmware_board: dict[str, Any],
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    installed: str,
    overview: dict[str, Any],
    expected_latest: str,
    expected_state: str,
) -> None:
    """Test only the newest release of the router's own branch is reported."""
    board_version(firmware_board, installed)
    register_overview(aioclient_mock, overview)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(firmware_entity_id(entity_registry))
    assert state is not None
    assert state.state == expected_state
    assert state.attributes["latest_version"] == expected_latest


async def test_asu_server_unreachable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the entity is unknown when the ASU server cannot be reached."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(OVERVIEW_URL, exc=aiohttp.ClientConnectionError())

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(firmware_entity_id(entity_registry))
    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert state.attributes["installed_version"] == "24.10.5"
    assert state.attributes["latest_version"] is None
    assert state.attributes["release_summary"] is None


@pytest.mark.parametrize(
    "system_board",
    [
        pytest.param({"return_value": None}, id="no_board"),
        pytest.param({"side_effect": ConnectionError}, id="connection_error"),
    ],
)
async def test_setup_retries_when_firmware_unreadable(
    hass: HomeAssistant,
    mock_ubus: MagicMock,
    mock_config_entry: MockConfigEntry,
    system_board: dict,
) -> None:
    """Test setup retries when the installed firmware version cannot be read."""
    mock_ubus.return_value.system_board.configure_mock(**system_board)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
