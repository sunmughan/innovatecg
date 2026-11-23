# Innovate CG Voting & Automated Data Entry Suite

An automated, browser-driven data entry system and web dashboard designed for reliable form automation on `innovatecg.in/voting` and custom web forms.

Supports semi-automated high-speed voting with human-in-the-loop CAPTCHA solving, automatic category and candidate targeting, Indian mobile number normalization, and a live DOM/network inspector.

---

## 🌟 Key Capabilities

### 1. ⚡ High-Speed Direct Voting Runner (`run_direct.py` & `start_automation.bat`)
- **Airtight Candidate Targeting**: Automatically switches to the **"Education & Skills"** category and clicks **"Vote Now"** on **"Sunmughan Swamy"** (`Digital Literacy and Skill Development Education`, `Durg`).
- **Strict Dialog Verification**: Confirms that the open modal belongs specifically to the target candidate and category before filling any data. Never submits votes to the default category or default candidate.
- **Auto Phone Normalization**: Automatically strips `+91`, country codes, spaces, and hyphens to extract the exact 10-digit Indian phone number required by the portal.
- **Human-in-the-Loop CAPTCHA**: Automatically focuses and highlights the CAPTCHA box (`4px solid #f59e0b`) so you only have to glance at the image, type the 4-6 characters, and click submit.
- **Auto-Advance Multi-Record Loop**: Detects modal closure upon successful vote submission, refreshes state, and instantly opens the next candidate modal.

### 2. 🌐 Interactive Web Dashboard (`app.py` & `run.bat`)
- **Drag-and-Drop CSV Upload**: Upload any CSV file. Automatically detects Name, Email, and Phone/Mobile columns.
- **Live DOM & Network Inspector**: Record any target website's network requests (`POST`/`GET`), payloads, and DOM clicks in real-time.
- **Auto Selector Discovery**: Detects CSS selectors for form fields automatically.

---

## 🚀 Quick Start (Windows)

### Option A: One-Click Automation Runner (Recommended)

1. Double-click **`start_automation.bat`** (or drag and drop your CSV file directly onto `start_automation.bat`).
2. A visible Chromium browser window will open to `https://innovatecg.in/voting`.
3. The bot selects **Education & Skills** -> **Sunmughan Swamy**, fills the contact info, and focuses the CAPTCHA field.
4. Type the CAPTCHA code and click **"Confirm & Cast Vote"**.
5. Once submitted, the bot immediately opens the next contact for Sunmughan Swamy automatically!

### Option B: Web Dashboard

1. Double-click **`run.bat`** or run:
   ```cmd
   .\venv\Scripts\activate
   python app.py
   ```
2. Open your browser to:
   - Dashboard: `http://localhost:5000`

---

## 📦 Installation & Setup

If setting up on a new machine:

```bash
# 1. Clone repository
git clone https://github.com/sunmughan/innovatecg.git
cd innovatecg

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser binaries
playwright install chromium
```

---

## 📂 Project Structure

```text
├── app.py                      # Flask web server, dashboard API, and Playwright worker
├── run_direct.py               # Standalone direct automation engine for innovatecg.in
├── start_automation.bat        # 1-click Windows launcher for direct runner
├── run.bat                     # 1-click Windows launcher for web dashboard
├── requirements.txt            # Python dependencies (Flask, Playwright, Pandas, etc.)
├── sample_contacts.csv         # Clean sample CSV format
├── templates/
│   ├── index.html              # Modern web dashboard UI with live log console
│   └── demo_form.html          # Mock local form for testing submissions
└── tests/                      # Verification and test scripts
    ├── test_category_toggle.py
    ├── test_multi_submission_loop.py
    └── inspect_dialog.py
```

---

## 📄 License
MIT License. Created for the Innovate CG Public Voting Initiative.
