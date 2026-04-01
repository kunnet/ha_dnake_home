import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .core.constant import (
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USERNAME,
    CONF_GATEWAY_IP,
    CONF_GATEWAY_MACS,
    CONF_SCAN_INTERVAL,
    DEFAULT_AUTH_PASSWORD,
    DEFAULT_AUTH_USERNAME,
    DEFAULT_GATEWAY_IP,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TITLE,
)
from .core.network import get_arp_table

_LOGGER = logging.getLogger(__name__)


def _build_schema(defaults: dict, arp_table: dict[str, str]) -> vol.Schema:
    mac_options = [
        SelectOptionDict(value=mac, label=f"{mac} ({ip})")
        for mac, ip in arp_table.items()
    ]
    return vol.Schema(
        {
            vol.Required(
                CONF_GATEWAY_IP,
                default=defaults.get(CONF_GATEWAY_IP, DEFAULT_GATEWAY_IP),
            ): str,
            vol.Required(
                CONF_AUTH_USERNAME,
                default=defaults.get(CONF_AUTH_USERNAME, DEFAULT_AUTH_USERNAME),
            ): str,
            vol.Required(
                CONF_AUTH_PASSWORD,
                default=defaults.get(CONF_AUTH_PASSWORD, DEFAULT_AUTH_PASSWORD),
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): int,
            vol.Optional(
                CONF_GATEWAY_MACS,
                default=defaults.get(CONF_GATEWAY_MACS, []),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=mac_options,
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class DNakeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=TITLE, data=user_input)

        arp_table = await self.hass.async_add_executor_job(get_arp_table)
        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}, arp_table),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DNakeOptionsFlow(config_entry)


class DNakeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **(self._config_entry.options or {})}
        arp_table = await self.hass.async_add_executor_job(get_arp_table)
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current, arp_table),
        )
