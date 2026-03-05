"""API client for NPM and GitHub."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import (
    NPM_API_BASE,
    NPM_REGISTRY_BASE,
    NPM_PERIODS_DEFAULT,
    GITHUB_API_BASE,
    PACKAGE_TYPE_NPM,
    PACKAGE_TYPE_GITHUB,
    REQUEST_DELAY_SECONDS,
    MAX_NPM_PACKAGES_PER_USER,
    MAX_GITHUB_REPOS_PER_USER,
    MAX_GITHUB_REPOS_WITH_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


async def _delay() -> None:
    """Delay between requests to respect rate limit."""
    await asyncio.sleep(REQUEST_DELAY_SECONDS)


def _npm_period_to_api(period: str) -> str:
    """Convert period key to NPM API format. last-18months uses date range."""
    if period == "last-18months":
        end = datetime.utcnow().date()
        start = end - timedelta(days=548)  # ~18 months
        return f"{start}:{end}"
    return period


async def _fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    max_retries: int = 2,
) -> dict[str, Any] | None:
    """Fetch URL with retry on connection/DNS errors."""
    for attempt in range(max_retries + 1):
        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 429:
                    _LOGGER.warning("Rate limit reached for %s", url)
                    return None
                if resp.status != 200:
                    return None
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            if attempt < max_retries:
                await asyncio.sleep(2**attempt)
            else:
                _LOGGER.warning(
                    "Cannot connect to %s (DNS/network error): %s. "
                    "Check Settings → System → Network → DNS servers.",
                    url.split("/")[2] if "/" in url else url,
                    e,
                )
                return None
    return None


async def fetch_npm_downloads(
    session: aiohttp.ClientSession,
    package: str,
    period: str,
) -> dict[str, Any] | None:
    """Fetch NPM downloads for a package and period."""
    api_period = _npm_period_to_api(period)
    url = f"{NPM_API_BASE}/{api_period}/{package}"
    data = await _fetch_with_retry(session, url)
    if data is None:
        _LOGGER.debug("NPM fetch failed for %s (period %s)", package, period)
    return data


async def fetch_npm_downloads_all_periods(
    session: aiohttp.ClientSession,
    package: str,
    periods: list[str] | None = None,
    add_delay: bool = True,
) -> dict[str, int]:
    """Fetch NPM downloads for specified periods."""
    periods = periods or NPM_PERIODS_DEFAULT
    result: dict[str, int] = {}
    for period in periods:
        if add_delay:
            await _delay()
        data = await fetch_npm_downloads(session, package, period)
        if data and "downloads" in data:
            result[period] = data["downloads"]
        else:
            result[period] = 0
    return result


async def fetch_npm_packages_by_maintainer(
    session: aiohttp.ClientSession,
    username: str,
) -> list[str]:
    """Fetch NPM packages list by maintainer (max MAX_NPM_PACKAGES_PER_USER)."""
    await _delay()
    url = f"{NPM_REGISTRY_BASE}/-/v1/search"
    params = {"text": f"maintainer:{username}", "size": MAX_NPM_PACKAGES_PER_USER}
    data = await _fetch_with_retry(session, url, params=params)
    if data is None:
        return []

    packages = []
    for obj in data.get("objects", []):
        pkg_name = obj.get("package", {}).get("name")
        if pkg_name:
            packages.append(pkg_name)
    return packages[:MAX_NPM_PACKAGES_PER_USER]


async def fetch_github_releases_downloads(
    session: aiohttp.ClientSession,
    owner: str,
    repo: str,
    token: str | None = None,
) -> dict[str, Any] | None:
    """Fetch total downloads from GitHub releases (assets)."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        await _delay()
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 403 and "rate limit" in (await resp.text()).lower():
                _LOGGER.warning("GitHub rate limit reached")
                return None
            if resp.status == 404:
                _LOGGER.warning("Repo %s/%s not found", owner, repo)
                return None
            if resp.status != 200:
                _LOGGER.warning("GitHub API %s: %s", url, resp.status)
                return None
            releases = await resp.json()
    except Exception as e:
        _LOGGER.warning("GitHub error %s/%s: %s", owner, repo, e)
        return None

    total_downloads = 0
    releases_count = 0
    assets_count = 0
    latest_version = None

    for release in releases:
        if release.get("draft"):
            continue
        releases_count += 1
        if latest_version is None:
            latest_version = release.get("tag_name") or release.get("name", "")
        for asset in release.get("assets", []):
            assets_count += 1
            total_downloads += asset.get("download_count", 0)

    return {
        "downloads": total_downloads,
        "releases_count": releases_count,
        "assets_count": assets_count,
        "latest_version": latest_version or "",
    }


async def fetch_github_repos_by_user(
    session: aiohttp.ClientSession,
    username: str,
    token: str | None = None,
) -> list[tuple[str, str]]:
    """Fetch GitHub repos list for a user (owner, repo)."""
    max_repos = MAX_GITHUB_REPOS_WITH_TOKEN if token else MAX_GITHUB_REPOS_PER_USER
    url = f"{GITHUB_API_BASE}/users/{username}/repos"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    all_repos: list[tuple[str, str]] = []
    page = 1
    per_page = min(100, max_repos)

    while len(all_repos) < max_repos:
        try:
            await _delay()
            async with session.get(
                url,
                headers=headers,
                params={"per_page": per_page, "page": page, "type": "owner"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 403:
                    _LOGGER.warning("GitHub rate limit or access denied")
                    break
                if resp.status != 200:
                    _LOGGER.warning("GitHub API %s: %s", url, resp.status)
                    break
                repos = await resp.json()
        except Exception as e:
            _LOGGER.warning("GitHub user error %s: %s", username, e)
            break

        if not repos:
            break

        for repo in repos:
            if len(all_repos) >= max_repos:
                break
            owner = repo.get("owner", {}).get("login", username)
            name = repo.get("name")
            if name:
                all_repos.append((owner, name))

        if len(repos) < per_page:
            break
        page += 1

    return all_repos[:max_repos]
