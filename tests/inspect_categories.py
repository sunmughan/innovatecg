from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://innovatecg.in/voting', wait_until='networkidle')
    
    # Category buttons usually sit in a horizontal scroll container or have category names
    # Let's inspect all buttons
    buttons = page.locator('button').all()
    print(f"Total buttons: {len(buttons)}")
    
    cat_names = []
    # Let's evaluate in JS to get the categories and candidates directly from DOM or fetch
    data = page.evaluate('''() => {
        // Find category buttons: they are in the category bar
        const catButtons = Array.from(document.querySelectorAll('button')).filter(b => {
            const t = b.innerText || '';
            return t && !['Vote Now', 'View', 'Search', 'Cast Vote', 'Filter', 'Next', 'Prev'].includes(t.trim()) && b.offsetHeight > 20;
        }).map(b => b.innerText.trim());
        
        return {
            possibleCategories: catButtons.slice(0, 15)
        };
    }''')
    print("Possible categories:", data['possibleCategories'])
    browser.close()
