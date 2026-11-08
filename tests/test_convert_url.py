"""
Unit tests for POST /convert-url endpoint.

Run with:
  pytest tests/test_convert_url.py -v
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.convert_url import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def post(url: str) -> dict:
    resp = client.post("/convert-url", json={"url": url})
    assert resp.status_code == 200
    return resp.json()


# ── Basic category URL (no keyword, no price) ────────────────────────────────


def test_category_only():
    data = post(
        "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/"
        "c220+wohnwagen_mobile.art_s:wohnwagen+wohnwagen_mobile.ez_i:2008%2C"
    )
    assert data["inserate_params"]["page_count"] == 1
    assert "query" not in data["inserate_params"]

    u = data["unmapped"]
    assert u["category_slug"] == "s-wohnwagen-mobile"
    assert u["subcategory"] == "wohnwagen"
    assert u["category_id"] == 220
    assert u["art"] == "wohnwagen"
    assert u["year_from"] == 2008
    assert u["year_to"] is None


# ── Full URL: keyword, price range, brands, year ─────────────────────────────


def test_full_url():
    data = post(
        "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/"
        "preis:1000:15000/klima/"
        "k0c220+wohnwagen_mobile.art_s:wohnwagen"
        "+wohnwagen_mobile.ez_i:2008%2C"
        "+wohnwagen_mobile.marke_s:(fendt%2Cknaus)"
    )
    ip = data["inserate_params"]
    assert ip["query"] == "klima"
    assert ip["min_price"] == 1000
    assert ip["max_price"] == 15000
    assert ip["page_count"] == 1

    u = data["unmapped"]
    assert u["category_id"] == 220
    assert u["art"] == "wohnwagen"
    assert u["year_from"] == 2008
    assert sorted(u["brands"]) == ["fendt", "knaus"]


# ── Query-string keyword + location + radius ─────────────────────────────────


def test_querystring_params():
    data = post(
        "https://www.kleinanzeigen.de/s-anzeige:angebote"
        "?keywords=wohnwagen&locationStr=Berlin&radius=50"
    )
    ip = data["inserate_params"]
    assert ip["query"] == "wohnwagen"
    assert ip["location"] == "Berlin"
    assert ip["radius"] == 50


# ── Pagination ────────────────────────────────────────────────────────────────


def test_page_number():
    data = post(
        "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/seite:3/c220"
    )
    assert data["inserate_params"]["page"] == 3
    assert data["inserate_params"]["page_count"] == 1


def test_s_seite_page():
    data = post("https://www.kleinanzeigen.de/s-wohnwagen-mobile/s-seite:4/c220")
    assert data["inserate_params"]["page"] == 4
    assert data["inserate_params"]["page_count"] == 1


# ── Single brand ─────────────────────────────────────────────────────────────


def test_single_brand():
    data = post(
        "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/"
        "c220+wohnwagen_mobile.marke_s:fendt"
    )
    assert data["unmapped"]["brands"] == ["fendt"]


# ── Missing / empty URL ───────────────────────────────────────────────────────


def test_empty_url_returns_defaults():
    data = post("")
    assert data["inserate_params"]["page_count"] == 1
    assert data["inserate_params"]["page"] == 1
    assert data["unmapped"] == {}


# ── Unmapped keys are NOT in inserate_params ─────────────────────────────────


def test_category_keys_not_in_inserate_params():
    data = post(
        "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/"
        "c220+wohnwagen_mobile.art_s:wohnwagen"
    )
    for key in (
        "category_slug",
        "subcategory",
        "category_id",
        "art",
        "brands",
        "year_from",
        "year_to",
    ):
        assert key not in data["inserate_params"]


# ── Autos URLs ────────────────────────────────────────────────────────────────


def test_autos_category_only():
    # "klima" lands at path position 1 → parsed as subcategory, not path_keyword
    data = post("https://www.kleinanzeigen.de/s-autos/klima/k0c216")
    ip = data["inserate_params"]
    assert "query" not in ip
    assert ip["page_count"] == 1

    u = data["unmapped"]
    assert u["category_slug"] == "s-autos"
    assert u["subcategory"] == "klima"
    assert u["category_id"] == 216


def test_autos_with_brand_and_keyword():
    data = post(
        "https://www.kleinanzeigen.de/s-autos/volkswagen/klima/"
        "k0c216+autos.marke_s:volkswagen"
    )
    ip = data["inserate_params"]
    assert ip["query"] == "klima"
    assert ip["page_count"] == 1

    u = data["unmapped"]
    assert u["category_slug"] == "s-autos"
    assert u["subcategory"] == "volkswagen"
    assert u["category_id"] == 216
    assert u["brands"] == ["volkswagen"]


def test_autos_full_filters():
    data = post(
        "https://www.kleinanzeigen.de/s-autos/volkswagen/klima/"
        "k0c216+autos.ez_i:2008%2C+autos.fuel_s:lpg+autos.km_i:2%2C"
        "+autos.marke_s:volkswagen+autos.shift_s:automatik+autos.typ_s:(kombi%2Csuv)"
    )
    ip = data["inserate_params"]
    assert ip["query"] == "klima"
    assert ip["page_count"] == 1

    u = data["unmapped"]
    assert u["category_id"] == 216
    assert u["year_from"] == 2008
    assert u["year_to"] is None
    assert u["brands"] == ["volkswagen"]

    ua = u["unknown_attrs"]
    assert ua["autos.fuel_s"] == "lpg"
    assert ua["autos.shift_s"] == "automatik"
    assert ua["autos.typ_s"] == "(kombi,suv)"
    assert "autos.km_i" in ua
