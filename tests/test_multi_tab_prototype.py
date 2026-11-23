import asyncio
import json
from playwright.async_api import async_playwright

with open('candidates_catalog.json', 'r', encoding='utf-8') as f:
    CATALOG = json.load(f)

print(f"Loaded {len(CATALOG)} categories and {sum(len(v) for v in CATALOG.values())} candidates.")

async def test_multi_tab_setup():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Test 3 tabs
        pages = []
        for i in range(3):
            page = await context.new_page()
            pages.append(page)
            print(f"Created Tab {i+1}")
            
        print("All tabs initialized successfully.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_multi_tab_setup())
