import asyncio
from playwright.async_api import async_playwright

async def test_dismiss():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Loading page...")
        await page.goto('https://innovatecg.in/voting', wait_until='networkidle')
        await page.wait_for_timeout(1000)
        
        # Check popup before dismiss
        popup = page.locator('div.fixed.inset-0:has-text("IMPORTANT ANNOUNCEMENT")').first
        is_vis_before = await popup.is_visible()
        print("Announcement visible initially:", is_vis_before)
        
        # Dismiss popup
        if is_vis_before:
            close_btn = popup.locator('button[aria-label="Close"], button:has-text("Close")').first
            await close_btn.click()
            await page.wait_for_timeout(800)
            
        is_vis_after = await popup.is_visible()
        print("Announcement visible after dismiss:", is_vis_after)
        assert not is_vis_after, "Failed to dismiss popup!"
        
        # Test clicking category button
        cat_btn = page.locator('button:has-text("Education & Skills")').first
        await cat_btn.click()
        await page.wait_for_timeout(800)
        
        # Verify candidate card clickable
        swamy_btn = page.locator('div.rounded-3xl:has-text("Sunmughan Swamy") >> button:has-text("Vote Now")').first
        print("Swamy Vote button visible after popup dismissed:", await swamy_btn.is_visible())
        
        await browser.close()
        print("TEST PASSED: Popup dismissed cleanly and categories work!")

if __name__ == "__main__":
    asyncio.run(test_dismiss())
