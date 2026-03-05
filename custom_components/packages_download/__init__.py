"""Packages Download integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_PACKAGES,
    CONF_SCAN_INTERVAL,
    CONF_GITHUB_TOKEN,
    CONF_NPM_PERIODS,
    DEFAULT_SCAN_INTERVAL,
    NPM_PERIODS_DEFAULT,
)
from .coordinator import PackagesDownloadCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup from config entry."""
    data = {**entry.data, **entry.options}
    packages = data.get(CONF_PACKAGES, [])
    scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    github_token = data.get(CONF_GITHUB_TOKEN)
    npm_periods = data.get(CONF_NPM_PERIODS, NPM_PERIODS_DEFAULT)

    coordinator = PackagesDownloadCoordinator(
        hass=hass,
        packages=packages,
        scan_interval=scan_interval,
        github_token=github_token,
        npm_periods=npm_periods,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "entry": entry,
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    success = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if success:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return success
