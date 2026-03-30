from typing import Dict, List, Optional, Union, Any
from playwright.async_api import Page, ElementHandle


async def get_element_content(
    page: Page, selector: str, default: Any = None
) -> Optional[str]:
    element: Optional[ElementHandle] = await page.query_selector(selector)
    if element:
        return await element.inner_text()
    return default


async def get_elements_content(page: Page, selector: str) -> List[str]:
    elements: List[ElementHandle] = await page.query_selector_all(selector)
    return [await element.text_content() for element in elements]


async def get_image_sources(page: Page, selector: str) -> List[str]:
    images: List[str] = []
    image_element: Optional[ElementHandle] = await page.query_selector(selector)
    if image_element:
        src: Optional[str] = await image_element.get_attribute("src")
        if src:
            images.append(src)
    return images


def parse_price(price_text: Optional[str]) -> Dict[str, Union[str, bool]]:
    if not price_text:
        return {"amount": "0", "currency": "€", "negotiable": False}

    price_text = price_text.strip()
    negotiable: bool = "VB" in price_text

    price_text = price_text.replace("VB", "").strip()

    amount: str = price_text.replace("€", "").replace(".", "").replace(",", ".").strip()

    return {"amount": amount, "currency": "€", "negotiable": negotiable}


async def get_seller_details(page: Page) -> Dict[str, Optional[str]]:
    result = {"name": None, "since": None, "type": "private", "badges": []}

    try:
        # Get seller name
        name_selector = ".userprofile-vip"
        result["name"] = await get_element_content(page, name_selector)

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
        print(f"Error getting seller details: {str(e)}")

    return result


async def get_details(page: Page) -> Dict[str, str]:
    details: Dict[str, str] = {}
    try:
        # Get all detail items
        detail_items: List[ElementHandle] = await page.query_selector_all(
            "#viewad-details .addetailslist--detail"
        )

        for item in detail_items:
            # Extract label (everything before the span)
            content: str = await item.text_content()
            # Find the span element inside
            value_span: Optional[ElementHandle] = await item.query_selector(
                ".addetailslist--detail--value"
            )

            if value_span:
                value: str = await value_span.text_content()
                # The label is the content without the value
                label: str = content.replace(value, "").strip()
                details[label] = value.strip()
    except Exception as e:
        print(f"Error getting details: {str(e)}")

    return details


async def get_features(page: Page) -> List[str]:
    features: List[str] = []
    try:
        feature_elements: List[ElementHandle] = await page.query_selector_all(
            "#viewad-configuration .checktaglist .checktag"
        )
        for feature in feature_elements:
            feature_text: str = await feature.text_content()
            if feature_text and feature_text.strip():
                features.append(feature_text.strip())
    except Exception as e:
        print(f"Error getting features: {str(e)}")

    return features


async def get_location(page: Page) -> Dict[str, str]:
    location: Optional[str] = await get_element_content(page, "#viewad-locality")
    if not location:
        return {"zip": "", "city": "", "state": ""}

    location_parts: List[str] = (
        location.split(" - ") if " - " in location else [location]
    )

    first_part: str = location_parts[0].strip()
    zip_state_parts: List[str] = first_part.split(" ", 1)
    zip_code: str = zip_state_parts[0].strip()
    state: str = zip_state_parts[1].strip() if len(zip_state_parts) > 1 else ""

    city: str = location_parts[1].strip() if len(location_parts) > 1 else ""

    return {"zip": zip_code, "city": city, "state": state}


async def get_extra_info(page: Page) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"created_at": None, "views": "0"}

    try:
        date_element: Optional[ElementHandle] = await page.query_selector(
            "#viewad-extra-info > div:nth-child(1) > span"
        )
        if date_element:
            result["created_at"] = await date_element.inner_text()

        views_element: Optional[ElementHandle] = await page.query_selector(
            "#viewad-cntr-num"
        )
        if views_element:
            result["views"] = await views_element.inner_text()
    except Exception as e:
        print(f"Error getting extra info: {str(e)}")

    return result
