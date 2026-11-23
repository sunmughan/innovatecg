import os
import sys
import time
import csv
import re
import json

PROGRESS_FILE = "automation_progress.json"

def load_progress(csv_name):
    """Loads previous run progress and submitted phone numbers from JSON."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "csv_file": data.get("csv_file", csv_name),
                    "last_index": data.get("last_index", -1),
                    "submitted_phones": set(data.get("submitted_phones", [])),
                    "duplicate_phones": set(data.get("duplicate_phones", [])),
                    "submitted_count": data.get("submitted_count", 0),
                    "duplicate_count": data.get("duplicate_count", 0)
                }
        except Exception:
            pass
    return {
        "csv_file": csv_name,
        "last_index": -1,
        "submitted_phones": set(),
        "duplicate_phones": set(),
        "submitted_count": 0,
        "duplicate_count": 0
    }

def save_progress(prog):
    """Persists progress to disk atomically so termination at any row never loses state."""
    try:
        data = {
            "csv_file": prog["csv_file"],
            "last_index": prog["last_index"],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "submitted_phones": sorted(list(prog["submitted_phones"])),
            "duplicate_phones": sorted(list(prog["duplicate_phones"])),
            "submitted_count": len(prog["submitted_phones"]),
            "duplicate_count": len(prog["duplicate_phones"])
        }
        temp_file = PROGRESS_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        os.rename(temp_file, PROGRESS_FILE)
    except Exception as e:
        print(f"  [!] Failed to save progress file: {e}")

def inject_browser_controls(page):
    """Injects a floating skip button in the browser for instant human skip of duplicates or bad rows."""
    try:
        page.evaluate('''() => {
            if (document.getElementById('agy-control-panel')) return;
            const div = document.createElement('div');
            div.id = 'agy-control-panel';
            div.style.cssText = 'position:fixed;top:12px;right:16px;z-index:999999;display:flex;gap:8px;font-family:sans-serif;';
            
            const btn = document.createElement('button');
            btn.id = 'agy-skip-btn';
            btn.innerText = '⏭️ Skip Record (Duplicate / Error)';
            btn.style.cssText = 'background:#dc2626;color:white;padding:8px 16px;border:none;border-radius:20px;font-weight:bold;font-size:12px;box-shadow:0 4px 12px rgba(0,0,0,0.35);cursor:pointer;transition:transform 0.1s;';
            btn.onmouseover = () => btn.style.transform = 'scale(1.05)';
            btn.onmouseout = () => btn.style.transform = 'scale(1)';
            btn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                window.__AGY_SKIP_REQUESTED = true;
                btn.innerText = '⏳ Skipping...';
                btn.style.background = '#6b7280';
            };
            div.appendChild(btn);
            document.body.appendChild(div);
        }''')
    except Exception:
        pass

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

    # Load persistent progress & previously submitted/duplicate numbers
    progress = load_progress(csv_path)
    submitted_set = set(progress["submitted_phones"])
    duplicate_set = set(progress["duplicate_phones"])
    already_processed = submitted_set | duplicate_set
    seen_in_current_run = set()

    if already_processed:
        print("\n" + "*" * 70)
        print("📌 [SESSION PROGRESS MEMORIZATION ACTIVE]")
        print(f"   ✓ Previously Submitted Votes : {len(submitted_set)}")
        print(f"   ✓ Previously Marked Duplicates: {len(duplicate_set)}")
        print(f"   ✓ Last Completed Row Index   : #{progress['last_index'] + 1}")
        print("   ✓ Bot will automatically SKIP all previously processed contacts!")
        print("*" * 70)

    # Calculate remaining unsubmitted contacts
    remaining = [c for c in contacts if c["phone"] not in already_processed]
    print(f"[*] Remaining Contacts to Process: {len(remaining)} / {len(contacts)}")

    if not remaining:
        print("\n🎉 ALL contacts in this CSV file have already been processed and submitted!")
        print("   If you want to re-run from scratch, delete or rename 'automation_progress.json'.")
        return

    print("\nPreview of next upcoming records:")
    for i, c in enumerate(remaining[:3]):
        print(f"  {i+1}. Name: '{c['name']}' | Phone: '{c['phone']}' | Email: '{c['email']}'")
    if len(remaining) > 3:
        print(f"  ... and {len(remaining) - 3} more queued.")

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
        print("6. DUPLICATE PROTECTION: Portal duplicates auto-detected & rolled to next!")
        print("7. PROGRESS MEMORY: Auto-saved to 'automation_progress.json' after every vote")
        print("=" * 70 + "\n")

        success_count = len(submitted_set)
        duplicate_count = len(duplicate_set)

        for i, contact in enumerate(contacts):
            phone = contact["phone"]
            name = contact["name"]

            # 1. Skip previously handled (from past sessions)
            if phone in already_processed:
                continue

            # 2. Skip duplicates within this CSV run
            if phone in seen_in_current_run:
                print(f"\n[{i+1}/{len(contacts)}] ⏭️ [AUTO-SKIP]: Duplicate phone '{phone}' ({name}) in CSV. Rolling next...")
                duplicate_set.add(phone)
                progress["duplicate_phones"].add(phone)
                save_progress(progress)
                continue

            seen_in_current_run.add(phone)

            print(f"\n[{i+1}/{len(contacts)}] Processing: {name} (Phone: {phone})...")
            try:
                # Guarantee correct category & candidate modal is open
                open_candidate_modal(page, candidate_name=TARGET_CANDIDATE, category_name=TARGET_CATEGORY)
                print(f"  ✓ Category '{TARGET_CATEGORY}' -> Candidate '{TARGET_CANDIDATE}' confirmed.")

                # Inject floating human skip button
                inject_browser_controls(page)

                # Fill Name
                name_field = page.locator('input[name="name"]').first
                name_field.wait_for(state="visible", timeout=10000)
                name_field.fill(name)
                print(f"  ✓ Name  : {name}")

                # Fill Phone
                phone_field = page.locator('input[name="phone"]').first
                phone_field.wait_for(state="visible", timeout=10000)
                phone_field.fill(phone)
                print(f"  ✓ Phone : {phone}")

                # Fill Email
                email_field = page.locator('input[name="email"]').first
                email_field.wait_for(state="visible", timeout=10000)
                email_field.fill(contact["email"])
                print(f"  ✓ Email : {contact['email']}")

                # Focus & Highlight Captcha Box
                code_field = page.locator('input[placeholder*="code" i], input[placeholder*="Enter code" i]').first
                if code_field.is_visible():
                    try:
                        page.evaluate("(el) => { el.style.outline = '4px solid #f59e0b'; el.focus(); }", code_field.element_handle())
                    except Exception:
                        code_field.focus()

                print(f"  👉 [ACTION REQUIRED]: Captcha box focused! Type code & click 'Confirm & Cast Vote'...")
                print(f"     (Tip: If this number has already voted, bot will auto-detect duplicate & roll forward!)")

                # Wait for submission, portal duplicate, or human skip
                start_t = time.time()
                outcome = "timeout"
                err_detail = ""

                while time.time() - start_t < 90:
                    # Check human skip requested via floating button
                    try:
                        if page.evaluate("() => Boolean(window.__AGY_SKIP_REQUESTED)"):
                            outcome = "human_skip"
                            page.evaluate("() => { window.__AGY_SKIP_REQUESTED = false; }")
                            break
                    except Exception:
                        pass

                    # Check for portal success banner (z=true in Innovate CG)
                    done_btn = page.locator('div.bg-emerald-50 button:has-text("Done")').first
                    if done_btn.is_visible():
                        outcome = "success"
                        done_btn.click()
                        page.wait_for_timeout(600)
                        break

                    # Check if modal closed upon submit
                    if not name_field.is_visible():
                        outcome = "success"
                        break

                    # Check for portal error / duplicate banner (div.bg-red-50, div.animate-shake)
                    try:
                        error_banner = page.locator('div.bg-red-50, div.animate-shake').first
                        if error_banner.is_visible():
                            err_msg = error_banner.inner_text().strip()
                            duplicate_words = ["already", "duplicate", "voted", "limit", "one vote", "1 vote", "registered", "policy", "exists"]
                            if any(w in err_msg.lower() for w in duplicate_words):
                                outcome = "duplicate"
                                err_detail = err_msg
                                break
                    except Exception:
                        pass

                    time.sleep(0.4)

                # Process outcome
                if outcome == "success":
                    success_count += 1
                    submitted_set.add(phone)
                    progress["submitted_phones"].add(phone)
                    progress["last_index"] = i
                    save_progress(progress)
                    print(f"  🎉 SUCCESS: Vote cast for {TARGET_CANDIDATE} by {name}! [Total: {len(submitted_set)}]")

                elif outcome == "duplicate":
                    duplicate_count += 1
                    duplicate_set.add(phone)
                    progress["duplicate_phones"].add(phone)
                    progress["last_index"] = i
                    save_progress(progress)
                    print(f"  ⚠️ [DUPLICATE DETECTED ON PORTAL]: {err_detail}")
                    print(f"  ⏭️ Mobile '{phone}' already voted. Auto-skipping to next contact immediately...")
                    
                    # Close modal cleanly
                    try:
                        close_btn = page.locator('div.fixed.inset-0 button').first
                        if close_btn.is_visible():
                            close_btn.click()
                            page.wait_for_timeout(600)
                    except Exception:
                        pass

                elif outcome == "human_skip":
                    print(f"  ⏭️ Record skipped by user request. Rolling to next contact...")
                    try:
                        close_btn = page.locator('div.fixed.inset-0 button').first
                        if close_btn.is_visible():
                            close_btn.click()
                            page.wait_for_timeout(600)
                    except Exception:
                        pass

                else:
                    print(f"  [!] Timeout (90s) waiting on {name}. Moving next...")

                page.wait_for_timeout(1000)

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
                print(f"  [!] Error processing {name}: {err}")
                try:
                    page.goto(TARGET_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)
                except Exception:
                    pass

        print("\n" + "=" * 70)
        print(f"DATA ENTRY FINISHED:")
        print(f"  ✓ Total Successful Votes  : {len(submitted_set)}")
        print(f"  ✓ Total Duplicates Skipped: {len(duplicate_set)}")
        print(f"  ✓ Progress saved to 'automation_progress.json'")
        print("=" * 70)
        try:
            browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
