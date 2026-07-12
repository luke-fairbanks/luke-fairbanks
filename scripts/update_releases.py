#!/usr/bin/env python3
"""Refresh the plain-Markdown release log in the profile README."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


OWNER = "luke-fairbanks"
GITHUB_REPOSITORIES = {
    "harbor-mcp": "Harbor",
    "BatteryHog": "Battery Hog",
}
NPM_PACKAGES = {
    "broll-mcp": "broll-mcp",
}
START_MARKER = "<!-- releases:start -->"
END_MARKER = "<!-- releases:end -->"
MAX_ITEMS = 4


def fetch_json(url: str, token: str | None = None) -> dict | list | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "luke-fairbanks-profile-release-log",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def github_release_items(token: str | None) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for repository, label in GITHUB_REPOSITORIES.items():
        release = fetch_json(
            f"https://api.github.com/repos/{OWNER}/{repository}/releases/latest",
            token,
        )
        if not isinstance(release, dict):
            continue
        items.append(
            {
                "title": str(release.get("name") or f"{label} {release['tag_name']}"),
                "url": str(release["html_url"]),
                "published_at": str(release["published_at"]),
            }
        )
    return items


def npm_release_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for package, label in NPM_PACKAGES.items():
        encoded = urllib.parse.quote(package, safe="@")
        metadata = fetch_json(f"https://registry.npmjs.org/{encoded}")
        if not isinstance(metadata, dict):
            continue
        version = str(metadata["dist-tags"]["latest"])
        published_at = str(metadata["time"][version])
        items.append(
            {
                "title": f"{label} v{version}",
                "url": f"https://www.npmjs.com/package/{encoded}/v/{version}",
                "published_at": published_at,
            }
        )
    return items


def format_date(timestamp: str) -> str:
    instant = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return f"{instant.strftime('%B')} {instant.day}, {instant.year}"


def render_release_log(items: list[dict[str, str]]) -> str:
    ordered = sorted(items, key=lambda item: item["published_at"], reverse=True)
    lines = [
        f"- [{item['title']}]({item['url']}) — {format_date(item['published_at'])}"
        for item in ordered[:MAX_ITEMS]
    ]
    if not lines:
        lines.append("- No public releases yet.")
    return "\n".join(lines)


def replace_release_log(readme: str, release_log: str) -> str:
    if readme.count(START_MARKER) != 1 or readme.count(END_MARKER) != 1:
        raise ValueError("README release markers must each appear exactly once")
    before, remainder = readme.split(START_MARKER, maxsplit=1)
    _, after = remainder.split(END_MARKER, maxsplit=1)
    return f"{before}{START_MARKER}\n{release_log}\n{END_MARKER}{after}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    readme_path = root / "README.md"
    token = os.environ.get("GITHUB_TOKEN")
    items = github_release_items(token) + npm_release_items()
    updated = replace_release_log(
        readme_path.read_text(encoding="utf-8"),
        render_release_log(items),
    )
    readme_path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
