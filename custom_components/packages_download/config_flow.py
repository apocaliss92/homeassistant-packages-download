"""Config flow for Packages Download - UI configuration."""

from __future__ import annotations

import re
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_PACKAGES,
    CONF_PACKAGE_NAME,
    CONF_PACKAGE_TYPE,
    CONF_SCAN_INTERVAL,
    CONF_GITHUB_TOKEN,
    CONF_NPM_PERIODS,
    PACKAGE_TYPE_NPM,
    PACKAGE_TYPE_GITHUB,
    PACKAGE_TYPE_NPM_USER,
    PACKAGE_TYPE_GITHUB_USER,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    NPM_PERIODS,
    NPM_PERIODS,
    NPM_PERIODS_DEFAULT,
)

VALID_TYPES = (PACKAGE_TYPE_NPM, PACKAGE_TYPE_GITHUB, PACKAGE_TYPE_NPM_USER, PACKAGE_TYPE_GITHUB_USER)

NPM_PERIOD_OPTIONS = [
    {"value": "last-day", "label": "Daily"},
    {"value": "last-week", "label": "Weekly"},
    {"value": "last-month", "label": "Monthly"},
    {"value": "last-year", "label": "Yearly"},
    {"value": "last-18months", "label": "All time (18 months)"},
]

PACKAGE_TYPE_OPTIONS = [
    {"value": PACKAGE_TYPE_NPM, "label": "NPM package (e.g. lodash)"},
    {"value": PACKAGE_TYPE_GITHUB, "label": "GitHub repo (e.g. owner/repo)"},
    {"value": PACKAGE_TYPE_NPM_USER, "label": "NPM - all packages of a user"},
    {"value": PACKAGE_TYPE_GITHUB_USER, "label": "GitHub - all repos of a user"},
]


def _validate_npm(name: str) -> bool:
    """Validate NPM package name (scoped or simple)."""
    if not name or len(name) > 214:
        return False
    if name.startswith("@"):
        parts = name[1:].split("/", 1)
        return len(parts) == 2 and all(
            re.match(r"^[a-z0-9][a-z0-9._-]*$", p, re.I) for p in parts
        )
    return bool(re.match(r"^[a-z0-9][a-z0-9._-]*$", name, re.I))


def _validate_github(name: str) -> bool:
    """Validate GitHub owner/repo."""
    if not name or "/" not in name:
        return False
    parts = name.split("/", 1)
    return len(parts) == 2 and all(p.strip() for p in parts)


def _validate_username(name: str) -> bool:
    """Validate username (for npm-user and github-user)."""
    if not name or len(name) > 39:
        return False
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", name))


def _validate_package(ptype: str, pname: str) -> str | None:
    """Return error key if invalid."""
    if ptype == PACKAGE_TYPE_NPM and not _validate_npm(pname):
        return "invalid_npm"
    if ptype == PACKAGE_TYPE_GITHUB and not _validate_github(pname):
        return "invalid_github"
    if ptype == PACKAGE_TYPE_NPM_USER and not _validate_username(pname):
        return "invalid_username"
    if ptype == PACKAGE_TYPE_GITHUB_USER and not _validate_username(pname):
        return "invalid_username"
    return None


class PackagesDownloadConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Packages Download."""

    VERSION = 1

    def __init__(self) -> None:
        """Init."""
        self._packages: list[dict] = []
        self._name: str = ""
        self._scan_interval: int = DEFAULT_SCAN_INTERVAL
        self._github_token: str | None = None
        self._npm_periods: list[str] = list(NPM_PERIODS_DEFAULT)

    async def async_step_user(self, user_input=None):
        """Step 1: Name and base settings."""
        errors = {}
        if user_input is not None:
            self._name = (user_input.get(CONF_NAME) or "").strip()
            self._scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            self._github_token = (user_input.get(CONF_GITHUB_TOKEN) or "").strip() or None
            raw_periods = user_input.get(CONF_NPM_PERIODS, NPM_PERIODS_DEFAULT)
            self._npm_periods = raw_periods if isinstance(raw_periods, list) else list(NPM_PERIODS_DEFAULT)
            if not self._npm_periods:
                self._npm_periods = list(NPM_PERIODS_DEFAULT)

            if not self._name:
                errors["base"] = "name_required"
            else:
                return await self.async_step_add_package()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self._name or ""): cv.string,
                    vol.Optional(
                        CONF_NPM_PERIODS,
                        default=self._npm_periods,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=NPM_PERIOD_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    ),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._scan_interval,
                    ): NumberSelector(NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=300, unit_of_measurement="s")),
                    vol.Optional(CONF_GITHUB_TOKEN, default=self._github_token or ""): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_add_package(self, user_input=None):
        """Step 2: Add a package."""
        errors = {}
        if user_input is not None:
            ptype = user_input.get(CONF_PACKAGE_TYPE, PACKAGE_TYPE_NPM)
            if isinstance(ptype, list):
                ptype = ptype[0] if ptype else PACKAGE_TYPE_NPM
            pname = (user_input.get(CONF_PACKAGE_NAME) or "").strip()

            err = _validate_package(ptype, pname)
            if err:
                errors["base"] = err
            else:
                self._packages.append({CONF_PACKAGE_TYPE: ptype, CONF_PACKAGE_NAME: pname})
                return await self.async_step_packages()

        return self.async_show_form(
            step_id="add_package",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PACKAGE_TYPE, default=PACKAGE_TYPE_NPM): SelectSelector(
                        SelectSelectorConfig(
                            options=PACKAGE_TYPE_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_PACKAGE_NAME, default=""): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_packages(self, user_input=None):
        """Step 3: Packages summary - add more or confirm."""
        if user_input is not None:
            action = user_input.get("action", "finish")
            if isinstance(action, list):
                action = action[0] if action else "finish"
            if action == "add":
                return await self.async_step_add_package()
            if action == "remove":
                return await self.async_step_remove_package()
            # finish - require at least one package
            if not self._packages:
                return await self.async_step_add_package()
            unique_id = f"packages_download_{self._name}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_NAME: self._name,
                    CONF_PACKAGES: self._packages,
                    CONF_SCAN_INTERVAL: self._scan_interval,
                    CONF_GITHUB_TOKEN: self._github_token,
                    CONF_NPM_PERIODS: self._npm_periods,
                },
            )

        # Build list description
        if self._packages:
            pkg_list = "\n".join(
                f"• {p[CONF_PACKAGE_TYPE]}: {p[CONF_PACKAGE_NAME]}" for p in self._packages
            )
        else:
            pkg_list = "—"

        options = [
            {"value": "add", "label": "Add another package"},
            {"value": "finish", "label": "Confirm and finish"},
        ]
        if self._packages:
            options.insert(1, {"value": "remove", "label": "Remove package"})

        return self.async_show_form(
            step_id="packages",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="finish"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={"packages_list": pkg_list, "count": str(len(self._packages))},
        )

    async def async_step_remove_package(self, user_input=None):
        """Remove a package from the list (config flow)."""
        if user_input is not None:
            idx = user_input.get("package_index")
            if isinstance(idx, list):
                idx = int(idx[0]) if idx else -1
            else:
                idx = int(idx) if idx is not None else -1
            if 0 <= idx < len(self._packages):
                self._packages.pop(idx)
            return await self.async_step_packages()

        options = [
            {"value": str(i), "label": f"{p[CONF_PACKAGE_TYPE]}: {p[CONF_PACKAGE_NAME]}"}
            for i, p in enumerate(self._packages)
        ]
        return self.async_show_form(
            step_id="remove_package",
            data_schema=vol.Schema(
                {
                    vol.Required("package_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Options flow."""
        return PackagesDownloadOptionsFlow()


class PackagesDownloadOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Packages Download - UI configuration."""

    def __init__(self) -> None:
        """Init. config_entry is provided by OptionsFlow base class (HA 2025.12+)."""
        data = {**self.config_entry.data, **self.config_entry.options}
        self._packages: list[dict] = list(data.get(CONF_PACKAGES, []))
        self._name: str = data.get(CONF_NAME, "")
        self._scan_interval: int = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._github_token: str | None = data.get(CONF_GITHUB_TOKEN) or None
        self._npm_periods: list[str] = list(data.get(CONF_NPM_PERIODS, NPM_PERIODS_DEFAULT))
        if not self._npm_periods:
            self._npm_periods = list(NPM_PERIODS_DEFAULT)

    async def async_step_init(self, user_input=None):
        """Initial options step - choose action."""
        if user_input is not None:
            action = user_input.get("action", "edit")
            if isinstance(action, list):
                action = action[0] if action else "edit"
            if action == "packages":
                return await self.async_step_packages()
            return await self.async_step_edit()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="edit"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "edit", "label": "Edit general settings"},
                                {"value": "packages", "label": "Manage packages"},
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_edit(self, user_input=None):
        """Edit name, interval, token, periods."""
        errors = {}
        if user_input is not None:
            self._name = (user_input.get(CONF_NAME) or "").strip()
            self._scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            self._github_token = (user_input.get(CONF_GITHUB_TOKEN) or "").strip() or None
            raw_periods = user_input.get(CONF_NPM_PERIODS, NPM_PERIODS_DEFAULT)
            self._npm_periods = raw_periods if isinstance(raw_periods, list) else list(NPM_PERIODS_DEFAULT)
            if not self._npm_periods:
                self._npm_periods = list(NPM_PERIODS_DEFAULT)
            if not self._name:
                errors["base"] = "name_required"
            else:
                return await self._async_save_and_show_init()

        return self.async_show_form(
            step_id="edit",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self._name): cv.string,
                    vol.Optional(
                        CONF_NPM_PERIODS,
                        default=self._npm_periods,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=NPM_PERIOD_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    ),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._scan_interval,
                    ): NumberSelector(NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=300, unit_of_measurement="s")),
                    vol.Optional(CONF_GITHUB_TOKEN, default=self._github_token or ""): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_packages(self, user_input=None):
        """Manage packages - add, remove or confirm."""
        if user_input is not None:
            action = user_input.get("action", "finish")
            if isinstance(action, list):
                action = action[0] if action else "finish"
            if action == "add":
                return await self.async_step_add_package()
            if action == "remove":
                return await self.async_step_remove_package()
            return await self._async_save_and_show_init()

        pkg_list = "\n".join(
            f"• {p[CONF_PACKAGE_TYPE]}: {p[CONF_PACKAGE_NAME]}" for p in self._packages
        ) if self._packages else "—"

        options = [{"value": "add", "label": "Add package"}, {"value": "finish", "label": "Confirm"}]
        if self._packages:
            options.insert(1, {"value": "remove", "label": "Remove package"})

        return self.async_show_form(
            step_id="packages",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="finish"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={"packages_list": pkg_list, "count": str(len(self._packages))},
        )

    async def async_step_add_package(self, user_input=None):
        """Add package."""
        errors = {}
        if user_input is not None:
            ptype = user_input.get(CONF_PACKAGE_TYPE, PACKAGE_TYPE_NPM)
            if isinstance(ptype, list):
                ptype = ptype[0] if ptype else PACKAGE_TYPE_NPM
            pname = (user_input.get(CONF_PACKAGE_NAME) or "").strip()
            err = _validate_package(ptype, pname)
            if err:
                errors["base"] = err
            else:
                self._packages.append({CONF_PACKAGE_TYPE: ptype, CONF_PACKAGE_NAME: pname})
                return await self.async_step_packages()

        return self.async_show_form(
            step_id="add_package",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PACKAGE_TYPE, default=PACKAGE_TYPE_NPM): SelectSelector(
                        SelectSelectorConfig(
                            options=PACKAGE_TYPE_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_PACKAGE_NAME, default=""): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_remove_package(self, user_input=None):
        """Remove a package from the list."""
        if user_input is not None:
            idx = user_input.get("package_index")
            if isinstance(idx, list):
                idx = int(idx[0]) if idx else -1
            else:
                idx = int(idx) if idx is not None else -1
            if 0 <= idx < len(self._packages):
                self._packages.pop(idx)
            return await self.async_step_packages()

        options = [
            {"value": str(i), "label": f"{p[CONF_PACKAGE_TYPE]}: {p[CONF_PACKAGE_NAME]}"}
            for i, p in enumerate(self._packages)
        ]
        return self.async_show_form(
            step_id="remove_package",
            data_schema=vol.Schema(
                {
                    vol.Required("package_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def _async_save_and_show_init(self):
        """Save and return to initial menu."""
        return self.async_create_entry(
            title="",
            data={
                CONF_NAME: self._name,
                CONF_PACKAGES: self._packages,
                CONF_SCAN_INTERVAL: self._scan_interval,
                CONF_GITHUB_TOKEN: self._github_token,
                CONF_NPM_PERIODS: self._npm_periods,
            },
        )
