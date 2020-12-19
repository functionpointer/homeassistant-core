import logging

from homeassistant.components.mysensors import CONF_DEVICE, NODE_SCHEMA, DEFAULT_BAUD_RATE, DEFAULT_TCP_PORT, \
    CONF_NODE_NAME

from .const import DOMAIN, CONF_PERSISTENCE_FILE, CONF_BAUD_RATE, CONF_TCP_PORT, CONF_TOPIC_IN_PREFIX, \
    CONF_TOPIC_OUT_PREFIX, CONF_NODES
from collections import OrderedDict
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from ... import config_entries
from ...core import callback
from . import CONFIG_SCHEMA, CONF_VERSION, CONF_GATEWAYS, CONF_RETAIN, CONF_PERSISTENCE, CONF_OPTIMISTIC, GATEWAY_SCHEMA, DEFAULT_VERSION

_LOGGER = logging.getLogger(__name__)

class MySensorsConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        _LOGGER.critical("starting mys config flow")
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        gateway_schema = OrderedDict()
        gateway_schema[vol.Required(CONF_DEVICE)] = str
        gateway_schema[vol.Optional(CONF_PERSISTENCE_FILE)] = str
        gateway_schema[vol.Optional(CONF_BAUD_RATE, default=DEFAULT_BAUD_RATE)] = cv.positive_int
        gateway_schema[vol.Optional(CONF_TCP_PORT, default=DEFAULT_TCP_PORT)]= cv.port
        gateway_schema[vol.Optional(CONF_TOPIC_IN_PREFIX)] = str
        gateway_schema[vol.Optional(CONF_TOPIC_OUT_PREFIX)] = str
        gateway_schema[vol.Optional(CONF_NODES, default={})] = vol.Schema({cv.positive_int: {vol.Required(CONF_NODE_NAME): str}})
        gateway_schema = vol.Schema(gateway_schema)

        schema = OrderedDict()
        schema[vol.Required(CONF_GATEWAYS)] = gateway_schema
        schema[vol.Optional(CONF_OPTIMISTIC, default=False)] = bool
        schema[vol.Optional(CONF_PERSISTENCE, default=True)] = bool
        schema[vol.Optional(CONF_RETAIN, default=True)] = bool
        schema[vol.Optional(CONF_VERSION, default=DEFAULT_VERSION)] = str
        schema = vol.Schema(schema)
        return self.async_show_form(
            step_id="init",
            data_schema=schema
        )

