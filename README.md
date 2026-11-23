# Innovate CG Voting & Automated Data Entry Suite

An automated, browser-driven data entry system and web dashboard designed for high-speed, reliable form automation on `innovatecg.in/voting` and custom web forms.

Supports semi-automated and automated multi-tab voting, live in-browser Control Center overlay HUD, all 15 categories, 337 candidates with instant search, duplicate mobile protection, and persistent progress memorization.

---

## 🌟 Key Capabilities

### 1. ⚙️ In-Browser Control Center & Multi-Tab Hub (`overlay_hud.js`)
- **Floating Control Center Button**: Always available at the top-right of your Chromium window (`⚙️ Control Center`).
- **Auto-Pause on Open**: Whenever the Control Center is opened, automation **automatically pauses** across all running tabs, allowing you to reconfigure without missing a beat.
- **Mode Switching**: Toggle between **Manual Run** (semi-auto with human captcha solving) and **Auto Run**.
- **Parallel Multi-Tab Execution**: Choose between **1 to 5+ parallel tabs** in the Chromium browser. Each tab runs independently with its own designated category and target candidate!
- **Instant Candidate Search**: Search across **all 337 candidates** and **15 categories** in real time with live autocomplete.
- **Skip Record Button**: 1-click skip button (`⏭️ Skip Record`) available on every screen.

### 2. ⚡ High-Speed Direct Voting Runner (`run_direct.py` & `start_automation.bat`)
- **Universal Category & Candidate Targeting**: Pre-configured for **"Sunmughan Swamy"** (`Education & Skills`), but fully reconfigurable on-the-fly to any candidate in any category.
- **Strict Dialog Verification**: Confirms that the open modal belongs specifically to the target candidate before filling data.
- **Auto Phone Normalization**: Automatically strips `+91`, spaces, and hyphens to extract the exact 10-digit Indian phone number required by the portal.
- **Human-in-the-Loop CAPTCHA**: Automatically focuses and highlights the CAPTCHA box (`4px solid #f59e0b`) for rapid typing.
- **Auto-Advance Multi-Record Loop**: Detects modal closure upon successful vote submission, refreshes state, and instantly opens the next candidate modal.

### 3. 🛡️ Duplicate Mobile Detection & Roll-Forward
- **CSV Pre-Check**: Skips repeated phone numbers in the CSV automatically.
- **Live Portal Error Detection**: Instantly detects red portal alerts (`already voted in this category` or `1 vote per category policy`), auto-dismisses the modal, and rolls forward to the next fresh contact immediately.

### 4. 📌 Persistent Session Progress Memorization (`automation_progress.json`)
- Automatically saves state after every single vote.
- If interrupted or closed, the next launch automatically skips already submitted contacts and resumes directly from the next unsubmitted row.

### 5. 🌐 Interactive Web Dashboard (`app.py` & `run.bat`)
- Drag-and-drop CSV upload, data preview, and live DOM/network inspector.

---

## 🚀 Quick Start (Windows)

### 1-Click Automation Runner

1. Double-click **`start_automation.bat`** (or drag and drop your CSV file directly onto `start_automation.bat`).
2. A visible Chromium browser window will open to `https://innovatecg.in/voting`.
3. To change categories, candidates, run mode, or parallel tabs:
   - Click the floating **`⚙️ Control Center`** button in the browser window.
   - Automation automatically pauses.
   - Choose your run mode (**Manual Run** or **Auto Run**).
   - Select number of parallel tabs (1 to 5 tabs).
   - Select category and search candidate for each tab.
   - Click **`🚀 Apply Settings & Resume`**!
4. The bot opens the designated forms, fills details, and highlights the CAPTCHA.
5. In Manual Mode: Type the CAPTCHA and click **"Confirm & Cast Vote"**.
6. The bot detects submission and immediately rolls to the next contact!

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
├── run_direct.py               # Asynchronous multi-tab direct automation runner
├── overlay_hud.js              # In-browser interactive floating Control Center HUD
├── candidates_catalog.json     # Indexed catalog of 15 categories & 337 candidates
├── start_automation.bat        # 1-click Windows launcher for direct runner
├── run.bat                     # 1-click Windows launcher for web dashboard
├── requirements.txt            # Python dependencies (Flask, Playwright, Pandas, etc.)
├── sample_contacts.csv         # Clean sample CSV format
├── templates/
│   ├── index.html              # Modern web dashboard UI with live log console
│   └── demo_form.html          # Mock local form for testing submissions
└── tests/                      # Verification and test scripts
    ├── test_overlay_hud.py
    ├── test_async_multi_tab_runner.py
    ├── test_progress_and_duplicate.py
    └── scrape_candidates.py
```

---

## 📄 License
MIT License. Created for the Innovate CG Public Voting Initiative.
