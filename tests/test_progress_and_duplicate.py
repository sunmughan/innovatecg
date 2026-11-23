import os
import json
import time

PROGRESS_FILE = "test_automation_progress.json"

def load_progress(csv_name):
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "csv_file": data.get("csv_file", csv_name),
                    "last_index": data.get("last_index", -1),
                    "submitted_phones": set(data.get("submitted_phones", [])),
                    "duplicate_phones": set(data.get("duplicate_phones", [])),
                    "submitted_count": data.get("submitted_count", 0)
                }
        except Exception:
            pass
    return {
        "csv_file": csv_name,
        "last_index": -1,
        "submitted_phones": set(),
        "duplicate_phones": set(),
        "submitted_count": 0
    }

def save_progress(prog):
    data = {
        "csv_file": prog["csv_file"],
        "last_index": prog["last_index"],
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "submitted_phones": sorted(list(prog["submitted_phones"])),
        "duplicate_phones": sorted(list(prog["duplicate_phones"])),
        "submitted_count": len(prog["submitted_phones"])
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def test_resume_and_duplicate():
    # Setup initial mock progress
    prog = load_progress("test.csv")
    prog["submitted_phones"].add("9383465787") # 1st contact already done
    prog["last_index"] = 0
    save_progress(prog)

    # Now reload
    reloaded = load_progress("test.csv")
    assert "9383465787" in reloaded["submitted_phones"], "Failed to reload submitted phone!"

    contacts = [
        {"name": "Sathish", "phone": "9383465787"}, # Already submitted
        {"name": "Malathi", "phone": "8485195442"}, # New
        {"name": "Malathi Duplicate", "phone": "8485195442"}, # Duplicate in CSV
        {"name": "Chithra", "phone": "8055362917"}  # New
    ]

    processed = []
    seen = set(reloaded["submitted_phones"]) | set(reloaded["duplicate_phones"])

    for i, c in enumerate(contacts):
        p = c["phone"]
        if p in seen:
            print(f"Skipping duplicate/already processed: {c['name']} ({p})")
            continue
        seen.add(p)
        reloaded["submitted_phones"].add(p)
        reloaded["last_index"] = i
        save_progress(reloaded)
        processed.append(c["name"])

    assert processed == ["Malathi", "Chithra"], f"Expected ['Malathi', 'Chithra'], got {processed}"
    print("Test passed! Resumed correctly and skipped duplicates:", processed)

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

if __name__ == "__main__":
    test_resume_and_duplicate()
