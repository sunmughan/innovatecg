import os
import sys
import time
import csv
import re
import json
import asyncio
from playwright.async_api import async_playwright

PROGRESS_FILE = "automation_progress.json"
CATALOG_FILE = "candidates_catalog.json"
HUD_SCRIPT_FILE = "overlay_hud.js"

# Load candidate catalog
CATALOG = {}
if os.path.exists(CATALOG_FILE):
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            CATALOG = json.load(f)
    except Exception:
        pass

# Load HUD injection script
HUD_SCRIPT = ""
if os.path.exists(HUD_SCRIPT_FILE):
    try:
        with open(HUD_SCRIPT_FILE, "r", encoding="utf-8") as f:
            HUD_SCRIPT = f.read()
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
        return digits[-10:]
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
    """Persists progress to disk atomically."""
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

async def inject_hud(page):
    """Injects the interactive Control Center HUD into the page."""
    try:
        await page.evaluate(f"window.__AGY_CATALOG = {json.dumps(CATALOG)};")
        if HUD_SCRIPT:
            await page.evaluate(HUD_SCRIPT)
    except Exception:
        pass

async def open_candidate_modal(page, candidate_name, category_name):
    """
    Ensures the voting modal is opened specifically for the designated candidate and category.
    Guarantees no data is submitted to any wrong category or wrong candidate.
    """
    name_field = page.locator('input[name="name"]').first
    
    # Check if modal is already open
    if await name_field.is_visible():
        dialog = page.locator('div.fixed.inset-0, div[role="dialog"]').first
        txt = (await dialog.inner_text()).lower()
        if candidate_name.lower() in txt:
            return True
        # If open for wrong person, reload clean page
        await page.goto("https://innovatecg.in/voting", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1000)

    # 1. Switch to the target category
    cat_btn = page.locator(f'button:has-text("{category_name}")').first
    if not (await cat_btn.is_visible()):
        await page.goto("https://innovatecg.in/voting", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1500)
        cat_btn = page.locator(f'button:has-text("{category_name}")').first

    await cat_btn.scroll_into_view_if_needed()
    await cat_btn.click()
    await page.wait_for_timeout(900)

    # 2. Click Vote Now specifically on candidate's card
    sel = f'div.rounded-3xl:has-text("{candidate_name}") >> button:has-text("Vote Now")'
    vote_btn = page.locator(sel).first
    
    if await vote_btn.is_visible():
        await vote_btn.scroll_into_view_if_needed()
        await vote_btn.click()
    else:
        clicked = await page.evaluate('''(name) => {
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
    await page.locator('input[name="name"]').first.wait_for(state="visible", timeout=12000)
    
    # 4. Strict verification: ensure candidate name appears inside the modal dialog
    dialog = page.locator('div.fixed.inset-0, div[role="dialog"]').first
    dialog_text = (await dialog.inner_text()).lower()
    if candidate_name.lower() in dialog_text:
        return True
    else:
        raise RuntimeError(f"Verification failed: Open modal does not contain '{candidate_name}'!")

async def tab_worker(tab_id, page, shared_state, contact_queue):
    """
    Runs continuous automated voting for an individual tab session.
    Respects global pause whenever the floating settings menu is open.
    """
    TARGET_URL = "https://innovatecg.in/voting"
    print(f"[Tab #{tab_id}] Worker online.")

    while not contact_queue.empty() and not shared_state.get("stop_requested", False):
        # 1. Global Pause Gate (Paused while Control Center overlay is open)
        while shared_state.get("paused", False):
            await asyncio.sleep(0.5)

        # 2. Get current assigned target from config
        tab_cfg = shared_state["tabs_config"].get(tab_id, {
            "category": "Education & Skills",
            "candidate": "Sunmughan Swamy"
        })
        category = tab_cfg["category"]
        candidate = tab_cfg["candidate"]

        try:
            contact = contact_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        phone = contact["phone"]
        name = contact["name"]

        # Duplicate check against persistent sets
        if phone in shared_state["already_processed"]:
            contact_queue.task_done()
            continue

        shared_state["already_processed"].add(phone)

        print(f"\n[Tab #{tab_id}] Processing: {name} (Phone: {phone}) -> Candidate: '{candidate}' [{category}]")
        
        try:
            # Re-inject HUD if needed
            await inject_hud(page)

            # Ensure correct candidate modal is open
            await open_candidate_modal(page, candidate_name=candidate, category_name=category)

            # Re-inject HUD after modal
            await inject_hud(page)

            # Fill Name
            name_field = page.locator('input[name="name"]').first
            await name_field.wait_for(state="visible", timeout=10000)
            await name_field.fill(name)

            # Fill Phone
            phone_field = page.locator('input[name="phone"]').first
            await phone_field.wait_for(state="visible", timeout=10000)
            await phone_field.fill(phone)

            # Fill Email
            email_field = page.locator('input[name="email"]').first
            await email_field.wait_for(state="visible", timeout=10000)
            await email_field.fill(contact["email"])

            # Focus & Highlight Captcha Box
            code_field = page.locator('input[placeholder*="code" i], input[placeholder*="Enter code" i]').first
            if await code_field.is_visible():
                try:
                    await page.evaluate("(el) => { el.style.outline = '4px solid #f59e0b'; el.focus(); }", await code_field.element_handle())
                except Exception:
                    await code_field.focus()

            # Mode handling
            mode = shared_state.get("mode", "manual")
            if mode == "auto":
                # Ready for user's final touch instructions
                print(f"  [Tab #{tab_id}] 🤖 Auto Mode ready for final touch. Waiting for submission...")

            print(f"  [Tab #{tab_id}] 👉 Captcha focused for {name} ({candidate}). Waiting for vote cast...")

            # Waiting loop (detect submit, duplicate, skip, or pause)
            start_t = time.time()
            outcome = "timeout"
            err_detail = ""

            while time.time() - start_t < 90:
                # Check if paused
                while shared_state.get("paused", False):
                    await asyncio.sleep(0.5)

                # Check if skip requested via floating button
                try:
                    if await page.evaluate("() => Boolean(window.__AGY_SKIP_REQUESTED)"):
                        outcome = "human_skip"
                        await page.evaluate("() => { window.__AGY_SKIP_REQUESTED = false; }")
                        break
                except Exception:
                    pass

                # Check portal success (Done button or green success box)
                done_btn = page.locator('div.bg-emerald-50 button:has-text("Done")').first
                if await done_btn.is_visible():
                    outcome = "success"
                    await done_btn.click()
                    await page.wait_for_timeout(600)
                    break

                # Check if modal closed upon submit
                if not (await name_field.is_visible()):
                    outcome = "success"
                    break

                # Check for portal duplicate error
                try:
                    error_banner = page.locator('div.bg-red-50, div.animate-shake').first
                    if await error_banner.is_visible():
                        err_msg = (await error_banner.inner_text()).strip()
                        duplicate_words = ["already", "duplicate", "voted", "limit", "one vote", "1 vote", "registered", "policy", "exists"]
                        if any(w in err_msg.lower() for w in duplicate_words):
                            outcome = "duplicate"
                            err_detail = err_msg
                            break
                except Exception:
                    pass

                await asyncio.sleep(0.4)

            # Process outcome
            if outcome == "success":
                shared_state["submitted_phones"].add(phone)
                shared_state["progress"]["submitted_phones"].add(phone)
                save_progress(shared_state["progress"])
                print(f"  🎉 [Tab #{tab_id}] SUCCESS: Vote cast for '{candidate}' by {name}! [Total: {len(shared_state['submitted_phones'])}]")

            elif outcome == "duplicate":
                shared_state["duplicate_phones"].add(phone)
                shared_state["progress"]["duplicate_phones"].add(phone)
                save_progress(shared_state["progress"])
                print(f"  ⚠️ [Tab #{tab_id}] DUPLICATE ON PORTAL: {err_detail}")
                print(f"  ⏭️ Mobile '{phone}' already voted. Rolling to next contact...")
                try:
                    close_btn = page.locator('div.fixed.inset-0 button').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

            elif outcome == "human_skip":
                print(f"  ⏭️ [Tab #{tab_id}] Skipped by user. Rolling to next...")
                try:
                    close_btn = page.locator('div.fixed.inset-0 button').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

            else:
                print(f"  [Tab #{tab_id}] [!] Timeout waiting on {name}. Moving next...")

            await page.wait_for_timeout(800)

            # Reset modal if still open
            if await name_field.is_visible():
                await page.goto(TARGET_URL, wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)

        except Exception as err:
            print(f"  [Tab #{tab_id}] [!] Error on {name}: {err}")
            try:
                await page.goto(TARGET_URL, wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
            except Exception:
                pass
        finally:
            contact_queue.task_done()

    print(f"[Tab #{tab_id}] Worker finished all assigned queue tasks.")

async def hud_poller(pages_dict, shared_state, context):
    """
    Listens for floating Control Center HUD clicks, pause states, and configuration updates across all tabs.
    Dynamically spawns or closes tabs based on user's parallel tab settings!
    """
    TARGET_URL = "https://innovatecg.in/voting"
    while not shared_state.get("stop_requested", False):
        try:
            # Poll Tab #1 (or all pages) for config updates and pause state
            if 1 in pages_dict:
                p1 = pages_dict[1]
                paused = await p1.evaluate("() => Boolean(window.__AGY_PAUSED)")
                shared_state["paused"] = paused

                cfg_update = await p1.evaluate("() => Boolean(window.__AGY_CONFIG_UPDATE)")
                if cfg_update:
                    await p1.evaluate("() => { window.__AGY_CONFIG_UPDATE = false; }")
                    new_cfg = await p1.evaluate("() => window.__AGY_CONFIG")
                    
                    shared_state["mode"] = new_cfg.get("mode", "manual")
                    desired_tabs = int(new_cfg.get("tab_count", 1))
                    shared_state["tab_count"] = desired_tabs
                    
                    print(f"\n⚙️ [CONTROL CENTER UPDATE DETECTED]:")
                    print(f"   Mode: {shared_state['mode'].upper()} | Desired Parallel Tabs: {desired_tabs}")

                    # Update tabs config
                    for t in new_cfg.get("tabs", []):
                        t_idx = t.get("tabIndex", 0) + 1
                        shared_state["tabs_config"][t_idx] = {
                            "category": t.get("category", "Education & Skills"),
                            "candidate": t.get("candidate", "Sunmughan Swamy")
                        }
                        print(f"   Tab #{t_idx} -> Category: '{t.get('category')}' | Candidate: '{t.get('candidate')}'")

                    # Handle spawning new parallel tabs if increased
                    current_tab_ids = list(pages_dict.keys())
                    if desired_tabs > len(current_tab_ids):
                        for new_id in range(len(current_tab_ids) + 1, desired_tabs + 1):
                            new_page = await context.new_page()
                            await new_page.goto(TARGET_URL, wait_until="domcontentloaded")
                            await inject_hud(new_page)
                            pages_dict[new_id] = new_page
                            # Launch worker task for new tab
                            asyncio.create_task(tab_worker(new_id, new_page, shared_state, shared_state["contact_queue"]))
                            print(f"🚀 [NEW TAB SPAWNED]: Tab #{new_id} launched for parallel run!")
        except Exception:
            pass

        await asyncio.sleep(0.5)

async def main():
    print("=" * 70)
    print("   UNIVERSAL MULTI-TAB VOTING AUTOMATION & CONTROL HUB")
    print("   Innovate CG Portal | All Categories & All Candidates Supported")
    print("=" * 70)

    csv_path = get_target_csv()
    print(f"\n[*] CSV Source File: {csv_path}")
    contacts, skipped = load_contacts_from_any_csv(csv_path)
    print(f"[*] Valid Contacts Loaded: {len(contacts)}")
    if skipped > 0:
        print(f"[*] Skipped {skipped} rows without 10-digit Indian phone or missing name/email.")

    if not contacts:
        print("[!] No valid contacts found. Please check your CSV file.")
        return

    # Load persistent progress
    progress = load_progress(csv_path)
    submitted_set = set(progress["submitted_phones"])
    duplicate_set = set(progress["duplicate_phones"])
    already_processed = submitted_set | duplicate_set

    if already_processed:
        print("\n" + "*" * 70)
        print("📌 [PROGRESS MEMORIZATION ACTIVE]")
        print(f"   ✓ Already Submitted Successfully : {len(submitted_set)}")
        print(f"   ✓ Previously Marked Duplicates: {len(duplicate_set)}")
        print("   ✓ Bot will automatically SKIP all previously processed contacts!")
        print("*" * 70)

    remaining = [c for c in contacts if c["phone"] not in already_processed]
    print(f"[*] Remaining Contacts to Process: {len(remaining)} / {len(contacts)}")

    if not remaining:
        print("\n🎉 ALL contacts in this CSV file have already been processed and submitted!")
        return

    # Initialize async queue
    contact_queue = asyncio.Queue()
    for c in remaining:
        await contact_queue.put(c)

    # Shared state
    shared_state = {
        "paused": False,
        "stop_requested": False,
        "mode": "manual",
        "tab_count": 1,
        "tabs_config": {
            1: {"category": "Education & Skills", "candidate": "Sunmughan Swamy"}
        },
        "submitted_phones": submitted_set,
        "duplicate_phones": duplicate_set,
        "already_processed": set(already_processed),
        "progress": progress,
        "contact_queue": contact_queue
    }

    TARGET_URL = "https://innovatecg.in/voting"
    print(f"\n[*] Target Website: {TARGET_URL}")
    print("[*] Launching Chromium browser with Control Center HUD...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(no_viewport=True)

        # Tab #1 initialization
        page1 = await context.new_page()
        await page1.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        await page1.wait_for_timeout(1000)
        await inject_hud(page1)

        pages_dict = {1: page1}

        print("\n" + "=" * 70)
        print("⚡ INTERACTIVE CONTROL CENTER ACTIVE IN BROWSER:")
        print("1. Click the floating '⚙️ Control Center' button on screen at any time")
        print("2. The run will PAUSE automatically while you configure")
        print("3. Select ANY Category, Search ANY Candidate, or choose Parallel Tabs (1 to 5)!")
        print("4. Switch between Manual Run and Auto Run")
        print("5. Click 'Apply Settings & Resume' to resume execution!")
        print("=" * 70 + "\n")

        # Start HUD poller and initial Tab #1 worker
        poller_task = asyncio.create_task(hud_poller(pages_dict, shared_state, context))
        worker1_task = asyncio.create_task(tab_worker(1, page1, shared_state, contact_queue))

        # Wait until queue is completely processed
        await contact_queue.join()
        shared_state["stop_requested"] = True
        await asyncio.sleep(1)

        poller_task.cancel()
        worker1_task.cancel()

        print("\n" + "=" * 70)
        print("DATA ENTRY FINISHED:")
        print(f"  ✓ Total Successful Votes  : {len(shared_state['submitted_phones'])}")
        print(f"  ✓ Total Duplicates Skipped: {len(shared_state['duplicate_phones'])}")
        print(f"  ✓ Saved to 'automation_progress.json'")
        print("=" * 70)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
