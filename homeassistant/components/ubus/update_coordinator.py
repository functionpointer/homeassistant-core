"""Coordinator reporting the OpenWrt firmware version and available updates.

The installed version comes from the router's ubus ``system board`` call. The
newest available release is fetched from the Attended Sysupgrade (ASU) server's
``/api/v1/overview`` endpoint. That endpoint lists every release branch, so the
branch the router runs (e.g. ``24.10``) is used to pick the newest point release
of the same branch, mirroring the Attended Sysupgrade client.
"""

from dataclasses import dataclass
from datetime import timedelta
from http import HTTPStatus
import logging
from typing import Any, override

import aiohttp
from openwrt.ubus import Ubus

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ASU_LUCI_PATH, DEFAULT_ASU_SERVER, DOMAIN

_LOGGER = logging.getLogger(__name__)

FIRMWARE_CHECK_INTERVAL = timedelta(days=1)
ASU_OVERVIEW_TIMEOUT = aiohttp.ClientTimeout(total=30)

RELEASE_SUMMARY = (
    "A newer release is available for this branch. To install it, open the "
    "router's [Attended Sysupgrade page]({asu_url}) in a browser and run the "
    "upgrade there."
)


@dataclass(frozen=True, slots=True)
class FirmwareData:
    """The installed firmware version and the newest release of its branch."""

    installed: str
    latest: str | None
    release_summary: str | None


def branch_for_version(version: str) -> str:
    """Return the release branch of a version, as the ASU server groups them.

    This mirrors the Attended Sysupgrade client, so ``24.10.5`` maps to the
    ``24.10`` branch and ``21.02-SNAPSHOT`` to ``21.02``.
    """
    return version.replace("-SNAPSHOT", "").split(".")[:2].join(".")


class UbusFirmwareCoordinator(DataUpdateCoordinator[FirmwareData | None]):
    """Report the newest OpenWrt release matching the router's branch."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        A dedicated ubus session is used, as the ubus client is not safe to use
        from multiple threads at once and this coordinator polls on a different
        cadence than the device tracker.
        """
        self.host = config_entry.data[CONF_HOST]
        self.ubus = Ubus(
            f"http://{self.host}/ubus",
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} - firmware - {self.host}",
            update_interval=FIRMWARE_CHECK_INTERVAL,
        )

    @override
    async def _async_update_data(self) -> FirmwareData | None:
        """Return the installed version and the newest release of its branch."""
        board = await self.hass.async_add_executor_job(self._fetch_board)
        installed = board.get("release", {}).get("version")
        if not installed:
            return None
        branch = branch_for_version(installed)
        latest = await self._fetch_latest(branch, installed)
        # Only point users at the upgrade page once a newer release exists.
        release_summary = (
            RELEASE_SUMMARY.format(asu_url=f"http://{self.host}{ASU_LUCI_PATH}")
            if latest and latest != installed
            else None
        )
        return FirmwareData(
            installed=installed, latest=latest, release_summary=release_summary
        )

    def _fetch_board(self) -> dict[str, Any]:
        """Read the board info, re-authenticating once if the session expired."""
        if self.ubus.session_id is None:
            self._login()
        try:
            board = self._system_board()
        except PermissionError:
            # The router dropped our session (e.g. after a reboot); log back in.
            self._login()
        try:
            board = self._system_board()
        except PermissionError as err:
            raise UpdateFailed(f"Access denied by ubus at {self.host}") from err
        return board

    def _system_board(self) -> dict[str, Any]:
        """Return the board info, raising UpdateFailed on a transport failure."""
        try:
            board = self.ubus.system_board()
        except ConnectionError as err:
            raise UpdateFailed(
                f"Error reading board info from ubus at {self.host}"
            ) from err
        if not isinstance(board, dict):
            # The ubus client returns None when the HTTP request fails.
            raise UpdateFailed(f"No board info from ubus at {self.host}")
        return board

    def _login(self) -> None:
        """Open a ubus session, raising UpdateFailed on failure."""
        try:
            session_id = self.ubus.connect()
        except (ConnectionError, PermissionError, TypeError) as err:
            # openwrt-ubus-rpc raises TypeError when the HTTP request itself
            # fails, because it subscripts a None response.
            raise UpdateFailed(f"Error connecting to ubus at {self.host}") from err
        if session_id is None:
            raise UpdateFailed(f"Invalid credentials for ubus at {self.host}")

    async def _fetch_latest(self, branch: str, installed: str) -> str | None:
        """Return the newest release of the branch, or None when unknown.

        A branch without any releases has nothing newer to offer, so the
        installed version is returned and no update is reported.
        """
        overview = await self._fetch_overview()
        if overview is None:
            return None
        versions = overview.get("branches", {}).get(branch, {}).get("versions", [])
        return versions[0] if versions else installed

    async def _asu_server(self) -> str:
        """Return the ASU server base URL, from the router when configured."""
        try:
            result = await self.hass.async_add_executor_job(
                self.ubus.get_uci_config, "attendedsysupgrade", "server"
            )
        except (ConnectionError, TypeError):
            return DEFAULT_ASU_SERVER
        for values in (result or {}).get("values", {}).values():
            if url := values.get("url"):
                return url.rstrip("/")
        return DEFAULT_ASU_SERVER

    async def _fetch_overview(self) -> dict[str, Any] | None:
        """Fetch the ASU release overview, or None when it is unavailable."""
        url = f"{await self._asu_server()}/api/v1/overview"
        session = async_get_clientsession(self.hass)
        try:
            resp = await session.get(url, timeout=ASU_OVERVIEW_TIMEOUT)
            if resp.status != HTTPStatus.OK:
                _LOGGER.debug(
                    "ASU overview at %s returned status %s", url, resp.status
                )
                return None
            data = await resp.json()
        except (aiohttp.ClientError, ValueError) as err:
            _LOGGER.debug("Could not read ASU overview at %s: %s", url, err)
            return None
        return data if isinstance(data, dict) else None
