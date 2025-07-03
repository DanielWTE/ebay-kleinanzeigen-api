from fastapi import HTTPException
from libs.websites import kleinanzeigen as lib
import re


async def get_inserate_details(url: str, page):
    try:
        await page.goto(url, timeout=120000)

        try:
            await page.wait_for_selector("#viewad-cntr-num", state="visible", timeout=2500)
        except:
            print("[WARNING] Views element did not appear within 5 seconds")

        ad_id = await lib.get_element_content(page, "#viewad-ad-id-box > ul > li:nth-child(2)",
                                              default="[ERROR] Ad ID not found")
        categories = [cat.strip() for cat in await lib.get_elements_content(page, ".breadcrump-link") if cat.strip()]
        title = await lib.get_element_content(page, "#viewad-title", default="[ERROR] Title not found")
        
        # Extract status from title element
        status = "active"  # Default status
        title_element = await page.query_selector("#viewad-title")
        if title_element:
            title_text = await title_element.inner_text()
            
            # Check for specific status indicators in the title text
            if "Verkauft" in title_text:
                status = "sold"
            elif "Reserviert •" in title_text:
                status = "reserved"
            elif "Gelöscht •" in title_text:
                status = "deleted"
            
            # Additional check for sold class
            title_classes = await title_element.get_attribute("class")
            if title_classes and "is-sold" in title_classes:
                status = "sold"
        
        # Final check for sold status in the page content
        sold_badge = await page.query_selector(".badge-sold")
        if sold_badge:
            status = "sold"
        
        price_element = await lib.get_element_content(page, "#viewad-price")
        price = lib.parse_price(price_element)
        views = await lib.get_element_content(page, "#viewad-cntr-num")
        description = await lib.get_element_content(page, "#viewad-description-text")
        if description:
            description = re.sub(r'[ \t]+', ' ', description).strip()
            description = re.sub(r'\n+', '\n', description)

        images = await lib.get_image_sources(page, "#viewad-image")
        seller_details = await lib.get_seller_details(page)
        details = await lib.get_details(page) if await page.query_selector("#viewad-details") else {}
        features = await lib.get_features(page) if await page.query_selector("#viewad-configuration") else {}
        
        shipping_text = await lib.get_element_content(page, ".boxedarticle--details--shipping")
        shipping = None
        if shipping_text:
            if "Nur Abholung" in shipping_text:
                shipping = "pickup"
            elif "Versand" in shipping_text:
                shipping = "shipping"
        
        location = await lib.get_location(page)
        extra_info = await lib.get_extra_info(page)

        return {
            "id": ad_id,
            "categories": categories,
            "title": title.split(" • ")[-1].strip() if " • " in title else title.strip(),
            "status": status,
            "price": price,
            "delivery": shipping,
            "location": location,
            "views": views if views else "0",
            "description": description,
            "images": images,
            "details": details,
            "features": features,
            "seller": seller_details,
            "extra_info": extra_info,
        }
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
