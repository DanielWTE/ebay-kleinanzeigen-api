async def get_element_content(page, selector, default=None):
    element = await page.query_selector(selector)
    if element:
        return await element.text_content()
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
    detail_labels = await page.query_selector_all("#viewad-details > div > span:first-child")
    detail_values = await page.query_selector_all("#viewad-details > div > span:last-child")
    
    for i in range(len(detail_labels)):
        label = await detail_labels[i].text_content()
        value = await detail_values[i].text_content()
        details[label.strip()] = value.strip()
    
    return details 