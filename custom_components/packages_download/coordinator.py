"""DataUpdateCoordinator for Packages Download."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    fetch_npm_downloads_all_periods,
    fetch_npm_packages_by_maintainer,
    fetch_github_releases_downloads,
    fetch_github_repos_by_user,
)
from .const import (
    CONF_PACKAGE_NAME,
    CONF_PACKAGE_TYPE,
    CONF_GITHUB_TOKEN,
    CONF_NPM_PERIODS,
    NPM_PERIODS_DEFAULT,
    PACKAGE_TYPE_NPM,
    PACKAGE_TYPE_GITHUB,
    PACKAGE_TYPE_NPM_USER,
    PACKAGE_TYPE_GITHUB_USER,
)

_LOGGER = logging.getLogger(__name__)


class PackagesDownloadCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to update package data."""

    def __init__(
        self,
        hass: HomeAssistant,
        packages: list[dict],
        scan_interval: int,
        github_token: str | None,
        npm_periods: list[str] | None = None,
    ) -> None:
        """Init coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="packages_download",
            update_interval=__import__("datetime").timedelta(seconds=scan_interval),
        )
        self._packages = packages
        self._github_token = github_token
        self._npm_periods = npm_periods or NPM_PERIODS_DEFAULT
        self._data: dict[str, Any] = {}

    @property
    def package_data(self) -> dict[str, Any]:
        """Data per package (key: type:name)."""
        return self._data

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data from NPM and GitHub."""
        result: dict[str, Any] = {}
        expanded: list[tuple[str, str]] = []  # (type, name)
        session = async_get_clientsession(self.hass)

        for pkg in self._packages:
            ptype = pkg.get(CONF_PACKAGE_TYPE, PACKAGE_TYPE_NPM)
            pname = pkg.get(CONF_PACKAGE_NAME, "")

            if ptype == PACKAGE_TYPE_NPM:
                expanded.append((PACKAGE_TYPE_NPM, pname))
            elif ptype == PACKAGE_TYPE_GITHUB:
                expanded.append((PACKAGE_TYPE_GITHUB, pname))
            elif ptype == PACKAGE_TYPE_NPM_USER:
                packages = await fetch_npm_packages_by_maintainer(session, pname)
                for p in packages:
                    expanded.append((PACKAGE_TYPE_NPM, p))
                _LOGGER.info("npm-user:%s → %d packages", pname, len(packages))
            elif ptype == PACKAGE_TYPE_GITHUB_USER:
                repos = await fetch_github_repos_by_user(
                    session, pname, self._github_token
                )
                for owner, repo in repos:
                    expanded.append((PACKAGE_TYPE_GITHUB, f"{owner}/{repo}"))
                _LOGGER.info("github-user:%s → %d repo", pname, len(repos))

        for ptype, pname in expanded:
            key = f"{ptype}:{pname}"

            if ptype == PACKAGE_TYPE_NPM:
                data = await fetch_npm_downloads_all_periods(
                    session, pname, periods=self._npm_periods
                )
                result[key] = {"type": PACKAGE_TYPE_NPM, "name": pname, "periods": data}
            elif ptype == PACKAGE_TYPE_GITHUB:
                parts = pname.split("/", 1)
                if len(parts) == 2:
                    owner, repo = parts[0].strip(), parts[1].strip()
                    data = await fetch_github_releases_downloads(
                        session, owner, repo, self._github_token
                    )
                    result[key] = {
                        "type": PACKAGE_TYPE_GITHUB,
                        "name": pname,
                        "owner": owner,
                        "repo": repo,
                        "data": data or {},
                    }
                else:
                    result[key] = {"type": PACKAGE_TYPE_GITHUB, "name": pname, "data": {}}

        self._data = result
        return result
