import os
import sys
import time
import csv
import re

def select_csv_dialog():
    """Opens a native Windows file picker dialog if available."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title="Select Any CSV File for Automated Data Entry",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        root.destroy()
        return file_path
    except Exception:
        return ""

def clean_phone_number(raw_phone):
    """
    Normalizes phone numbers to standard 10-digit format for innovatecg.in.
    Strips '+91', spaces, hyphens, and extracts the last 10 digits.
    """
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone))
    if len(digits) >= 10:
        return digits[-10:] # Take last 10 digits
    return ""

def load_contacts_from_any_csv(csv_file):
    contacts = []
    skipped_count = 0
    if not os.path.exists(csv_file):
        return [], 0
        
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
        if not rows:
            return [], 0
            
        headers = [h.strip().lower() for h in rows[0]]
        name_idx, email_idx, phone_idx = -1, -1, -1
        
        for idx, h in enumerate(headers):
            if name_idx == -1 and "name" in h:
                name_idx = idx
            elif email_idx == -1 and ("mail" in h):
                email_idx = idx
            elif phone_idx == -1 and ("phone" in h or "mobile" in h or "tel" in h or "contact" in h):
                phone_idx = idx

        if name_idx == -1: name_idx = 0
        if phone_idx == -1: phone_idx = 1 if len(headers) > 1 else 0
        if email_idx == -1: email_idx = 2 if len(headers) > 2 else 0

        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            name = row[name_idx].strip() if name_idx < len(row) else ""
            email = row[email_idx].strip() if email_idx < len(row) else ""
            raw_phone = row[phone_idx].strip() if phone_idx < len(row) else ""
            
            clean_phone = clean_phone_number(raw_phone)
            
            # Ensure valid name, email, and 10-digit phone
            if name and email and len(clean_phone) == 10:
                contacts.append({
                    "name": name,
                    "email": email,
                    "phone": clean_phone,
                    "raw_phone": raw_phone
                })
            else:
                skipped_count += 1

    return contacts, skipped_count

def get_target_csv():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]

    common_files = [
        "mobile.csv",
        "indian_mobile_contacts_renamed.csv",
        r"c:\Users\WIN\OneDrive\Downloads\cleaned_indian_contacts_primary_only.csv",
        r"c:\Users\WIN\OneDrive\Downloads\indian_mobile_contacts_renamed.csv",
        r"c:\Users\WIN\OneDrive\Downloads\identities-from-contacts.csv",
        "sample_contacts.csv"
    ]
    for cf in common_files:
        if os.path.exists(cf):
            return cf

    picked = select_csv_dialog()
    if picked:
        return picked

    return "indian_mobile_contacts_renamed.csv"

def open_candidate_modal(page, candidate_name="Sunmughan Swamy", category_name="Education & Skills"):
    """
    Ensures the voting modal is opened specifically for the designated candidate and category.
    Guarantees no data is submitted to any wrong category or wrong candidate.
    """
    name_field = page.locator('input[name="name"]').first
    
    # Check if modal is already open
    if name_field.is_visible():
        dialogs = page.locator('div.fixed.inset-0, div[role="dialog"]').all()
        for d in dialogs:
            txt = d.inner_text().lower()
            if candidate_name.lower() in txt and ("education" in txt or category_name.lower() in txt):
                return True
        # If open for wrong person, reload clean page
        page.goto("https://innovatecg.in/voting", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)

    # 1. Switch to the target category
    cat_btn = page.locator(f'button:has-text("{category_name}")').first
    if not cat_btn.is_visible():
        page.goto("https://innovatecg.in/voting", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        cat_btn = page.locator(f'button:has-text("{category_name}")').first

    cat_btn.scroll_into_view_if_needed()
    cat_btn.click()
    page.wait_for_timeout(1000)

    # 2. Click Vote Now specifically on candidate's card
    sel = f'div.rounded-3xl:has-text("{candidate_name}") >> button:has-text("Vote Now")'
    vote_btn = page.locator(sel).first
    
    if vote_btn.is_visible():
        vote_btn.scroll_into_view_if_needed()
        vote_btn.click()
    else:
        clicked = page.evaluate('''(name) => {
            const elements = Array.from(document.querySelectorAll('h4, h3, h2, p, span, div'))
                .filter(el => (el.innerText || '').toLowerCase().includes(name.toLowerCase()));
            for (let el of elements) {
                let cur = el;
                while (cur && cur.parentElement && cur.tagName !== 'BODY') {
                    cur = cur.parentElement;
                    let btns = Array.from(cur.querySelectorAll('button')).filter(b => (b.innerText || '').includes('Vote Now'));
                    if (btns.length === 1) {
                        btns[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
                        btns[0].click();
                        return true;
                    }
                }
            }
            return false;
        }''', candidate_name)
        if not clicked:
            raise RuntimeError(f"Could not locate Vote button for '{candidate_name}' under '{category_name}'.")

    # 3. Wait for form to open
    page.locator('input[name="name"]').first.wait_for(state="visible", timeout=12000)
    
    # 4. Strict verification: ensure candidate name AND category appear inside the modal dialog
    dialog = page.locator('div.fixed.inset-0, div[role="dialog"]').first
    dialog_text = dialog.inner_text().lower()
    if candidate_name.lower() in dialog_text and ("education" in dialog_text or category_name.lower() in dialog_text):
        return True
    else:
        raise RuntimeError(f"Verification failed: Open modal does not contain '{candidate_name}' under '{category_name}'!")

def main():
    TARGET_CATEGORY = "Education & Skills"
    TARGET_CANDIDATE = "Sunmughan Swamy"

    print("=" * 70)
    print("   AUTOMATED DATA ENTRY - INNOVATE CG VOTING PORTAL")
    print(f"   Target Category  : {TARGET_CATEGORY}")
    print(f"   Target Candidate : {TARGET_CANDIDATE}")
    print("=" * 70)

    csv_path = ""
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        csv_path = sys.argv[1]
    else:
        csv_path = get_target_csv()

    print(f"\n[*] CSV Source File: {csv_path}")
    contacts, skipped = load_contacts_from_any_csv(csv_path)
    print(f"[*] Valid Contacts Ready: {len(contacts)}")
    if skipped > 0:
        print(f"[*] Skipped {skipped} rows without 10-digit Indian phone or missing name/email.")

    if not contacts:
        print("[!] No valid contacts found. Please check your CSV file.")
        return

    print("\nPreview of first 3 records to be submitted:")
    for i, c in enumerate(contacts[:3]):
        print(f"  {i+1}. Name: '{c['name']}' | Phone: '{c['phone']}' | Email: '{c['email']}'")
    if len(contacts) > 3:
        print(f"  ... and {len(contacts) - 3} more contacts queued.")

    print("\n" + "=" * 70)
    TARGET_URL = "https://innovatecg.in/voting"
    print(f"[*] Target Website: {TARGET_URL}")
    print("[*] Launching Chromium browser...")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        print("\n" + "=" * 70)
        print("SEMI-AUTOMATION ACTIVE:")
        print(f"1. Bot selects category '{TARGET_CATEGORY}'")
        print(f"2. Bot selects candidate '{TARGET_CANDIDATE}'")
        print("3. Bot fills Name, 10-digit Phone, and Email instantly")
        print("4. Bot highlights & places your cursor in the CAPTCHA box")
        print("5. You type the captcha code and click 'Confirm & Cast Vote'")
        print("6. Bot detects submission and advances to the next contact automatically!")
        print("=" * 70 + "\n")

        success_count = 0

        for i, contact in enumerate(contacts):
            print(f"\n[{i+1}/{len(contacts)}] Processing: {contact['name']} (Phone: {contact['phone']})...")
            try:
                # 1. Guarantee correct category & candidate modal is open
                open_candidate_modal(page, candidate_name=TARGET_CANDIDATE, category_name=TARGET_CATEGORY)
                print(f"  ✓ Category '{TARGET_CATEGORY}' -> Candidate '{TARGET_CANDIDATE}' confirmed.")

                # 2. Fill Name
                name_field = page.locator('input[name="name"]').first
                name_field.wait_for(state="visible", timeout=10000)
                name_field.fill(contact["name"])
                print(f"  ✓ Name  : {contact['name']}")

                # 3. Fill Phone (clean 10-digit number)
                phone_field = page.locator('input[name="phone"]').first
                phone_field.wait_for(state="visible", timeout=10000)
                phone_field.fill(contact["phone"])
                print(f"  ✓ Phone : {contact['phone']}")

                # 4. Fill Email
                email_field = page.locator('input[name="email"]').first
                email_field.wait_for(state="visible", timeout=10000)
                email_field.fill(contact["email"])
                print(f"  ✓ Email : {contact['email']}")

                # 5. Focus & Highlight Captcha Box
                code_field = page.locator('input[placeholder*="code" i], input[placeholder*="Enter code" i]').first
                if code_field.is_visible():
                    try:
                        page.evaluate("(el) => { el.style.outline = '4px solid #f59e0b'; el.focus(); }", code_field.element_handle())
                    except Exception:
                        code_field.focus()

                print(f"  👉 [ACTION REQUIRED]: Captcha box focused! Type the code and click 'Confirm & Cast Vote' in browser...")

                # 6. Wait for submission to complete (modal disappears)
                start_t = time.time()
                submitted = False
                while time.time() - start_t < 90:
                    if not name_field.is_visible():
                        submitted = True
                        success_count += 1
                        print(f"  🎉 SUCCESS: Vote cast for {TARGET_CANDIDATE} by {contact['name']}!")
                        break
                    time.sleep(0.5)

                if not submitted:
                    print(f"  [!] Timeout (90s) waiting for user submission on {contact['name']}. Moving next...")

                page.wait_for_timeout(1200)

                # Close any lingering confirmation dialog/toast overlay if still present
                try:
                    overlay_btns = page.locator('div.fixed.inset-0 button').all()
                    for cb in overlay_btns:
                        if cb.is_visible():
                            cb.click()
                            page.wait_for_timeout(400)
                except Exception:
                    pass

                # Reset to base URL if needed for next loop
                if name_field.is_visible():
                    page.goto(TARGET_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)

            except Exception as err:
                print(f"  [!] Error processing {contact['name']}: {err}")
                try:
                    page.goto(TARGET_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)
                except Exception:
                    pass

        print("\n" + "=" * 70)
        print(f"DATA ENTRY COMPLETE: {success_count}/{len(contacts)} votes processed successfully!")
        print("=" * 70)
        try:
            browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
