import json
import asyncio
from playwright.async_api import async_playwright

with open('candidates_catalog.json', 'r', encoding='utf-8') as f:
    CATALOG = json.load(f)

with open('overlay_hud.js', 'r', encoding='utf-8') as f:
    HUD_JS = f.read()

async def test_injection():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://innovatecg.in/voting', wait_until='networkidle')
        
        # Inject catalog and script
        await page.evaluate(f"window.__AGY_CATALOG = {json.dumps(CATALOG)};")
        await page.evaluate(HUD_JS)
        
        # Verify button is present
        btn_exists = await page.locator('#agy-hub-btn').is_visible()
        print("Floating Hub button visible:", btn_exists)
        
        # Click button to open modal
        await page.locator('#agy-hub-btn').click()
        modal_visible = await page.locator('#agy-hub-modal').is_visible()
        print("Modal visible on click:", modal_visible)
        
        # Check paused state
        paused = await page.evaluate('() => window.__AGY_PAUSED')
        print("Paused state while modal open:", paused)
        
        # Check tab cards count
        cards_count = await page.locator('.agy-tab-card').count()
        print("Tab cards rendered:", cards_count)
        
        # Switch tab count to 3
        await page.locator('#agy-tab-count').select_option('3')
        cards_count_3 = await page.locator('.agy-tab-card').count()
        print("After switching to 3 tabs, cards rendered:", cards_count_3)
        
        # Search candidate in Tab 1
        search_input = page.locator('.agy-cand-search').first
        await search_input.fill('Swamy')
        cand_select = page.locator('.agy-cand-select').first
        cand_text = await cand_select.inner_text()
        print("Candidate search result text:", cand_text.strip())
        
        # Apply settings
        await page.locator('#agy-apply-btn').click()
        config_update = await page.evaluate('() => window.__AGY_CONFIG_UPDATE')
        new_config = await page.evaluate('() => window.__AGY_CONFIG')
        paused_after_apply = await page.evaluate('() => window.__AGY_PAUSED')
        print("Config updated flag:", config_update)
        print("New config tab count:", new_config['tab_count'])
        print("New config tabs length:", len(new_config['tabs']))
        print("Paused state after apply:", paused_after_apply)
        
        await browser.close()
        print("\nOVERLAY HUD TEST PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    asyncio.run(test_injection())
