async def get_element_content(page, selector, default=None):
    element = await page.query_selector(selector)
    if element:
        return await element.inner_text()
    return default


async def get_elements_content(page, selector):
    elements = await page.query_selector_all(selector)
    return [await element.text_content() for element in elements]


async def get_image_sources(page, selector):
    images = []
    image_element = await page.query_selector(selector)
    if image_element:
        src = await image_element.get_attribute("src")
        if src:
            images.append(src)
    return images


def parse_price(price_text):
    if not price_text:
        return {"amount": "0", "currency": "€", "negotiable": False}

    price_text = price_text.strip()
    negotiable = "VB" in price_text

    price_text = price_text.replace("VB", "").strip()

    amount = price_text.replace("€", "").replace(".", "").replace(",", ".").strip()

    return {
        "amount": amount,
        "currency": "€",
        "negotiable": negotiable
    }


async def get_seller_details(seller_card, page):
    if not seller_card:
        return {
            "name": None,
            "since": None,
            "type": "private"
        }

    seller_name = await get_element_content(seller_card, "#viewad-contact-seller-name")
    seller_since = await get_element_content(seller_card, "#viewad-contact-seller-since")
    if seller_since:
        seller_since = seller_since.replace("Aktiv seit ", "").strip()

    seller_type = "private"
    pro_badge = await page.query_selector(".badge-hint-pro-small")
    if pro_badge:
        seller_type = "business"

    return {
        "name": seller_name.strip() if seller_name else None,
        "since": seller_since,
        "type": seller_type
    }


async def get_details(page):
    details = {}
    try:
        # Get all detail items
        detail_items = await page.query_selector_all("#viewad-details .addetailslist--detail")

        for item in detail_items:
            # Extract label (everything before the span)
            content = await item.text_content()
            # Find the span element inside
            value_span = await item.query_selector(".addetailslist--detail--value")

            if value_span:
                value = await value_span.text_content()
                # The label is the content without the value
                label = content.replace(value, "").strip()
                details[label] = value.strip()
    except Exception as e:
        print(f"Error getting details: {str(e)}")

    return details


async def get_features(page):
    features = []
    try:
        feature_elements = await page.query_selector_all("#viewad-configuration .checktaglist .checktag")
        for feature in feature_elements:
            feature_text = await feature.text_content()
            if feature_text and feature_text.strip():
                features.append(feature_text.strip())
    except Exception as e:
        print(f"Error getting features: {str(e)}")

    return features


async def get_location(page):
    location = await get_element_content(page, "#viewad-locality")
    if not location:
        return {
            "zip": "",
            "city": "",
            "state": ""
        }

    location_parts = location.split(" - ") if " - " in location else [location]

    first_part = location_parts[0].strip()
    zip_state_parts = first_part.split(" ", 1)
    zip_code = zip_state_parts[0].strip()
    state = zip_state_parts[1].strip() if len(zip_state_parts) > 1 else ""

    city = location_parts[1].strip() if len(location_parts) > 1 else ""

    return {
        "zip": zip_code,
        "city": city,
        "state": state
    }


async def get_extra_info(page):
    result = {
        "created_at": None,
        "views": "0"
    }

    try:
        date_element = await page.query_selector("#viewad-extra-info > div:nth-child(1) > span")
        if date_element:
            result["created_at"] = await date_element.inner_text()

        views_element = await page.query_selector("#viewad-cntr-num")
        if views_element:
            result["views"] = await views_element.inner_text()
    except Exception as e:
        print(f"Error getting extra info: {str(e)}")

    return result
