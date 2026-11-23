import asyncio
import json
import time
from playwright.async_api import async_playwright

with open('candidates_catalog.json', 'r', encoding='utf-8') as f:
    CATALOG = json.load(f)

with open('overlay_hud.js', 'r', encoding='utf-8') as f:
    HUD_JS = f.read()

async def simulate_tab_worker(tab_id, page, category, candidate, queue, shared_state):
    print(f"[Tab {tab_id}] Started for '{candidate}' ({category})")
    
    # Inject HUD
    await page.evaluate(f"window.__AGY_CATALOG = {json.dumps(CATALOG)};")
    await page.evaluate(HUD_JS)
    
    while not queue.empty():
        # Check pause
        while shared_state.get("paused", False):
            await asyncio.sleep(0.5)
            
        contact = await queue.get()
        print(f"[Tab {tab_id}] Processing: {contact['name']} ({contact['phone']}) for {candidate}")
        await asyncio.sleep(0.5) # simulate action
        queue.task_done()
        print(f"[Tab {tab_id}] Finished: {contact['name']}")
        
    print(f"[Tab {tab_id}] Queue empty, tab worker completed.")

async def test_multi_tab_execution():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        queue = asyncio.Queue()
        for i in range(6):
            await queue.put({"name": f"User {i+1}", "phone": f"980000000{i}", "email": f"user{i+1}@test.com"})
            
        shared_state = {"paused": False}
        
        # Launch 2 tabs
        p1 = await context.new_page()
        p2 = await context.new_page()
        await p1.goto('https://innovatecg.in/voting', wait_until='domcontentloaded')
        await p2.goto('https://innovatecg.in/voting', wait_until='domcontentloaded')
        
        workers = [
            simulate_tab_worker(1, p1, "Education & Skills", "Sunmughan Swamy", queue, shared_state),
            simulate_tab_worker(2, p2, "Science & Tech", "Dr. Amit", queue, shared_state)
        ]
        
        await asyncio.gather(*workers)
        await browser.close()
        print("All tabs completed successfully.")

if __name__ == "__main__":
    asyncio.run(test_multi_tab_execution())
