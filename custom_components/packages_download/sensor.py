"""Sensors for Packages Download."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    CONF_NAME,
    PACKAGE_TYPE_NPM,
    PACKAGE_TYPE_GITHUB,
    ATTR_PERIOD,
    ATTR_PACKAGE,
    ATTR_LATEST_VERSION,
    ATTR_RELEASES_COUNT,
    ATTR_ASSETS_COUNT,
)
from .coordinator import PackagesDownloadCoordinator

PERIOD_LABELS = {
    "last-day": "Daily",
    "last-week": "Weekly",
    "last-month": "Monthly",
    "last-year": "Yearly",
    "last-18months": "All time",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from config entry."""
    coordinator: PackagesDownloadCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data.get(CONF_NAME, "Packages")
    entities: list[PackagesDownloadSensor] = []

    for key, pkg_data in coordinator.package_data.items():
        ptype = pkg_data.get("type", "")
        pname = pkg_data.get("name", "").replace("/", "_")
        base_id = slugify(f"{name}_{ptype}_{pname}")

        if ptype == PACKAGE_TYPE_NPM:
            periods = pkg_data.get("periods", {})
            for period in periods:
                entities.append(
                    NpmDownloadSensor(
                        coordinator=coordinator,
                        package_key=key,
                        period=period,
                        entity_id_suffix=f"{base_id}_{period.replace('-', '_')}",
                    )
                )
        elif ptype == PACKAGE_TYPE_GITHUB:
            entities.append(
                GitHubDownloadSensor(
                    coordinator=coordinator,
                    package_key=key,
                    entity_id_suffix=base_id,
                )
            )

    async_add_entities(entities)


class PackagesDownloadSensor(CoordinatorEntity[PackagesDownloadCoordinator], SensorEntity):
    """Base sensor for package downloads."""

    _attr_icon = "mdi:download"
    _attr_native_unit_of_measurement = "downloads"

    def __init__(
        self,
        coordinator: PackagesDownloadCoordinator,
        package_key: str,
        entity_id_suffix: str,
    ) -> None:
        """Init."""
        super().__init__(coordinator)
        self._package_key = package_key
        self._entity_id_suffix = entity_id_suffix
        self._attr_unique_id = f"packages_download_{entity_id_suffix}"

    @property
    def package_data(self) -> dict:
        """Package data from coordinator."""
        return self.coordinator.package_data.get(self._package_key, {})


class NpmDownloadSensor(PackagesDownloadSensor):
    """Sensor for NPM downloads."""

    def __init__(
        self,
        coordinator: PackagesDownloadCoordinator,
        package_key: str,
        period: str,
        entity_id_suffix: str,
    ) -> None:
        """Init."""
        super().__init__(coordinator, package_key, entity_id_suffix)
        self._period = period
        pname = self.package_data.get("name", package_key)
        self._attr_name = f"NPM {pname} ({PERIOD_LABELS.get(period, period)})"

    @property
    def native_value(self) -> int | None:
        """Download value for the period."""
        periods = self.package_data.get("periods", {})
        return periods.get(self._period)

    @property
    def extra_state_attributes(self) -> dict:
        """Extra attributes."""
        return {
            ATTR_PACKAGE: self.package_data.get("name", ""),
            ATTR_PERIOD: self._period,
        }


class GitHubDownloadSensor(PackagesDownloadSensor):
    """Sensor for GitHub Releases downloads."""

    _attr_name = None

    def __init__(
        self,
        coordinator: PackagesDownloadCoordinator,
        package_key: str,
        entity_id_suffix: str,
    ) -> None:
        """Init."""
        super().__init__(coordinator, package_key, entity_id_suffix)
        pname = self.package_data.get("name", package_key)
        self._attr_name = f"GitHub {pname}"

    @property
    def native_value(self) -> int | None:
        """Total downloads from release assets."""
        data = self.package_data.get("data", {})
        return data.get("downloads")

    @property
    def extra_state_attributes(self) -> dict:
        """Extra attributes."""
        data = self.package_data.get("data", {})
        return {
            ATTR_PACKAGE: self.package_data.get("name", ""),
            ATTR_LATEST_VERSION: data.get("latest_version", ""),
            ATTR_RELEASES_COUNT: data.get("releases_count", 0),
            ATTR_ASSETS_COUNT: data.get("assets_count", 0),
        }
