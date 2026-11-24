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
    """
    Loads previous run progress with independent per-candidate checkpoints.
    Each candidate's run resumes from their own last finished row.
    """
    prog = {
        "csv_file": csv_name,
        "candidates": {},
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                prog["csv_file"] = data.get("csv_file", csv_name)
                # Backward-compatibility migration if older flat format was used
                if "submitted_phones" in data and "candidates" not in data:
                    prog["candidates"]["Sunmughan Swamy"] = {
                        "category": "Education & Skills",
                        "last_index": data.get("last_index", -1),
                        "submitted_phones": set(data.get("submitted_phones", [])),
                        "duplicate_phones": set(data.get("duplicate_phones", [])),
                        "submitted_count": len(data.get("submitted_phones", []))
                    }
                else:
                    for cand_name, c_data in data.get("candidates", {}).items():
                        prog["candidates"][cand_name] = {
                            "category": c_data.get("category", ""),
                            "last_index": c_data.get("last_index", -1),
                            "submitted_phones": set(c_data.get("submitted_phones", [])),
                            "duplicate_phones": set(c_data.get("duplicate_phones", [])),
                            "submitted_count": len(c_data.get("submitted_phones", []))
                        }
        except Exception as e:
            print(f"  [!] Note loading progress: {e}")
    return prog

def save_progress(prog):
    """Persists per-candidate checkpoints to disk atomically."""
    try:
        cand_dict = {}
        for cand_name, c_data in prog["candidates"].items():
            cand_dict[cand_name] = {
                "category": c_data.get("category", ""),
                "last_index": c_data.get("last_index", -1),
                "submitted_count": len(c_data.get("submitted_phones", set())),
                "duplicate_count": len(c_data.get("duplicate_phones", set())),
                "submitted_phones": sorted(list(c_data.get("submitted_phones", set()))),
                "duplicate_phones": sorted(list(c_data.get("duplicate_phones", set()))),
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        data = {
            "csv_file": prog["csv_file"],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "candidates": cand_dict
        }
        temp_file = PROGRESS_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        os.rename(temp_file, PROGRESS_FILE)
    except Exception as e:
        print(f"  [!] Failed to save progress file: {e}")

def get_or_create_candidate_progress(prog, candidate, category):
    """Ensures candidate has an active tracking object in progress."""
    if candidate not in prog["candidates"]:
        prog["candidates"][candidate] = {
            "category": category,
            "last_index": -1,
            "submitted_phones": set(),
            "duplicate_phones": set(),
            "submitted_count": 0
        }
    return prog["candidates"][candidate]

async def inject_hud(page, prog=None):
    """Injects the interactive Control Center HUD with live candidate checkpoints into the page."""
    try:
        checkpoints_summary = {}
        if prog:
            for cand_name, c_data in prog.get("candidates", {}).items():
                checkpoints_summary[cand_name] = {
                    "last_index": c_data.get("last_index", -1),
                    "submitted_count": len(c_data.get("submitted_phones", set())),
                    "duplicate_count": len(c_data.get("duplicate_phones", set()))
                }
        await page.evaluate(f"window.__AGY_CHECKPOINTS = {json.dumps(checkpoints_summary)};")
        await page.evaluate(f"window.__AGY_CATALOG = {json.dumps(CATALOG)};")
        if os.path.exists(HUD_SCRIPT_FILE):
            with open(HUD_SCRIPT_FILE, "r", encoding="utf-8") as f:
                hud_code = f.read()
            await page.evaluate(hud_code)
    except Exception:
        pass

async def dismiss_announcement_popup(page):
    """Automatically detects and closes the 'Voting Lines Close Tonight' announcement popup if visible."""
    try:
        popup = page.locator('div.fixed.inset-0:has-text("IMPORTANT ANNOUNCEMENT"), div.fixed.inset-0:has-text("Voting Lines Close")').first
        if await popup.is_visible():
            close_btn = popup.locator('button[aria-label="Close"], button:has-text("Close"), button:has-text("Vote Now")').first
            if await close_btn.is_visible():
                await close_btn.click()
                await page.wait_for_timeout(500)
    except Exception:
        pass

async def open_candidate_modal(page, candidate_name, category_name):
    """
    Ensures the voting modal is opened specifically for the designated candidate and category.
    Guarantees no data is submitted to any wrong category or wrong candidate.
    """
    # 0. Always dismiss any announcement popup first so it doesn't block clicks
    await dismiss_announcement_popup(page)

    name_field = page.locator('input[name="name"]').first
    
    # Check if modal is already open
    if await name_field.is_visible():
        dialog = page.locator('div.fixed.inset-0, div[role="dialog"]').first
        txt = (await dialog.inner_text()).lower()
        if candidate_name.lower() in txt:
            return True
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

async def get_next_contact_for_candidate(candidate, category, shared_state, contacts):
    """
    Safely retrieves the next unsubmitted contact for a specific candidate.
    Advances from that candidate's saved checkpoint without duplicate collisions.
    """
    prog = shared_state["progress"]
    lock = shared_state["candidate_locks"].setdefault(candidate, asyncio.Lock())

    async with lock:
        c_prog = get_or_create_candidate_progress(prog, candidate, category)
        cursor = shared_state["candidate_cursors"].setdefault(candidate, c_prog["last_index"] + 1)

        while cursor < len(contacts):
            c = contacts[cursor]
            phone = c["phone"]
            # Check if this phone has already voted or failed for this candidate
            if phone not in c_prog["submitted_phones"] and phone not in c_prog["duplicate_phones"]:
                shared_state["candidate_cursors"][candidate] = cursor + 1
                return cursor, c
            cursor += 1
            shared_state["candidate_cursors"][candidate] = cursor

    return None, None

async def tab_worker(tab_id, page, shared_state, contacts):
    """
    Runs continuous automated voting for an individual tab session.
    Respects candidate checkpoints, parallel isolation, and global pause.
    """
    TARGET_URL = "https://innovatecg.in/voting"
    print(f"[Tab #{tab_id}] Online.")

    while not shared_state.get("stop_requested", False):
        # 1. Global Pause Gate (Paused while Control Center overlay is open)
        while shared_state.get("paused", False):
            await asyncio.sleep(0.5)

        # 2. Get current assigned target for this tab
        tab_cfg = shared_state["tabs_config"].get(tab_id, {
            "category": "Education & Skills",
            "candidate": "Sunmughan Swamy"
        })
        category = tab_cfg["category"]
        candidate = tab_cfg["candidate"]

        # 3. Pull next record from this candidate's specific checkpoint
        row_idx, contact = await get_next_contact_for_candidate(candidate, category, shared_state, contacts)
        if contact is None:
            print(f"[Tab #{tab_id}] Completed all contacts for candidate '{candidate}'!")
            break

        phone = contact["phone"]
        name = contact["name"]
        row_num = row_idx + 1

        print(f"\n[Tab #{tab_id}] [Row #{row_num}/{len(contacts)}] Processing: {name} (Phone: {phone}) -> Candidate: '{candidate}' [{category}]")
        
        try:
            # Ensure announcement popup is dismissed
            await dismiss_announcement_popup(page)

            # Re-inject HUD with latest checkpoints
            await inject_hud(page, shared_state["progress"])

            # Ensure correct candidate modal is open
            await open_candidate_modal(page, candidate_name=candidate, category_name=category)

            # Re-inject HUD after modal opens
            await inject_hud(page, shared_state["progress"])

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

            # Mode indicator
            mode = shared_state.get("mode", "manual")
            if mode == "auto":
                print(f"  [Tab #{tab_id}] 🤖 Auto Mode ready for final touch.")

            print(f"  [Tab #{tab_id}] 👉 Captcha focused for {name} ({candidate}). Waiting for vote cast...")

            # Waiting loop (detect submit, duplicate, skip, or pause)
            start_t = time.time()
            outcome = "timeout"
            err_detail = ""

            while time.time() - start_t < 90:
                # Check pause state
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
                    try:
                        success_box = page.locator('div.bg-emerald-50').first
                        success_txt = (await success_box.inner_text()).replace('\n', ' ').strip()
                        print(f"\n  ✅ [Tab #{tab_id}] Portal Success Message: \"{success_txt}\"")
                    except Exception:
                        pass
                    # Wait 2 seconds as requested so the user/admin can see the confirmation
                    print(f"  ⏳ Waiting 2 seconds after submission to verify portal state...")
                    await asyncio.sleep(2.0)
                    outcome = "success"
                    await done_btn.click()
                    await page.wait_for_timeout(600)
                    break

                # Check if modal closed upon submit
                if not (await name_field.is_visible()):
                    outcome = "success"
                    print(f"  ⏳ Vote modal closed. Waiting 2 seconds to ensure state sync...")
                    await asyncio.sleep(2.0)
                    break

                # Check for portal error banner (div.bg-red-50, div.animate-shake, div.text-red-700)
                try:
                    error_banner = page.locator('div.bg-red-50, div.animate-shake').first
                    if await error_banner.is_visible():
                        err_msg = (await error_banner.inner_text()).strip()
                        
                        # Print the exact portal message live to terminal
                        print(f"\n  📢 [Tab #{tab_id}] FORM RESPONSE FROM PORTAL: \"{err_msg}\"")
                        print(f"  ⏳ Pausing 2 seconds to inspect portal error message...")
                        await asyncio.sleep(2.0)

                        # 1. Check IP restriction first
                        ip_words = ["ip restricted", "ip address", "network limit", "rate limit", "too many", "maximum votes from this ip", "ip limit", "ip block"]
                        if any(w in err_msg.lower() for w in ip_words):
                            outcome = "ip_restricted"
                            err_detail = err_msg
                            break

                        # 2. Check for captcha code error (user just needs to re-enter code)
                        if any(w in err_msg.lower() for w in ["captcha", "verification code", "security code", "incorrect code", "enter code"]):
                            print(f"  ⚠️ [CAPTCHA MISMATCH]: {err_msg} -> Highlighting captcha box for re-entry...")
                            if await code_field.is_visible():
                                try:
                                    await page.evaluate("(el) => { el.style.outline = '4px solid #ef4444'; el.value = ''; el.focus(); }", await code_field.element_handle())
                                except Exception:
                                    await code_field.focus()
                            await asyncio.sleep(1.0)
                            continue

                        # 3. Check duplicate phone / voter
                        duplicate_words = ["already", "duplicate", "voted", "limit", "one vote", "1 vote", "registered", "policy", "exists"]
                        if any(w in err_msg.lower() for w in duplicate_words):
                            outcome = "duplicate"
                            err_detail = err_msg
                            break

                        # 4. Any other server error (e.g. invalid email / dummy phone)
                        outcome = "other_error"
                        err_detail = err_msg
                        break
                except Exception:
                    pass

                await asyncio.sleep(0.4)

            # Update candidate-specific checkpoint
            c_prog = get_or_create_candidate_progress(shared_state["progress"], candidate, category)

            if outcome == "success":
                c_prog["submitted_phones"].add(phone)
                c_prog["last_index"] = max(c_prog["last_index"], row_idx)
                save_progress(shared_state["progress"])
                print(f"  🎉 [Tab #{tab_id}] SUCCESS: Vote cast for '{candidate}' by {name}!")
                print(f"     [Checkpoint: Row #{c_prog['last_index'] + 1} | Total Votes: {len(c_prog['submitted_phones'])}]")

            elif outcome == "ip_restricted":
                print(f"\n🚨 [Tab #{tab_id}] IP RESTRICTION ALERT FROM PORTAL: {err_detail}")
                print(f"   👉 Cause: The portal has rate-limited or restricted your current IP network.")
                print(f"   💡 QUICK FIX (Takes 5 seconds):")
                print(f"      1. Disconnect and reconnect your Mobile Hotspot (or turn Airplane Mode ON for 5s then OFF on your phone).")
                print(f"         In India (Jio/Airtel/Vi), this gives you a clean dynamic Indian IP instantly!")
                print(f"      2. Or enter a proxy in 'proxy.txt' (format: http://host:port).")
                print(f"   ⏸️ Automation paused. Row #{row_num} preserved. Reconnect IP and close menu to resume!\n")
                
                # Reset cursor for this candidate so this contact is retried after IP change
                shared_state["candidate_cursors"][candidate] = row_idx
                
                try:
                    close_btn = page.locator('div.fixed.inset-0 button').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(600)
                except Exception:
                    pass
                
                shared_state["paused"] = True

            elif outcome == "duplicate":
                c_prog["duplicate_phones"].add(phone)
                c_prog["last_index"] = max(c_prog["last_index"], row_idx)
                save_progress(shared_state["progress"])
                print(f"  ⚠️ [Tab #{tab_id}] DUPLICATE FOR '{candidate}': {err_detail}")
                print(f"  ⏭️ Mobile '{phone}' already voted in {category}. Rolling next...")
                try:
                    close_btn = page.locator('div.fixed.inset-0 button').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

            elif outcome == "other_error":
                print(f"  ⚠️ [Tab #{tab_id}] PORTAL REJECTED ROW: {err_detail}")
                print(f"  ⏭️ Moving past Row #{row_num} and rolling to next contact...")
                c_prog["last_index"] = max(c_prog["last_index"], row_idx)
                save_progress(shared_state["progress"])
                try:
                    close_btn = page.locator('div.fixed.inset-0 button').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

            elif outcome == "human_skip":
                c_prog["last_index"] = max(c_prog["last_index"], row_idx)
                save_progress(shared_state["progress"])
                print(f"  ⏭️ [Tab #{tab_id}] Skipped by user. Checkpoint moved to Row #{row_num}...")
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

    print(f"[Tab #{tab_id}] Worker finished execution.")

async def hud_poller(pages_dict, shared_state, context, contacts):
    """
    Listens for floating Control Center HUD clicks, pause states, and configuration updates across all tabs.
    Dynamically spawns or manages parallel tabs and keeps candidate checkpoints synchronized.
    """
    TARGET_URL = "https://innovatecg.in/voting"
    while not shared_state.get("stop_requested", False):
        try:
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
                    
                    print(f"\n⚙️ [CONTROL CENTER SETTINGS APPLIED]:")
                    print(f"   Mode: {shared_state['mode'].upper()} | Active Parallel Tabs: {desired_tabs}")

                    # Update per-tab configuration
                    for t in new_cfg.get("tabs", []):
                        t_idx = t.get("tabIndex", 0) + 1
                        cand = t.get("candidate", "Sunmughan Swamy")
                        cat = t.get("category", "Education & Skills")
                        shared_state["tabs_config"][t_idx] = {
                            "category": cat,
                            "candidate": cand
                        }
                        c_prog = get_or_create_candidate_progress(shared_state["progress"], cand, cat)
                        next_row = c_prog["last_index"] + 2 if c_prog["last_index"] >= 0 else 1
                        print(f"   Tab #{t_idx} -> Target: '{cand}' [{cat}] | Resumes from CSV Row: #{next_row} ({c_prog.get('submitted_count', 0)} votes)")

                    # Dynamically spawn new tabs if parallel tab count was increased
                    current_tab_ids = list(pages_dict.keys())
                    if desired_tabs > len(current_tab_ids):
                        for new_id in range(len(current_tab_ids) + 1, desired_tabs + 1):
                            new_page = await context.new_page()
                            await new_page.goto(TARGET_URL, wait_until="domcontentloaded")
                            await inject_hud(new_page, shared_state["progress"])
                            pages_dict[new_id] = new_page
                            asyncio.create_task(tab_worker(new_id, new_page, shared_state, contacts))
                            print(f"🚀 [PARALLEL TAB LAUNCHED]: Tab #{new_id} online!")
        except Exception:
            pass

        await asyncio.sleep(0.5)

async def main():
    print("=" * 70)
    print("   UNIVERSAL MULTI-TAB VOTING AUTOMATION & CONTROL HUB")
    print("   Independent Candidate Checkpoints & Parallel CSV Resumption")
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

    # Load persistent per-candidate checkpoints
    progress = load_progress(csv_path)

    print("\n" + "=" * 70)
    print("📌 [PER-CANDIDATE CHECKPOINTS SAVED]:")
    if progress["candidates"]:
        for cand_name, c_data in progress["candidates"].items():
            last_i = c_data.get("last_index", -1)
            next_row = last_i + 2 if last_i >= 0 else 1
            votes = len(c_data.get("submitted_phones", set()))
            dups = len(c_data.get("duplicate_phones", set()))
            cat = c_data.get("category", "General")
            print(f"   • {cand_name} [{cat}]:")
            print(f"     - Last Finished Row: #{last_i + 1} | Next Resume Row: #{next_row}")
            print(f"     - Confirmed Votes: {votes} | Duplicates: {dups}")
    else:
        print("   (No previous runs yet. Starting fresh from Row #1)")
    print("=" * 70)

    # Shared state
    shared_state = {
        "paused": False,
        "stop_requested": False,
        "mode": "manual",
        "tab_count": 1,
        "tabs_config": {
            1: {"category": "Education & Skills", "candidate": "Sunmughan Swamy"}
        },
        "candidate_cursors": {},
        "candidate_locks": {},
        "progress": progress
    }

    # Check for optional proxy configuration
    proxy_config = None
    proxy_server = None
    for arg in sys.argv[1:]:
        if arg.startswith("--proxy="):
            proxy_server = arg.split("=", 1)[1].strip()

    if not proxy_server and os.path.exists("proxy.txt"):
        try:
            with open("proxy.txt", "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip() and not l.strip().startswith("#")]
                if lines:
                    proxy_server = lines[0]
        except Exception:
            pass

    if proxy_server:
        print(f"\n🌐 [PROXY ENABLED]: Routing browser traffic through proxy: {proxy_server}")
        proxy_config = {"server": proxy_server}
    else:
        print("\n🌐 [NETWORK]: Direct connection. (Tip: Reconnect mobile hotspot anytime to get fresh IP!)")

    TARGET_URL = "https://innovatecg.in/voting"
    print(f"\n[*] Target Website: {TARGET_URL}")
    print("[*] Launching Chromium browser with Control Center HUD...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"],
            proxy=proxy_config if proxy_config else None
        )
        context = await browser.new_context(no_viewport=True)

        # Tab #1 initialization
        page1 = await context.new_page()
        await page1.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        await page1.wait_for_timeout(1000)
        await dismiss_announcement_popup(page1)
        await inject_hud(page1, progress)

        pages_dict = {1: page1}

        print("\n" + "=" * 70)
        print("⚡ INTERACTIVE CONTROL CENTER ACTIVE IN BROWSER:")
        print("1. Click the floating '⚙️ Control Center' button on screen at any time")
        print("2. The run will PAUSE automatically while you configure")
        print("3. Configure Parallel Tabs (1 to 5) and choose each candidate's target")
        print("4. Each candidate automatically starts/resumes from their OWN CSV checkpoint!")
        print("5. Click 'Apply Settings & Resume' to continue execution!")
        print("=" * 70 + "\n")

        # Start HUD poller and initial Tab #1 worker
        poller_task = asyncio.create_task(hud_poller(pages_dict, shared_state, context, contacts))
        worker1_task = asyncio.create_task(tab_worker(1, page1, shared_state, contacts))

        # Keep running until user terminates or contacts complete
        try:
            await worker1_task
        except asyncio.CancelledError:
            pass

        shared_state["stop_requested"] = True
        poller_task.cancel()

        print("\n" + "=" * 70)
        print("DATA ENTRY SESSION COMPLETED:")
        for cand_name, c_data in shared_state["progress"]["candidates"].items():
            print(f"  • {cand_name}: {len(c_data.get('submitted_phones', set()))} votes recorded (Checkpoint: Row #{c_data.get('last_index', -1) + 1})")
        print("  ✓ All progress saved to 'automation_progress.json'")
        print("=" * 70)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
