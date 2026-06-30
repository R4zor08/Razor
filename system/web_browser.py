"""Web browser and URL helpers."""

from __future__ import annotations

import os
import urllib.parse

KNOWN_SITES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
}


class WebBrowser:
    """Open URLs and web searches in the default browser."""

    def open_url(self, target: str) -> str:
        """Open a URL or known site name."""
        query = target.strip()
        if not query:
            return "Please specify a website or URL."

        lowered = query.lower()
        if lowered in KNOWN_SITES:
            return self._launch(KNOWN_SITES[lowered])

        if lowered.startswith(("http://", "https://")):
            return self._launch(query)

        if "." in query and " " not in query:
            url = query if query.startswith("http") else f"https://{query}"
            return self._launch(url)

        site_key = lowered.replace(" ", "")
        for name, url in KNOWN_SITES.items():
            if name in site_key or site_key in name:
                return self._launch(url)

        return self.search_web(query)

    def search_web(self, query: str) -> str:
        """Open a Google search for the query."""
        keyword = query.strip()
        if not keyword:
            return "Please specify a search query."

        for prefix in ("search google for ", "google ", "search for ", "search the web for ", "look up "):
            if keyword.lower().startswith(prefix):
                keyword = keyword[len(prefix) :].strip()
                break

        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(keyword)
        return self._launch(url, label=f"Google search for '{keyword}'")

    @staticmethod
    def _launch(url: str, *, label: str | None = None) -> str:
        try:
            os.startfile(url)  # noqa: S606
        except OSError as exc:
            return f"Failed to open browser: {exc}"
        return f"Opened {label or url}."
