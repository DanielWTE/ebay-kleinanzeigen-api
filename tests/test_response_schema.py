"""End-to-end response-schema validation for every public route.

Drives the real FastAPI app through TestClient (real HTTP, real response_model
serialization/validation) with the scrapers stubbed to return payloads shaped
exactly like the real ones. Two checks per route:

1. HTTP layer: TestClient already runs response_model validation - a shape the
   schema rejects surfaces as a 500 ResponseValidationError.
2. Drift check: because every model sets extra="allow", undeclared keys pass
   silently. We diff the JSON keys actually emitted against the model's declared
   fields so schema/implementation drift fails loudly here instead of shipping.

Run with:  pytest tests/test_response_schema.py -v
"""

import pytest
from fastapi.testclient import TestClient

import routers.inserat as inserat_router
import routers.inserate_batch as batch_router
import routers.inserate_detailed_ultra as detailed_router
import routers.inserate_ultra as ultra_router
import scrapers.inserate_by_url as by_url_scraper
from main import app
from schemas import (
    BatchResponse,
    ConvertUrlResponse,
    DetailedSearchResponse,
    ListingDetailResponse,
    RootResponse,
    SearchResponse,
)

client = TestClient(app)
app.state.browser_manager = object()  # truthy stand-in; scrapers are stubbed

# ── Payload fixtures shaped like the real scraper output ─────────────────────

_DETAIL = {
    "id": "3379172637",
    "scraped_at": "2026-11-07T12:00:00+00:00",
    "url_requested": "https://www.kleinanzeigen.de/s-anzeige/3379172637",
    "url_redirected": "https://www.kleinanzeigen.de/s-anzeige/3379172637",
    "categories": ["s-wohnwagen-mobile"],
    "title": "Wohnwagen Favorit 550",
    "status": "active",
    "price": {"amount": "15000", "currency": "€", "negotiable": False},
    "delivery": "shipping",
    "location": {"zip": "12345", "city": "Berlin", "state": "Berlin"},
    "media": {
        "images": {"count": 3, "urls": ["https://img/1.jpg"]},
        "videos": {"count": 0, "urls": []},
        "audios": {"count": 0, "urls": []},
    },
    "details": {"Baujahr": "2008", "Kilometerstand": "80.000"},
    "features": ["Klimaanlage", "Radio"],
    "description": "Sehr gepflegter Wohnwagen.",
    "seller": {
        "name": "Max Mustermann",
        "user_id": "12345678",
        "since": "2019",
        "type": "private",
        "badges": [],
    },
    "extra_info": {"created_at": "2026-11-01", "views": "42"},
}

_CARD = {
    "adid": "3379172637",
    "url": "https://www.kleinanzeigen.de/s-anzeige/3379172637",
    "title": "Wohnwagen Favorit 550",
    "price": "15000",
    "location": "12345 Berlin (12 km)",
    "distance_km": 12.0,
    "description": "Sehr gepflegter Wohnwagen.",
    "published_at": "2026-11-06T10:00:00",
    "is_top_ad": False,
}

_SEARCH_RESULT = {
    "success": True,
    "results": [_CARD],
    "unique_results": 1,
    "time_taken": 1.234,
    "performance_metrics": {
        "pages_requested": 1,
        "pages_successful": 1,
        "success_rate": 100,
        "average_page_time": 1.2,
    },
    "browser_metrics": {"contexts_in_use": 1, "contexts_in_pool": 4},
}

_DETAIL_SCRAPE_RESULT = {
    "success": True,
    "data": _DETAIL,
    "time_taken": 0.5,
    "performance_metrics": {"success_rate": 100, "time_taken": 0.5},
}


def _detail_scraper_stub(browser_manager, listing_id, **kwargs):
    async def _run():
        return dict(_DETAIL_SCRAPE_RESULT)

    return _run()


def _search_scraper_stub(**kwargs):
    async def _run():
        return {**_SEARCH_RESULT}

    return _run()


@pytest.fixture
def patched_scrapers(monkeypatch):
    monkeypatch.setattr(
        inserat_router, "get_inserate_details_optimized", _detail_scraper_stub
    )
    monkeypatch.setattr(
        batch_router, "get_inserate_details_optimized", _detail_scraper_stub
    )
    monkeypatch.setattr(
        detailed_router, "get_inserate_details_optimized", _detail_scraper_stub
    )
    monkeypatch.setattr(
        detailed_router, "ultra_optimized_scrape_inserate", _search_scraper_stub
    )
    monkeypatch.setattr(
        ultra_router, "ultra_optimized_scrape_inserate", _search_scraper_stub
    )
    monkeypatch.setattr(by_url_scraper, "scrape_by_url", _search_scraper_stub)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _assert_keys_within_model(payload: dict, model) -> None:
    """Every key in payload must be a declared field on model (recursive for
    nested models). extra='allow' means undeclared keys validate silently;
    this surfaces them as drift."""
    declared = set(model.model_fields)
    extras = set(payload) - declared
    assert not extras, f"{model.__name__} emits undeclared keys: {sorted(extras)}"

    for name, field in model.model_fields.items():
        if name not in payload:
            continue
        value = payload[name]
        annotation = field.annotation
        # Unwrap Optional/Union to find a BaseModel member
        members = getattr(annotation, "__args__", None) or ()
        for member in members:
            if (
                isinstance(member, type)
                and issubclass(member, type)
                and hasattr(member, "model_fields")
            ):
                if isinstance(value, dict):
                    _assert_keys_within_model(value, member)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            _assert_keys_within_model(item, member)


# ── Route tests ──────────────────────────────────────────────────────────────


def test_root(patched_scrapers):
    resp = client.get("/")
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), RootResponse)


def test_inserat_detail(patched_scrapers):
    resp = client.get("/inserat/3379172637", params={"batch_id": "test"})
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), ListingDetailResponse)


def test_inserate_search(patched_scrapers):
    resp = client.get("/inserate", params={"query": "wohnwagen", "page_count": 1})
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), SearchResponse)


def test_inserate_detailed(patched_scrapers):
    resp = client.get("/inserate-detailed", params={"query": "wohnwagen"})
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), DetailedSearchResponse)


def test_inserate_batch(patched_scrapers):
    resp = client.post("/inserate/batch", json={"ids": ["3379172637"]})
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), BatchResponse)


def test_inserate_by_url(patched_scrapers):
    resp = client.post(
        "/inserate-by-url",
        json={"url": "https://www.kleinanzeigen.de/s-wohnwagen/", "max_pages": 1},
    )
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), SearchResponse)


def test_convert_url():
    resp = client.post(
        "/convert-url",
        json={"url": "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/"},
    )
    assert resp.status_code == 200
    _assert_keys_within_model(resp.json(), ConvertUrlResponse)
