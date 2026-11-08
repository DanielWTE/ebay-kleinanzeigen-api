"""
Unit tests for the context-level request blocking in utils/browser.py.

Uses fake route/browser objects, so no Chromium or network is needed.

Run with:
  pytest tests/test_browser_resource_blocking.py -v
"""

import pytest

from utils.browser import _block_heavy_resources, _new_context


class FakeRequest:
    def __init__(self, url: str, resource_type: str):
        self.url = url
        self.resource_type = resource_type


class FakeRoute:
    def __init__(self, url: str, resource_type: str):
        self.request = FakeRequest(url, resource_type)
        self.outcome = None

    async def abort(self):
        self.outcome = "aborted"

    async def continue_(self):
        self.outcome = "continued"


async def _route(url: str, resource_type: str) -> str:
    route = FakeRoute(url, resource_type)
    await _block_heavy_resources(route)
    return route.outcome


@pytest.mark.parametrize("resource_type", ["image", "media", "font"])
async def test_heavy_resource_types_are_aborted(resource_type):
    url = "https://img.kleinanzeigen.de/api/v1/prod-ads/images/ab/abc.jpg"
    assert await _route(url, resource_type) == "aborted"


async def test_stylesheets_are_not_blocked():
    # inner_text() depends on CSS: without it the hidden "Reserviert • " /
    # "Gelöscht • " spans in #viewad-title leak into the title text and
    # every ad is reported as reserved.
    url = "https://static.kleinanzeigen.de/static/css/vip.css"
    assert await _route(url, "stylesheet") == "continued"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.kleinanzeigen.de/liberty/liberty.min.js",
        "https://www.kleinanzeigen.de/gdpr/cmp.js",
        "https://static.kleinanzeigen.de/promotion-frontend/bundle.js",
        "https://www.kleinanzeigen.de/kameleoon/engine.js",
        "https://server.sgtm-legacy.kleinanzeigen.de/gtm.js",
    ],
)
async def test_ad_tech_scripts_are_aborted(url):
    assert await _route(url, "script") == "aborted"


@pytest.mark.parametrize(
    ("url", "resource_type"),
    [
        ("https://www.kleinanzeigen.de/s-fahrraeder/c217", "document"),
        ("https://static.kleinanzeigen.de/static/js/header-navigation.js", "script"),
        ("https://www.kleinanzeigen.de/s-vac-inc-get.json?adId=1", "xhr"),
    ],
)
async def test_page_and_app_requests_pass_through(url, resource_type):
    assert await _route(url, resource_type) == "continued"


class FakeContext:
    def __init__(self):
        self.routes = []

    async def route(self, pattern, handler):
        self.routes.append((pattern, handler))


class FakeBrowser:
    def __init__(self):
        self.user_agents = []

    async def new_context(self, user_agent):
        self.user_agents.append(user_agent)
        return FakeContext()


async def test_new_context_installs_blocking_route(monkeypatch):
    monkeypatch.delenv("BROWSER_DISABLE_RESOURCE_BLOCKING", raising=False)
    browser = FakeBrowser()

    context = await _new_context(browser, "test-ua")

    assert browser.user_agents == ["test-ua"]
    assert context.routes == [("**/*", _block_heavy_resources)]


async def test_env_var_disables_blocking(monkeypatch):
    monkeypatch.setenv("BROWSER_DISABLE_RESOURCE_BLOCKING", "1")

    context = await _new_context(FakeBrowser(), "test-ua")

    assert context.routes == []
