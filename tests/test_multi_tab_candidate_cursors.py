import asyncio
import json

def test_candidate_cursors():
    contacts = [{"name": f"Contact_{i}", "phone": f"98000000{i:02d}"} for i in range(20)]
    
    prog = {
        "csv_file": "test.csv",
        "candidates": {
            "Sunmughan Swamy": {
                "category": "Education & Skills",
                "last_index": 5, # Finished rows 0-5
                "submitted_phones": {f"98000000{i:02d}" for i in range(6)},
                "duplicate_phones": set()
            },
            "Candidate B": {
                "category": "Science & Tech",
                "last_index": 2, # Finished rows 0-2
                "submitted_phones": {f"98000000{i:02d}" for i in range(3)},
                "duplicate_phones": set()
            }
        }
    }
    
    candidate_cursors = {}
    
    def get_next_contact(candidate, category):
        c_prog = prog["candidates"].setdefault(candidate, {
            "category": category,
            "last_index": -1,
            "submitted_phones": set(),
            "duplicate_phones": set()
        })
        cursor = candidate_cursors.setdefault(candidate, c_prog["last_index"] + 1)
        while cursor < len(contacts):
            c = contacts[cursor]
            p = c["phone"]
            if p not in c_prog["submitted_phones"] and p not in c_prog["duplicate_phones"]:
                candidate_cursors[candidate] = cursor + 1
                return cursor, c
            cursor += 1
            candidate_cursors[candidate] = cursor
        return None, None

    # Tab 1 for Sunmughan Swamy
    idx1, c1 = get_next_contact("Sunmughan Swamy", "Education & Skills")
    print(f"Sunmughan Swamy next row: {idx1} -> {c1['name']}")
    assert idx1 == 6, f"Expected row 6 for Swamy, got {idx1}"

    # Tab 2 for Candidate B
    idx2, c2 = get_next_contact("Candidate B", "Science & Tech")
    print(f"Candidate B next row: {idx2} -> {c2['name']}")
    assert idx2 == 3, f"Expected row 3 for Candidate B, got {idx2}"

    # Simulate submission
    prog["candidates"]["Sunmughan Swamy"]["last_index"] = idx1
    prog["candidates"]["Sunmughan Swamy"]["submitted_phones"].add(c1["phone"])

    prog["candidates"]["Candidate B"]["last_index"] = idx2
    prog["candidates"]["Candidate B"]["submitted_phones"].add(c2["phone"])

    # Next iteration for both
    idx1_next, _ = get_next_contact("Sunmughan Swamy", "Education & Skills")
    idx2_next, _ = get_next_contact("Candidate B", "Science & Tech")

    assert idx1_next == 7
    assert idx2_next == 4
    print("Multi-tab independent cursor advancement passed successfully!")

if __name__ == "__main__":
    test_candidate_cursors()
