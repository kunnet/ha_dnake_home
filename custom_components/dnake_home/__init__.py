import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .core.assistant import assistant
from .core.constant import (
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USERNAME,
    CONF_GATEWAY_IP,
    CONF_GATEWAY_MACS,
    CONF_SCAN_INTERVAL,
    DEFAULT_GATEWAY_CHECK_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .core.network import check_host_online, get_arp_table, normalize_mac
from .cover import load_covers, update_covers_state
from .light import load_lights, update_lights_state
from .climate import load_climates, update_climates_state

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.LIGHT, Platform.COVER, Platform.CLIMATE]


def _get_entry_config(entry: ConfigEntry) -> dict:
    """Merge entry.data and entry.options, options take precedence."""
    return {**entry.data, **(entry.options or {})}


def _parse_gateway_macs(config: dict) -> list[str]:
    raw = config.get(CONF_GATEWAY_MACS, [])
    if isinstance(raw, str):
        # backward compat: v1 stored comma-separated string
        items = [m.strip() for m in raw.split(",") if m.strip()]
    elif isinstance(raw, list):
        items = raw
    else:
        return []
    return [normalize_mac(m) for m in items if m]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    config = _get_entry_config(entry)

    gateway_ip = config[CONF_GATEWAY_IP]
    auth_username = config[CONF_AUTH_USERNAME]
    auth_password = config[CONF_AUTH_PASSWORD]
    assistant.bind_auth_info(gateway_ip, auth_username, auth_password)

    macs = _parse_gateway_macs(config)
    if macs:
        resolved_ip = await _async_resolve_gateway(hass, macs)
        if resolved_ip:
            assistant.update_gateway_ip(resolved_ip)

    iot_info = await hass.async_add_executor_job(assistant.query_iot_info)
    if not iot_info:
        _LOGGER.error("query_iot_info fail")
        return False

    assistant.bind_iot_info(iot_info["iot_device_name"], iot_info["gw_iot_name"])

    device_list = await hass.async_add_executor_job(assistant.query_device_list)
    if not device_list:
        _LOGGER.error("query_device_list fail")
        return False

    load_lights(device_list)
    load_covers(device_list)
    load_climates(device_list)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_refresh_states(now=None):
        _LOGGER.info("update all device state")
        states = await hass.async_add_executor_job(assistant.read_all_dev_state)
        if states:
            update_lights_state(states)
            update_covers_state(states)
            update_climates_state(states)

    await _async_refresh_states()

    scan_seconds = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    cancel_refresh = async_track_time_interval(
        hass, _async_refresh_states, timedelta(seconds=scan_seconds)
    )
    entry.async_on_unload(cancel_refresh)

    if macs:

        async def _async_check_gateway(now=None):
            resolved_ip = await _async_resolve_gateway(hass, macs)
            if resolved_ip:
                assistant.update_gateway_ip(resolved_ip)
            else:
                _LOGGER.warning(
                    "No configured gateway MAC is online, keeping current IP: %s",
                    assistant.gw_ip,
                )

        cancel_gw_check = async_track_time_interval(
            hass,
            _async_check_gateway,
            timedelta(seconds=DEFAULT_GATEWAY_CHECK_INTERVAL),
        )
        entry.async_on_unload(cancel_gw_check)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_resolve_gateway(
    hass: HomeAssistant, macs: list[str]
) -> str | None:
    """Walk MACs in order, return IP of the first one that is online."""
    arp_table = await hass.async_add_executor_job(get_arp_table)
    for mac in macs:
        ip = arp_table.get(mac)
        if ip:
            is_online = await hass.async_add_executor_job(check_host_online, ip)
            if is_online:
                _LOGGER.debug("Gateway MAC %s -> IP %s is online", mac, ip)
                return ip
    return None


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Reload integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate config entry from an older version."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version < 2:
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_GATEWAY_MACS, [])
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )
        _LOGGER.info("Migration to version 2 successful")

    return True
