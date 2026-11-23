from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://innovatecg.in/voting', wait_until='networkidle')
    page.locator('button:has-text("Education & Skills")').first.click()
    page.wait_for_timeout(1000)
    page.locator('div.rounded-3xl:has-text("Sunmughan Swamy") >> button:has-text("Vote Now")').first.click()
    page.wait_for_timeout(1000)
    
    # Inspect modal
    dialogs = page.locator('div.fixed.inset-0').all()
    print(f"Found {len(dialogs)} fixed inset-0 elements:")
    for i, d in enumerate(dialogs):
        print(f"--- Dialog {i+1} ---")
        print(d.inner_text()[:400])
        
    browser.close()
