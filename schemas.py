"""Response models for the public API.

Each model mirrors a dict built in routers/ or scrapers/ and documents it in
the OpenAPI schema. Models allow extra keys, so response validation never drops
a field a route emits. Routes set response_model_exclude_unset=True so optional
keys that are absent at runtime stay absent instead of appearing as null.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Metrics are computed as floats but some code paths emit literal ints (e.g. 100).
# The union keeps the emitted JSON type unchanged instead of coercing 100 -> 100.0.
Num = int | float


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow")


# ── Errors ───────────────────────────────────────────────────────────────────


class ErrorResponse(_Model):
    detail: str = Field(description="Human-readable error message")


class ListingNotFoundDetail(_Model):
    error: str = Field(description="Why the listing could not be fetched")
    status: Literal["deleted"]


class ListingNotFoundResponse(_Model):
    detail: ListingNotFoundDetail


class ScrapeErrorDetail(_Model):
    """Structured error detail returned when a listing fetch fails."""

    error: str = Field(description="Human-readable error message")
    category: str = Field(
        description="Error category (network, browser, resource, parsing, validation)"
    )
    severity: str = Field(description="Error severity (low, medium, high, critical)")
    recovery_suggestions: list[str] = Field(
        description="Suggested recovery steps; empty when none"
    )


class ScrapeErrorResponse(_Model):
    """500 body for listing detail endpoints.

    `detail` is a plain string for generic failures, or a ScrapeErrorDetail
    object when the scraper classifies the failure.
    """

    detail: str | ScrapeErrorDetail


# ── Root ─────────────────────────────────────────────────────────────────────


class RootResponse(_Model):
    message: str
    endpoints: list[str]
    status: str


# ── Listing detail ───────────────────────────────────────────────────────────


class Price(_Model):
    amount: str = Field(
        description="Numeric string (e.g. '1500' or '12,50'); '0' when no price"
    )
    currency: str
    negotiable: bool = Field(description="True when the price is 'VB'")


class Location(_Model):
    zip: str
    city: str
    state: str


class MediaGroup(_Model):
    count: int
    urls: list[str]


class Media(_Model):
    images: MediaGroup
    videos: MediaGroup
    audios: MediaGroup


class Seller(_Model):
    name: str | None = None
    user_id: str | None = None
    since: str | None = None
    type: Literal["private", "business"]
    badges: list[str]


class ExtraInfo(_Model):
    created_at: str | None = None
    views: str


class ListingDetail(_Model):
    id: str | None = Field(description="Ad ID")
    scraped_at: str = Field(description="UTC timestamp, ISO 8601 (seconds precision)")
    url_requested: str
    url_redirected: str
    categories: list[str]
    title: str | None
    status: Literal["active", "sold", "reserved", "deleted"]
    price: Price
    delivery: Literal["pickup", "shipping"] | None = None
    location: Location
    media: Media
    details: dict[str, str] = Field(description="Label/value pairs from the ad")
    features: list[str] | dict[str, Any] = Field(
        description="Feature labels; an empty list when the ad has no feature section"
    )
    description: str | None
    seller: Seller
    extra_info: ExtraInfo


class DetailPerformanceMetrics(_Model):
    success_rate: Num
    time_taken: Num


class ListingDetailResponse(_Model):
    success: bool
    time_taken: Num
    data: ListingDetail
    performance_metrics: DetailPerformanceMetrics | None = None


# ── Search results ───────────────────────────────────────────────────────────


class ListingCard(_Model):
    adid: str
    url: str
    title: str
    price: str = Field(
        description="Price with '€', 'VB' and '.' removed; '' when absent"
    )
    location: str
    description: str
    published_at: str | None = Field(
        None, description="ISO 8601 datetime; null when the card shows no date"
    )
    is_top_ad: bool
    distance_km: float | None = Field(
        None,
        description="Distance in km parsed from a trailing '(N km)' on the location; null when absent",
    )


class SearchPerformanceMetrics(_Model):
    pages_requested: int
    pages_successful: int
    success_rate: Num
    average_page_time: Num


class SearchResponse(_Model):
    success: bool
    results: list[ListingCard]
    unique_results: int
    time_taken: Num
    performance_metrics: SearchPerformanceMetrics
    browser_metrics: dict[str, Any] | None = Field(
        None, description="Browser pool counters"
    )
    total_results: int | None = Field(
        None,
        description="Total hits from the page breadcrumb; only set when it could be parsed",
    )
    warnings: list[str] | None = Field(
        None, description="User-facing warnings; only set when there are any"
    )
    warning_summary: dict[str, Any] | None = Field(
        None, description="Warning counts by severity; only set when there are warnings"
    )


class DetailedListing(ListingCard):
    details: ListingDetail
    detail_fetch_time: Num


class DetailedSearchPerformanceMetrics(_Model):
    listings_found: int
    details_fetched: int
    success_rate: Num
    listing_phase_time: Num | None = None
    detail_phase_time: Num | None = None


class DetailedSearchResponse(_Model):
    success: bool
    data: list[DetailedListing]
    unique_results: int
    time_taken: Num
    performance_metrics: DetailedSearchPerformanceMetrics


# ── Batch ────────────────────────────────────────────────────────────────────


class BatchResponse(_Model):
    success: bool
    request_id: str
    total: int
    successful: int
    failed: int
    results: list[ListingDetail]
    errors: list[str] | None = Field(
        None, description="'<id>: <reason>' per failed ID; omitted when none failed"
    )


# ── URL conversion ───────────────────────────────────────────────────────────


class InserateParams(_Model):
    query: str | None = None
    location: str | None = None
    radius: int | None = None
    min_price: int | None = None
    max_price: int | None = None
    page_count: int


class UnmappedParams(_Model):
    category_slug: str | None = None
    subcategory: str | None = None
    category_id: int | None = None
    art: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    brands: list[str] | None = None
    unknown_attrs: dict[str, str] | None = Field(
        None,
        description="Unrecognized Kleinanzeigen filter attributes kept verbatim (key -> value)",
    )


class ConvertUrlResponse(_Model):
    inserate_params: InserateParams = Field(
        description="Parameters accepted by GET /inserate"
    )
    unmapped: UnmappedParams = Field(
        description="URL filters that GET /inserate cannot express yet"
    )
