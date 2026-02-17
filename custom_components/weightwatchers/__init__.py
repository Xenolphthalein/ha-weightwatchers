"""The WeightWatchers integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import WeightWatchersApiClient
from .const import CONF_REGION, DOMAIN, PLATFORMS, REGION_TO_DOMAIN
from .coordinator import WeightWatchersDataUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from YAML (not used)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WeightWatchers from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    entry_data = dict(entry.data)
    expected_title = f"WeightWatchers ({entry_data[CONF_USERNAME]})"
    if entry.title != expected_title:
        hass.config_entries.async_update_entry(
            entry,
            data=entry_data,
            title=expected_title,
        )

    session = async_get_clientsession(hass)
    region_domain = REGION_TO_DOMAIN[entry_data[CONF_REGION]]

    api = WeightWatchersApiClient(
        session=session,
        region_domain=region_domain,
        username=entry_data[CONF_USERNAME],
        password=entry_data[CONF_PASSWORD],
    )
    coordinator = WeightWatchersDataUpdateCoordinator(hass, api, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
