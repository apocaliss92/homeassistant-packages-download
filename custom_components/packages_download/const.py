"""Constants for Packages Download integration."""

DOMAIN = "packages_download"

CONF_NAME = "name"
CONF_PACKAGES = "packages"
CONF_PACKAGE_NAME = "package_name"
CONF_PACKAGE_TYPE = "package_type"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GITHUB_TOKEN = "github_token"
CONF_NPM_PERIODS = "npm_periods"

PACKAGE_TYPE_NPM = "npm"
PACKAGE_TYPE_GITHUB = "github"
PACKAGE_TYPE_NPM_USER = "npm-user"
PACKAGE_TYPE_GITHUB_USER = "github-user"

# Safe defaults for rate limit (NPM ~100 req/min, GitHub 60/h without token)
DEFAULT_SCAN_INTERVAL = 7200  # 2 hours - reduces rate limit risk
MIN_SCAN_INTERVAL = 900  # 15 min minimum
MAX_SCAN_INTERVAL = 86400  # 24 hours maximum

# Limits when monitoring ALL packages of a user
MAX_NPM_PACKAGES_PER_USER = 50  # NPM: 4 req/pkg × 50 = 200 req every 2h
MAX_GITHUB_REPOS_PER_USER = 30  # GitHub: 30 req every 2h < 60/h without token
MAX_GITHUB_REPOS_WITH_TOKEN = 100  # With token: 5000/h

# Delay between API requests to avoid rate limit
REQUEST_DELAY_SECONDS = 0.5

# NPM API
NPM_API_BASE = "https://api.npmjs.org/downloads/point"
NPM_REGISTRY_BASE = "https://registry.npmjs.org"
# Available periods: daily, weekly, monthly, yearly, all-time (NPM max 18 months)
NPM_PERIODS = ["last-day", "last-week", "last-month", "last-year", "last-18months"]
NPM_PERIODS_DEFAULT = ["last-day", "last-week", "last-month", "last-year"]

# GitHub API
GITHUB_API_BASE = "https://api.github.com"

# Sensor attributes
ATTR_DOWNLOADS = "downloads"
ATTR_PERIOD = "period"
ATTR_PACKAGE = "package"
ATTR_LATEST_VERSION = "latest_version"
ATTR_RELEASES_COUNT = "releases_count"
ATTR_ASSETS_COUNT = "assets_count"
