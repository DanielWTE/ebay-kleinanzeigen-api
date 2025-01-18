from fastapi import HTTPException
from libs.websites import kleinanzeigen as lib

async def get_inserate_details(url: str, page):
    try:
        await page.goto(url, timeout=120000)
        
        try:
            await page.wait_for_selector("#viewad-cntr-num", state="visible", timeout=2500)
        except:
            print("[WARNING] Views element did not appear within 5 seconds")
        
        ad_id = await lib.get_element_content(page, "#viewad-ad-id-box > ul > li:nth-child(2)", default="[ERROR] Ad ID not found")
        categorys = [cat.strip() for cat in await lib.get_elements_content(page, ".breadcrump-link") if cat.strip()]
        title = await lib.get_element_content(page, "#viewad-title", default="[ERROR] Title not found")
        price_element = await lib.get_element_content(page, "#viewad-price")
        price = lib.parse_price(price_element)
        location = await lib.get_element_content(page, "#viewad-locality", default="[ERROR] Location not found")
        views = await lib.get_element_content(page, "#viewad-cntr-num")
        upload_date = await lib.get_element_content(page, "#viewad-extra-info > div:nth-child(1) > span")
        description = await lib.get_element_content(page, "#viewad-description-text")
        if description:
            description = description.strip().replace("\n", " ").replace("  ", " ")
        
        images = await lib.get_image_sources(page, "#viewad-image")
        seller_card = await page.query_selector("#viewad-contact")
        seller_details = await lib.get_seller_details(seller_card, page) if seller_card else {
            "name": None,
            "since": None,
            "type": "private"
        }
        details = await lib.get_details(page) if await page.query_selector("#viewad-details") else {}
        shipping = await lib.get_element_content(page, ".boxedarticle--details--shipping")

        location_parts = location.split(" - ") if location and " - " in location else [location]
        zip_city = location_parts[0].split(" ", 1) if location_parts and " " in location_parts[0] else ["", ""]
        state = location_parts[1] if len(location_parts) > 1 else ""

        return {
            "id": ad_id,
            "categorys": categorys,
            "title": title.split(" • ")[-1] if " • " in title else title,
            "price": price,
            "shipping": True if shipping else False,
            "location": {
                "zip": zip_city[0],
                "city": zip_city[1] if len(zip_city) > 1 else "",
                "state": state
            },
            "views": views if views else "0",
            "upload_date": upload_date.strip() if upload_date else None,
            "description": description,
            "images": images,
            "details": details,
            "seller": seller_details,
        }
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 