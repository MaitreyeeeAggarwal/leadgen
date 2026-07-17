import asyncio
import csv
import os
import re
from playwright.async_api import async_playwright

async def scroll_feed(page, feed_locator):
    """Scrolls the Google Maps sidebar feed to the bottom to load all results."""
    print("Scrolling results panel...")
    last_height = await feed_locator.evaluate("el => el.scrollHeight")
    no_change_count = 0
    
    while True:
        await feed_locator.evaluate("el => el.scrollTo(0, el.scrollHeight)")
        await page.wait_for_timeout(2000)
        
        new_height = await feed_locator.evaluate("el => el.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 3:
                break
        else:
            no_change_count = 0
            last_height = new_height
            
    print("Finished scrolling results panel.")

async def scrape_query_stealth(page, query):
    """Search Google Maps and scrape listings by clicking them sequentially in the sidebar."""
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/"
    print(f"Navigating to: {search_url}")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await page.goto(search_url, timeout=30000)
            break
        except Exception as e:
            print(f"Error navigating to query (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return []
            await page.wait_for_timeout(5000)
    
    # Wait for the results pane
    try:
        await page.wait_for_selector('div[role="feed"]', timeout=15000)
    except Exception:
        print("Results feed not found or timed out. Checking if a single result opened directly...")
        if "/maps/place/" in page.url:
            # Single result page
            details = await scrape_detail_panel(page, page.url)
            if details["Business Name"]:
                return [details]
        return []

    feed = page.locator('div[role="feed"]')
    await scroll_feed(page, feed)
    
    # Get all direct result links
    links_locator = page.locator('a[href*="/maps/place/"]')
    count = await links_locator.count()
    
    # Collect unique URLs
    urls = []
    seen = set()
    for i in range(count):
        href = await links_locator.nth(i).get_attribute("href") or ""
        # Deduplicate using the base URL path (before "/data=")
        base_url = href.split("/data=")[0] if "/data=" in href else href
        if base_url and base_url not in seen:
            seen.add(base_url)
            urls.append(href)
            
    print(f"Found {len(urls)} unique listing links in the sidebar.")
    
    results = []
    
    for idx, url in enumerate(urls):
        try:
            # Locate the link element in JS to avoid CSS escaping issues
            element_handle = await page.evaluate_handle(
                """(targetUrl) => {
                    const links = document.querySelectorAll('a[href*="/maps/place/"]');
                    for (const link of links) {
                        const href = link.getAttribute('href') || link.href;
                        if (href === targetUrl) {
                            return link;
                        }
                    }
                    return null;
                }""",
                url
            )
            
            element = element_handle.as_element()
            if element:
                await element.scroll_into_view_if_needed()
                await element.click()
                await page.wait_for_timeout(1500)
                
                # Parse detail panel
                details = await parse_current_detail_panel(page, url)
                if details["Business Name"]:
                    results.append(details)
                    print(f"[{idx+1}/{len(urls)}] Scraped: {details['Business Name']} | Phone: {details['Phone Number']} | Web: {details['Website']}")
            else:
                print(f"[{idx+1}/{len(urls)}] Warning: Element handle not found for {url}")
        except Exception as e:
            print(f"[{idx+1}/{len(urls)}] Error scraping listing: {e}")
            
    return results

async def parse_current_detail_panel(page, url):
    """Parses details from the currently open detail panel in Google Maps."""
    details = {
        "Business Name": "",
        "Phone Number": "",
        "Website": "",
        "Industry": "",
        "Address Line 1": "",
        "Address Line 2": "",
        "Rating": "",
        "Review Count": "",
        "Google Maps Link": url
    }
    
    try:
        # Title
        # Standard Google Maps details panel title class
        title_loc = page.locator('h1.DUwDvf')
        if await title_loc.count() > 0:
            details["Business Name"] = (await title_loc.first.text_content() or "").strip()
        else:
            # Fallback: check all h1 elements and exclude 'Results' / 'Search Results'
            h1_elements = page.locator('h1')
            count = await h1_elements.count()
            for idx in range(count):
                txt = (await h1_elements.nth(idx).text_content() or "").strip()
                if txt.lower() not in ("results", "search results", "results map"):
                    details["Business Name"] = txt
                    break
            
        # Category
        industry_locator = page.locator("button[jsaction*='.category']")
        if await industry_locator.count() > 0:
            details["Industry"] = (await industry_locator.first.text_content() or "").strip()
            
        # Rating & Reviews
        rating_container = page.locator('div.F7nice')
        if await rating_container.count() > 0:
            text = await rating_container.first.text_content() or ""
            match = re.search(r'(\d\.\d)\s*\(?([\d,]+)\)?', text)
            if match:
                details["Rating"] = match.group(1)
                details["Review Count"] = match.group(2).replace(',', '')
                
        # Phone
        phone_locator = page.locator('button[data-item-id^="phone:tel:"]')
        if await phone_locator.count() > 0:
            data_id = await phone_locator.first.get_attribute("data-item-id")
            if data_id:
                details["Phone Number"] = data_id.replace("phone:tel:", "").strip()
            else:
                details["Phone Number"] = (await phone_locator.first.text_content() or "").strip()
                
        # Website
        website_locator = page.locator('a[data-item-id="authority"]')
        if await website_locator.count() > 0:
            details["Website"] = await website_locator.first.get_attribute("href") or ""
            
        # Address
        address_locator = page.locator('button[data-item-id^="address"]')
        if await address_locator.count() > 0:
            address_str = (await address_locator.first.text_content() or "").strip()
            address_str = address_str.replace("", "").strip()
            parts = [p.strip() for p in address_str.split(',') if p.strip()]
            if len(parts) > 1:
                details["Address Line 1"] = parts[0]
                details["Address Line 2"] = ", ".join(parts[1:])
            elif parts:
                details["Address Line 1"] = parts[0]
    except Exception as e:
        print(f"Error parsing detail panel fields: {e}")
        
    return details

async def scrape_detail_panel(page, url):
    """Fallback parser for direct single-listing landing pages."""
    try:
        await page.wait_for_selector('h1', timeout=15000)
        return await parse_current_detail_panel(page, url)
    except Exception as e:
        print(f"Error scraping fallback details for {url}: {e}")
        return {
            "Business Name": "", "Phone Number": "", "Website": "", "Industry": "",
            "Address Line 1": "", "Address Line 2": "", "Rating": "", "Review Count": "", "Google Maps Link": url
        }

async def scrape_maps_stealth_main(queries, output_csv):
    """Core entry point for the stealth maps scraper."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        all_results = []
        for q in queries:
            print(f"\n--- Starting Query: {q} ---")
            query_results = await scrape_query_stealth(page, q)
            all_results.extend(query_results)
            print(f"Query '{q}' complete. Collected {len(query_results)} listings.")
            # Pause between search queries
            await asyncio.sleep(3)
            
        await browser.close()
        
        # Write intermediate raw output
        if all_results:
            keys = all_results[0].keys()
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(all_results)
            print(f"Saved {len(all_results)} listings to {output_csv}")
        else:
            print("No listings found.")

if __name__ == "__main__":
    # Test run
    asyncio.run(scrape_maps_stealth_main(["Accounting firms in Hobart Tasmania"], "raw_stealth_test.csv"))
