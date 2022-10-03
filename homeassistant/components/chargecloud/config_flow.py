"""Config flow for chargecloud integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import chargecloudapi
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def evse_id(value: str) -> str:
    match = re.fullmatch(
        r"^([A-Z]+)\*([A-Z0-9]+)\*([A-Z0-9]*)(?:\*([A-Z0-9]+))?$", value
    )
    if match is None:
        raise vol.Invalid
    return value


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("evse_id"): evse_id,
        vol.Optional("base_url"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        eid = evse_id(data["evse_id"])
    except vol.Invalid:
        raise InvalidEvseId()

    api = chargecloudapi.Api(
        websession=async_get_clientsession(), base_url=data.get("base_url")
    )
    try:
        locations = await api.location_by_evse_id(data["evse_id"])
    except Exception as e:
        raise CannotConnect(e)

    if len(locations) == 0:
        raise EmptyResponse()

    if locations[0].evses[0].id != data["evse_id"]:
        raise NotFoundException()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for chargecloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidEvseId:
            errors["evse_id"] = "invalid_evse_id"
        except EmptyResponse:
            errors["base"] = "empty_response"
        except NotFoundException:
            errors["base"] = "evse_not_found"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=user_input["evse_id"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class EmptyResponse(HomeAssistantError):
    """Error to indicate we didn't find the evse"""


class InvalidEvseId(HomeAssistantError):
    pass


class NotFoundException(HomeAssistantError):
    pass
