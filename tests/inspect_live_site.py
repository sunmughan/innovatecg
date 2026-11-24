import asyncio
from playwright.async_api import async_playwright
import json

async def inspect_live():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to https://innovatecg.in/voting...")
        await page.goto('https://innovatecg.in/voting', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Save screenshot of initial load to see popup
        await page.screenshot(path='live_load.png')
        print("Screenshot saved to live_load.png")
        
        # Check all dialogs/popups
        dialogs = await page.evaluate('''() => {
            const elements = Array.from(document.querySelectorAll('div.fixed, div[role="dialog"], div.modal, div.popup, div[class*="banner"]'));
            return elements.map(el => ({
                tag: el.tagName,
                classes: el.className,
                text: el.innerText.trim().slice(0, 300)
            })).filter(e => e.text.length > 0);
        }''')
        
        print(f"Found {len(dialogs)} overlay/dialog elements:")
        for idx, d in enumerate(dialogs):
            print(f"--- Overlay #{idx+1} ---")
            print(f"Classes: {d['classes']}")
            print(f"Text: {d['text']}\n")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_live())
