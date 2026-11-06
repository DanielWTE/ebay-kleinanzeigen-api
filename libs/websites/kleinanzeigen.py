import re
from typing import Any

from playwright.async_api import ElementHandle, Page


async def get_element_content(
    page: Page, selector: str, default: Any = None
) -> str | None:
    element: ElementHandle | None = await page.query_selector(selector)
    if element:
        return await element.inner_text()
    return default


async def get_elements_content(page: Page, selector: str) -> list[str]:
    elements: list[ElementHandle] = await page.query_selector_all(selector)
    return [await element.text_content() for element in elements]


async def get_image_sources(page: Page, selector: str) -> list[str]:
    elements: list[ElementHandle] = await page.query_selector_all(selector)
    seen: set = set()
    images: list[str] = []
    for el in elements:
        src: str = (
            await el.get_attribute("src") or await el.get_attribute("data-src") or ""
        )
        if "prod-ads" in src and src not in seen:
            seen.add(src)
            images.append(src)
    return images


def parse_price(price_text: str | None) -> dict[str, str | bool]:
    if not price_text:
        return {"amount": "0", "currency": "€", "negotiable": False}

    price_text = price_text.strip()
    negotiable: bool = "VB" in price_text

    price_text = price_text.replace("VB", "").strip()

    amount: str = price_text.replace("€", "").replace(".", "").replace(",", ".").strip()

    return {"amount": amount, "currency": "€", "negotiable": negotiable}


def _extract_user_id(href: str) -> str | None:
    """Extract the numeric Kleinanzeigen user ID from a profile link href.

    Handles two URL patterns:
      /s-anzeigen-des-nutzers/12345678
      /s-bestandsliste.html?userId=12345678
    """
    m = re.search(r"s-anzeigen-des-nutzers/(\d+)", href)
    if m:
        return m.group(1)
    m = re.search(r"[?&]userId=(\d+)", href)
    if m:
        return m.group(1)
    return None


async def get_seller_details(page: Page) -> dict[str, str | None]:
    result = {
        "name": None,
        "user_id": None,
        "since": None,
        "type": "private",
        "badges": [],
    }

    try:
        # Get seller name and user ID from the profile link.
        # .userprofile-vip is typically an <a> whose href encodes the user ID.
        name_selector = ".userprofile-vip"
        result["name"] = await get_element_content(page, name_selector)

        user_id = None
        for selector in (
            "a.userprofile-vip",
            "a[href*='s-anzeigen-des-nutzers']",
            "a[href*='userId']",
        ):
            el = await page.query_selector(selector)
            if el:
                href = await el.get_attribute("href") or ""
                user_id = _extract_user_id(href)
                if user_id:
                    break
        result["user_id"] = user_id

        # Get seller type
        type_selector = ".userprofile-vip-details-text:has-text('Privater Nutzer'), .userprofile-vip-details-text:has-text('Gewerblicher Nutzer')"
        seller_type = await get_element_content(page, type_selector)
        if seller_type:
            result["type"] = "business" if "Gewerblicher" in seller_type else "private"

        # Get since date
        since_selector = ".userprofile-vip-details-text:has-text('Aktiv seit')"
        seller_since = await get_element_content(page, since_selector)
        if seller_since:
            result["since"] = seller_since.replace("Aktiv seit ", "").strip()

        # Get user badges
        badges_selector = ".userprofile-vip-badges .userbadge-tag"
        badges = await get_elements_content(page, badges_selector)
        result["badges"] = [
            badge.strip() for badge in badges if badge and badge.strip()
        ]

    except Exception as e:
        print(f"Error getting seller details: {e!s}")

    return result


async def get_details(page: Page) -> dict[str, str]:
    details: dict[str, str] = {}
    try:
        # Get all detail items
        detail_items: list[ElementHandle] = await page.query_selector_all(
            "#viewad-details .addetailslist--detail"
        )

        for item in detail_items:
            # Extract label (everything before the span)
            content: str = await item.text_content()
            # Find the span element inside
            value_span: ElementHandle | None = await item.query_selector(
                ".addetailslist--detail--value"
            )

            if value_span:
                value: str = await value_span.text_content()
                # The label is the content without the value
                label: str = content.replace(value, "").strip()
                details[label] = value.strip()
    except Exception as e:
        print(f"Error getting details: {e!s}")

    return details


async def get_features(page: Page) -> list[str]:
    features: list[str] = []
    try:
        feature_elements: list[ElementHandle] = await page.query_selector_all(
            "#viewad-configuration .checktaglist .checktag"
        )
        for feature in feature_elements:
            feature_text: str = await feature.text_content()
            if feature_text and feature_text.strip():
                features.append(feature_text.strip())
    except Exception as e:
        print(f"Error getting features: {e!s}")

    return features


async def get_location(page: Page) -> dict[str, str]:
    location: str | None = await get_element_content(page, "#viewad-locality")
    if not location:
        return {"zip": "", "city": "", "state": ""}

    location_parts: list[str] = (
        location.split(" - ") if " - " in location else [location]
    )

    first_part: str = location_parts[0].strip()
    zip_state_parts: list[str] = first_part.split(" ", 1)
    zip_code: str = zip_state_parts[0].strip()
    state: str = zip_state_parts[1].strip() if len(zip_state_parts) > 1 else ""

    city: str = location_parts[1].strip() if len(location_parts) > 1 else ""

    return {"zip": zip_code, "city": city, "state": state}


async def get_extra_info(page: Page) -> dict[str, str | None]:
    result: dict[str, str | None] = {"created_at": None, "views": "0"}

    try:
        date_element: ElementHandle | None = await page.query_selector(
            "#viewad-extra-info > div:nth-child(1) > span"
        )
        if date_element:
            result["created_at"] = await date_element.inner_text()

        views_element: ElementHandle | None = await page.query_selector(
            "#viewad-cntr-num"
        )
        if views_element:
            result["views"] = await views_element.inner_text()
    except Exception as e:
        print(f"Error getting extra info: {e!s}")

    return result
