# Packages Download

Custom component for Home Assistant that generates sensors to monitor **NPM** package downloads and **GitHub** release downloads.

## Features

- **NPM**: sensors for each package with downloads for last day, week, month and year
- **GitHub**: sensor for total downloads of release assets (e.g. .zip, .tar.gz files)
- **User monitoring**: monitor **all** packages of an NPM or GitHub user with a single entry

## Installation

### HACS (recommended)

1. Open HACS → Integrations
2. Click the three dots → Custom repositories
3. Add: `https://github.com/apocaliss92/homeassistant-packages-download`
4. Search for "Packages Download" and install
5. Restart Home Assistant

### Manual

Copy the `custom_components/packages_download` folder to the `custom_components` folder of your Home Assistant installation.

## Configuration

1. Go to **Settings** → **Devices & services** → **Add integration**
2. Search for "Packages Download"
3. Fill in:
   - **Name**: instance name (e.g. "My packages")
   - **Packages**: add via UI, one per entry:
     - `npm:package-name` for NPM (e.g. `npm:lodash`, `npm:@angular/core`)
     - `github:owner/repo` for GitHub (e.g. `github:home-assistant/core`)
     - `npm-user:USERNAME` for **all** NPM packages of a maintainer (max 50)
     - `github-user:USERNAME` for **all** GitHub repos of a user (max 30 without token, 100 with token)
   - **NPM periods**: select which periods to track (daily, weekly, monthly, yearly, all-time)
   - **Update interval**: seconds between updates (default: **7200** = 2 hours, for rate limit safety)
   - **GitHub token** (optional): to increase API rate limits and number of monitorable repos

### Example packages

```
npm:lodash
npm:axios
github:home-assistant/core
npm-user:sindresorhus
github-user:esphome
```

## Generated sensors

### NPM

For each NPM package, sensors are created based on selected periods:

- **Daily** – last 24 hours
- **Weekly** – last 7 days
- **Monthly** – last 30 days
- **Yearly** – last 365 days
- **All time** – last 18 months (NPM API limit)

### GitHub

For each GitHub repo, 1 sensor is created with total downloads of release assets.

Attributes: `latest_version`, `releases_count`, `assets_count`

## Safe defaults for rate limit

To avoid exceeding API limits, the integration uses safe defaults:

| Setting | Default | Notes |
|---------|---------|-------|
| Update interval | 7200 s (2 hours) | Min 900 s, max 86400 s |
| npm-user | max 50 packages | ~200 NPM requests every 2h |
| github-user without token | max 30 repos | < 60 req/h GitHub limit |
| github-user with token | max 100 repos | 5000 req/h with token |
| Delay between requests | 0.5 s | Reduces rate limit risk |

## Notes

- **GitHub**: downloads are from release assets (files attached to releases). Container Registry (ghcr.io) pulls are not included, as GitHub does not expose a public API for them.
- **NPM**: uses official API `api.npmjs.org`. Maintainer search uses `registry.npmjs.org/-/v1/search`.
- **npm-user**: lists packages via maintainer search; may not include all if user has many packages.
- **github-user**: lists user's public repos and fetches release downloads for each.

## Versioning

The integration uses **semantic versioning** (e.g. `0.1.0`) from `manifest.json`. HACS installs from GitHub releases only (not from the default branch), so updates are always version-based. To release a new version:

1. Update `version` in `custom_components/packages_download/manifest.json`
2. Push to `main` — the CI workflow creates the tag and GitHub release automatically

## License

MIT
