import os
import json
import time

PROGRESS_FILE = "test_checkpoints_progress.json"

def load_progress(csv_name):
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
                for cand_name, c_data in data.get("candidates", {}).items():
                    prog["candidates"][cand_name] = {
                        "category": c_data.get("category", ""),
                        "last_index": c_data.get("last_index", -1),
                        "submitted_phones": set(c_data.get("submitted_phones", [])),
                        "duplicate_phones": set(c_data.get("duplicate_phones", [])),
                        "submitted_count": len(c_data.get("submitted_phones", []))
                    }
        except Exception:
            pass
    return prog

def save_progress(prog):
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
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def test_per_candidate_checkpoints():
    prog = load_progress("mobile.csv")
    
    # Candidate 1: Sunmughan Swamy (Education & Skills)
    c1 = prog["candidates"].setdefault("Sunmughan Swamy", {
        "category": "Education & Skills",
        "last_index": -1,
        "submitted_phones": set(),
        "duplicate_phones": set()
    })
    # Simulate processing up to row 10
    for i in range(10):
        c1["submitted_phones"].add(f"98000000{i:02d}")
        c1["last_index"] = i
    save_progress(prog)
    
    # Candidate 2: Rahul Agrawal (Science & Tech)
    c2 = prog["candidates"].setdefault("Rahul Kumar Agrawal", {
        "category": "Science & Tech",
        "last_index": -1,
        "submitted_phones": set(),
        "duplicate_phones": set()
    })
    # Simulate processing up to row 4
    for i in range(5):
        c2["submitted_phones"].add(f"98000000{i:02d}")
        c2["last_index"] = i
    save_progress(prog)
    
    # Reload and verify
    reloaded = load_progress("mobile.csv")
    swamy = reloaded["candidates"]["Sunmughan Swamy"]
    rahul = reloaded["candidates"]["Rahul Kumar Agrawal"]
    
    print("Swamy Checkpoint Index:", swamy["last_index"], "Votes:", len(swamy["submitted_phones"]))
    print("Rahul Checkpoint Index:", rahul["last_index"], "Votes:", len(rahul["submitted_phones"]))
    
    assert swamy["last_index"] == 9, "Swamy last_index should be 9 (Row 10)"
    assert len(swamy["submitted_phones"]) == 10
    
    assert rahul["last_index"] == 4, "Rahul last_index should be 4 (Row 5)"
    assert len(rahul["submitted_phones"]) == 5
    
    # Notice that the same phone numbers (e.g. 9800000000) voted for BOTH candidates without collision!
    shared_numbers = swamy["submitted_phones"] & rahul["submitted_phones"]
    assert len(shared_numbers) == 5, f"Expected 5 shared valid category votes, got {len(shared_numbers)}"
    print(f"Verified: {len(shared_numbers)} contacts voted in both categories legally under 1-vote-per-category rule!")
    
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    print("\nPER-CANDIDATE CHECKPOINTS VERIFIED 100% SUCCESFULLY!")

if __name__ == "__main__":
    test_per_candidate_checkpoints()
