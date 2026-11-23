import time
from playwright.sync_api import sync_playwright

def simulate_loop():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://innovatecg.in/voting', wait_until='networkidle')

        contacts = [
            {"name": "Sathish Shivaprasad", "phone": "9383465787", "email": "vikas.gupta@yahoo.com"},
            {"name": "Malathi Satyanarayana", "phone": "8485195442", "email": "biju.gupta@yahoo.com"},
            {"name": "Chithra Parameshwaran", "phone": "8055362917", "email": "vikas.kumar47@outlook.com"}
        ]

        TARGET_CATEGORY = "Education & Skills"
        TARGET_CANDIDATE = "Sunmughan Swamy"

        for i, contact in enumerate(contacts):
            print(f"\n--- [Contact {i+1}] {contact['name']} ---")

            # 1. Switch to category
            cat_btn = page.locator(f'button:has-text("{TARGET_CATEGORY}")').first
            if not cat_btn.is_visible():
                page.goto("https://innovatecg.in/voting", wait_until="domcontentloaded")
                cat_btn = page.locator(f'button:has-text("{TARGET_CATEGORY}")').first
            
            cat_btn.scroll_into_view_if_needed()
            cat_btn.click()
            page.wait_for_timeout(800)

            # 2. Click candidate Vote Now
            vote_btn = page.locator(f'div.rounded-3xl:has-text("{TARGET_CANDIDATE}") >> button:has-text("Vote Now")').first
            vote_btn.scroll_into_view_if_needed()
            vote_btn.click()

            # 3. Wait for modal
            name_input = page.locator('input[name="name"]').first
            name_input.wait_for(state="visible", timeout=10000)

            # 4. STRICT VERIFICATION OF CANDIDATE AND CATEGORY IN MODAL
            dialog = page.locator('div.fixed.inset-0').first
            dialog_text = dialog.inner_text()
            assert TARGET_CANDIDATE.lower() in dialog_text.lower(), f"Wrong candidate in modal for record {i+1}!"
            assert "education" in dialog_text.lower(), f"Wrong category in modal for record {i+1}!"
            print(f"  [Verified] Modal belongs to: '{TARGET_CANDIDATE}' in '{TARGET_CATEGORY}'")

            # 5. Fill fields
            name_input.fill(contact['name'])
            page.locator('input[name="phone"]').first.fill(contact['phone'])
            page.locator('input[name="email"]').first.fill(contact['email'])
            print(f"  [Filled] Name: {contact['name']} | Phone: {contact['phone']} | Email: {contact['email']}")

            # 6. Simulate submission / close
            # Close button is the SVG X in the modal top right
            close_btn = page.locator('div.fixed.inset-0 button').first
            close_btn.click()
            page.wait_for_timeout(1000)
            assert not name_input.is_visible(), "Modal did not close!"
            print(f"  [Closed] Modal closed cleanly after submission.")

        browser.close()
        print("\nALL 3 CONSECUTIVE SUBMISSIONS OPENED SUNMUGHAN SWAMY PERFECTLY WITHOUT RESETTING TO DEFAULT!")

if __name__ == "__main__":
    simulate_loop()
