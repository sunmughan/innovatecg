import asyncio
from playwright.async_api import async_playwright
import json

async def monitor_network():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        requests_log = []
        
        page.on("request", lambda r: requests_log.append({
            "url": r.url,
            "method": r.method,
            "headers": dict(r.headers)
        }))
        
        page.on("response", lambda resp: print(f"[{resp.status}] {resp.request.method} {resp.url}"))
        
        print("Navigating to https://innovatecg.in/voting...")
        await page.goto('https://innovatecg.in/voting', wait_until='networkidle')
        await page.wait_for_timeout(1000)
        
        # Dismiss announcement popup if visible
        popup = page.locator('div.fixed.inset-0:has-text("IMPORTANT ANNOUNCEMENT")').first
        if await popup.is_visible():
            close_btn = popup.locator('button[aria-label="Close"], button:has-text("Close")').first
            if await close_btn.is_visible():
                await close_btn.click()
                await page.wait_for_timeout(500)
                
        # Switch to Education & Skills
        await page.locator('button:has-text("Education & Skills")').first.click()
        await page.wait_for_timeout(800)
        
        # Click Sunmughan Swamy Vote Now
        await page.locator('div.rounded-3xl:has-text("Sunmughan Swamy") >> button:has-text("Vote Now")').first.click()
        await page.wait_for_timeout(2000)
        
        # Print intercepted API URLs
        api_urls = [r["url"] for r in requests_log if not r["url"].endswith(('.js', '.css', '.png', '.jpg', '.ico', '.svg', '.woff2'))]
        print("\n--- Non-static API calls intercepted ---")
        for u in api_urls:
            print(u)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(monitor_network())
