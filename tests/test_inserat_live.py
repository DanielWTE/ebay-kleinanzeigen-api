"""
Live integration tests for GET /inserat/{id}.

Requires the server to be running:
  uvicorn main:app

Run with:
  pytest tests/test_inserat_live.py -v

A real listing id is fetched first via /inserate-by-url to ensure the id is valid.
Two fixture variants test the two accepted id formats:
  - full URL segment  (adid-category_id-location_id) — no redirect, ~4s
  - plain adid only                                  — server redirect,  ~7s

Deleted-ad tests use a known-expired ID. If that ID is ever recycled by
Kleinanzeigen the deleted-ad tests will need a new ID.
"""

import httpx
import pytest

pytestmark = pytest.mark.integration


BASE_URL = "http://localhost:8000"

SEARCH_URL = (
    "https://www.kleinanzeigen.de/s-autos/volkswagen/klima/"
    "k0c216+autos.marke_s:volkswagen"
)

# Known-deleted ads — all verified gone at time of writing (2026-05-09).
# If any entry returns 200 the test fails with an explicit "ID recycled" message
# so it is obvious the ID list needs updating rather than the detection logic.
DELETED_AD_IDS = [
    "3400236352",  # Mazda CX5 150ps
    "3400603080",  # VW Passat Alltrack 4Motion DSG
]

EXPECTED_DATA_FIELDS = {
    "id",
    "url_requested",
    "url_redirected",
    "categories",
    "title",
    "status",
    "price",
    "delivery",
    "location",
    "description",
    "media",
    "details",
    "features",
    "seller",
    "extra_info",
}

EXPECTED_TOP_FIELDS = {"success", "time_taken", "data", "performance_metrics"}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def http_client():
    try:
        httpx.get(f"{BASE_URL}/", timeout=5).raise_for_status()
    except Exception:
        pytest.skip("Server not running — start with: uvicorn main:app")
    with httpx.Client(base_url=BASE_URL, timeout=60) as client:
        yield client


@pytest.fixture(scope="session")
def listing(http_client):
    """Fetch one real listing from search results to use as test target."""
    resp = http_client.post(
        "/inserate-by-url", json={"url": SEARCH_URL, "max_pages": 1}
    )
    assert resp.status_code == 200
    results = resp.json().get("results", [])
    assert results, "No search results returned — cannot run /inserat tests"
    return results[0]


@pytest.fixture(scope="session")
def full_segment_response(http_client, listing):
    """Fetch detail using the full URL segment from the listing url field."""
    segment = listing["url"].rstrip("/").split("/")[-1]
    resp = http_client.get(
        f"/inserat/{segment}", params={"batch_id": "test-full-segment"}
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
    return resp.json()


@pytest.fixture(scope="session")
def plain_adid_response(http_client, full_segment_response):
    """Fetch detail using only the plain adid — triggers a server-side redirect."""
    adid = full_segment_response["data"]["id"]
    resp = http_client.get(f"/inserat/{adid}", params={"batch_id": "test-plain-adid"})
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
    return resp.json()


# ── Top-level structure ───────────────────────────────────────────────────────


def test_top_level_fields_present(full_segment_response):
    missing = EXPECTED_TOP_FIELDS - full_segment_response.keys()
    assert not missing, f"Missing top-level fields: {missing}"


def test_success_flag_is_true(full_segment_response):
    assert full_segment_response["success"] is True


def test_data_fields_present(full_segment_response):
    missing = EXPECTED_DATA_FIELDS - full_segment_response["data"].keys()
    assert not missing, f"Missing data fields: {missing}"


# ── url_requested and url_redirected ─────────────────────────────────────────


def test_full_segment_url_requested_matches_input(
    http_client, listing, full_segment_response
):
    segment = listing["url"].rstrip("/").split("/")[-1]
    expected = f"https://www.kleinanzeigen.de/s-anzeige/{segment}"
    assert full_segment_response["data"]["url_requested"] == expected


def test_full_segment_no_redirect(full_segment_response):
    """With a full segment, no redirect occurs — both URLs are identical."""
    data = full_segment_response["data"]
    assert data["url_requested"] == data["url_redirected"]


def test_plain_adid_url_requested_is_short_form(plain_adid_response):
    adid = plain_adid_response["data"]["id"]
    expected = f"https://www.kleinanzeigen.de/s-anzeige/{adid}"
    assert plain_adid_response["data"]["url_requested"] == expected


def test_plain_adid_redirected_url_contains_id(plain_adid_response):
    """url_redirected must always contain the listing id regardless of whether a redirect occurred."""
    data = plain_adid_response["data"]
    assert data["id"] in data["url_redirected"], (
        "url_redirected does not contain the listing id"
    )
    assert "s-anzeige" in data["url_redirected"]


def test_both_formats_return_same_id(full_segment_response, plain_adid_response):
    assert full_segment_response["data"]["id"] == plain_adid_response["data"]["id"]


def test_both_formats_return_same_title(full_segment_response, plain_adid_response):
    assert (
        full_segment_response["data"]["title"] == plain_adid_response["data"]["title"]
    )


# ── Content fields ────────────────────────────────────────────────────────────


def test_title_is_non_empty(full_segment_response):
    assert full_segment_response["data"]["title"].strip()


def test_status_is_valid(full_segment_response):
    assert full_segment_response["data"]["status"] in {
        "active",
        "sold",
        "reserved",
        "deleted",
    }


def test_categories_is_list(full_segment_response):
    assert isinstance(full_segment_response["data"]["categories"], list)


def test_images_is_list(full_segment_response):
    assert isinstance(full_segment_response["data"]["media"]["images"]["urls"], list)


# ── Deleted / not-found ads ───────────────────────────────────────────────────


@pytest.mark.parametrize("ad_id", DELETED_AD_IDS)
def test_deleted_ad(http_client, ad_id):
    resp = http_client.get(f"/inserat/{ad_id}", params={"batch_id": "test-deleted"})

    if resp.status_code == 200:
        data = resp.json().get("data", {})
        title = data.get("title") or "(no title)"
        pytest.fail(
            f"Ad {ad_id} returned 200 — it may have been recycled by Kleinanzeigen "
            f"(title: {title!r}). Remove this ID from DELETED_AD_IDS and replace it "
            f"with a freshly deleted one."
        )

    assert resp.status_code == 404, (
        f"Ad {ad_id}: expected 404, got {resp.status_code}: {resp.text[:200]}"
    )
    body = resp.json()
    assert body.get("detail", {}).get("status") == "deleted", (
        f"Ad {ad_id}: response body missing status=deleted: {body}"
    )
    assert "deleted" in body.get("detail", {}).get("error", "").lower(), (
        f"Ad {ad_id}: error message does not mention 'deleted': {body}"
    )


def test_active_ad_does_not_report_deleted(full_segment_response):
    """Guard: a live ad must never come back with status=deleted."""
    assert full_segment_response["data"]["status"] != "deleted"
    assert full_segment_response["success"] is True
