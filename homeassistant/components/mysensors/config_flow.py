import logging

from homeassistant.components.mysensors import CONF_DEVICE, NODE_SCHEMA, DEFAULT_BAUD_RATE, DEFAULT_TCP_PORT, \
    CONF_NODE_NAME

from .const import DOMAIN, CONF_PERSISTENCE_FILE, CONF_BAUD_RATE, CONF_TCP_PORT, CONF_TOPIC_IN_PREFIX, \
    CONF_TOPIC_OUT_PREFIX, CONF_NODES
from collections import OrderedDict
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import hashlib

from ... import config_entries
from ...core import callback
from . import CONFIG_SCHEMA, CONF_VERSION, CONF_GATEWAYS, CONF_RETAIN, CONF_PERSISTENCE, CONF_OPTIMISTIC, GATEWAY_SCHEMA, DEFAULT_VERSION

_LOGGER = logging.getLogger(__name__)

class MySensorsConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None, errors=None):
        if user_input is not None:
            gatewayid = hashlib.sha256(user_input[CONF_DEVICE].encode()).hexdigest()[:8]
            await self.async_set_unique_id(gatewayid)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="", data=user_input)

        schema = OrderedDict()
        schema[vol.Optional(CONF_OPTIMISTIC, default=False)] = bool
        schema[vol.Optional(CONF_PERSISTENCE, default=True)] = bool
        schema[vol.Optional(CONF_RETAIN, default=True)] = bool
        schema[vol.Optional(CONF_VERSION, default=DEFAULT_VERSION)] = str

        schema[vol.Required(CONF_DEVICE)] = str
        #schema[vol.Optional(CONF_PERSISTENCE_FILE)] = str
        schema[vol.Optional(CONF_BAUD_RATE, default=DEFAULT_BAUD_RATE)] = cv.positive_int
        schema[vol.Optional(CONF_TCP_PORT, default=DEFAULT_TCP_PORT)] = int
        schema[vol.Optional(CONF_TOPIC_IN_PREFIX)] = str
        schema[vol.Optional(CONF_TOPIC_OUT_PREFIX)] = str

        schema = vol.Schema(schema)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )

