"""Response models for the public API.

Each model mirrors a dict built in routers/ or scrapers/ and documents it in
the OpenAPI schema. Models allow extra keys, so response validation never drops
a field a route emits. Routes set response_model_exclude_unset=True so optional
keys that are absent at runtime stay absent instead of appearing as null.
"""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# Metrics are computed as floats but some code paths emit literal ints (e.g. 100).
# Union keeps the emitted JSON type unchanged instead of coercing 100 -> 100.0.
Num = Union[int, float]


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
    name: Optional[str] = None
    user_id: Optional[str] = None
    since: Optional[str] = None
    type: Literal["private", "business"]
    badges: list[str]


class ExtraInfo(_Model):
    created_at: Optional[str] = None
    views: str


class ListingDetail(_Model):
    id: Optional[str] = Field(description="Ad ID")
    scraped_at: str = Field(description="UTC timestamp, ISO 8601 (seconds precision)")
    url_requested: str
    url_redirected: str
    categories: list[str]
    title: Optional[str]
    status: Literal["active", "sold", "reserved", "deleted"]
    price: Price
    delivery: Optional[Literal["pickup", "shipping"]] = None
    location: Location
    media: Media
    details: dict[str, str] = Field(description="Label/value pairs from the ad")
    features: Union[list[str], dict[str, Any]] = Field(
        description="Feature labels; an empty object when the ad has no feature section"
    )
    description: Optional[str]
    seller: Seller
    extra_info: ExtraInfo


class DetailPerformanceMetrics(_Model):
    success_rate: Num
    time_taken: Num


class ListingDetailResponse(_Model):
    success: bool
    time_taken: Num
    data: ListingDetail
    performance_metrics: Optional[DetailPerformanceMetrics] = None


# ── Search results ───────────────────────────────────────────────────────────


class ListingCard(_Model):
    adid: str
    url: str
    title: str
    price: str = Field(description="Price with '€', 'VB' and '.' removed; '' when absent")
    location: str
    description: str
    published_at: Optional[str] = Field(
        None, description="ISO 8601 datetime; null when the card shows no date"
    )
    is_top_ad: bool


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
    browser_metrics: Optional[dict[str, Any]] = Field(
        None, description="Browser pool counters"
    )
    total_results: Optional[int] = Field(
        None,
        description="Total hits from the page breadcrumb; only set when it could be parsed",
    )
    warnings: Optional[list[str]] = Field(
        None, description="User-facing warnings; only set when there are any"
    )
    warning_summary: Optional[dict[str, Any]] = Field(
        None, description="Warning counts by severity; only set when there are warnings"
    )


class DetailedListing(ListingCard):
    details: ListingDetail
    detail_fetch_time: Num


class DetailedSearchPerformanceMetrics(_Model):
    listings_found: int
    details_fetched: int
    success_rate: Num
    listing_phase_time: Optional[Num] = None
    detail_phase_time: Optional[Num] = None


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
    errors: Optional[list[str]] = Field(
        None, description="'<id>: <reason>' per failed ID; omitted when none failed"
    )


# ── URL conversion ───────────────────────────────────────────────────────────


class InserateParams(_Model):
    query: Optional[str] = None
    location: Optional[str] = None
    radius: Optional[int] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    page_count: int


class UnmappedParams(_Model):
    category_slug: Optional[str] = None
    subcategory: Optional[str] = None
    category_id: Optional[int] = None
    art: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    brands: Optional[list[str]] = None


class ConvertUrlResponse(_Model):
    inserate_params: InserateParams = Field(
        description="Parameters accepted by GET /inserate"
    )
    unmapped: UnmappedParams = Field(
        description="URL filters that GET /inserate cannot express yet"
    )
