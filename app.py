import os
import sys
import time
import json
import threading
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

flow_lock = threading.Lock()
flow_state = {
    "is_recording": False,
    "is_replaying": False,
    "stop_requested": False,
    "target_url": "https://innovatecg.in/voting",
    "recorded_steps": [],
    "total": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "new_logs": [],
    "results": []
}

active_recording_browser = None

FLOW_RECORDER_JS = """
(function() {
  if (window.__FLOW_RECORDER_INSTALLED__) return;
  window.__FLOW_RECORDER_INSTALLED__ = true;

  let stepCount = 0;

  // Floating banner
  const banner = document.createElement('div');
  banner.id = '__flow_banner__';
  banner.innerHTML = `
    <div style="position:fixed; top:12px; right:12px; z-index:2147483647; background:#0f172a; color:#f8fafc; padding:12px 18px; border-radius:10px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; box-shadow:0 8px 30px rgba(0,0,0,0.6); border:2px solid #ef4444; font-size:13px; display:flex; align-items:center; gap:10px;">
      <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#ef4444; box-shadow:0 0 10px #ef4444;"></span>
      <span><strong>RECORDING FLOW:</strong> <span id="__step_count_text__">Perform actions in this window...</span></span>
    </div>
  `;
  document.documentElement.appendChild(banner);

  function updateBanner(msg) {
    const el = document.getElementById('__step_count_text__');
    if (el) el.innerText = msg;
  }

  function getSelector(el) {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
    try {
      const name = el.getAttribute('name');
      if (name) return el.tagName.toLowerCase() + '[name="' + name + '"]';

      const placeholder = el.getAttribute('placeholder');
      if (placeholder) return el.tagName.toLowerCase() + '[placeholder*="' + placeholder.trim().substring(0, 20) + '" i]';

      const btn = el.closest('button, input[type="submit"], input[type="button"], [role="button"], a');
      if (btn) {
        const btnText = (btn.innerText || btn.value || '').trim().replace(/\\s+/g, ' ');
        if (btnText) {
          const card = btn.closest('[class*="card"], [class*="item"], div');
          const heading = card ? card.querySelector('h1, h2, h3, h4, strong') : null;
          if (heading && heading.innerText.trim() && !heading.contains(btn)) {
            const cardTitle = heading.innerText.trim().split('\\n')[0].substring(0, 30);
            return 'div:has-text("' + cardTitle + '") >> button:has-text("' + btnText + '")';
          }
          return 'button:has-text("' + btnText + '")';
        }
      }

      if (el.id && !el.id.match(/^:[a-z0-9]+:$/i)) return '#' + el.id;
      if (el.getAttribute('type')) return el.tagName.toLowerCase() + '[type="' + el.getAttribute('type') + '"]';

      return el.tagName.toLowerCase();
    } catch(e) {
      return el.tagName ? el.tagName.toLowerCase() : '';
    }
  }

  function detectFieldType(el) {
    try {
      const name = (el.getAttribute('name') || '').toLowerCase();
      const ph = (el.getAttribute('placeholder') || '').toLowerCase();
      const type = (el.getAttribute('type') || '').toLowerCase();
      const id = (el.id || '').toLowerCase();
      const all = name + ' ' + ph + ' ' + type + ' ' + id;

      if (all.includes('code') || all.includes('captcha')) return 'captcha';
      if (all.includes('phone') || all.includes('mobile') || all.includes('tel') || type === 'tel') return 'phone';
      if (all.includes('mail') || type === 'email') return 'email';
      if (all.includes('name')) return 'name';
      return 'fixed';
    } catch(e) {
      return 'fixed';
    }
  }

  function report(data) {
    if (window.recordFlowStep) {
      try {
        stepCount++;
        updateBanner('Recorded ' + stepCount + ' actions! (Latest: ' + data.description + ')');
        window.recordFlowStep(data);
      } catch(e) {
        console.error('report error', e);
      }
    }
  }

  document.addEventListener('click', function(e) {
    try {
      if (e.target.closest('#__flow_banner__')) return;
      const btn = e.target.closest('button, input[type="submit"], input[type="button"], [role="button"], a');
      if (btn) {
        const sel = getSelector(btn);
        const text = (btn.innerText || btn.value || '').trim();
        report({
          action: 'click',
          selector: sel,
          tag: btn.tagName.toLowerCase(),
          text: text,
          description: 'Click "' + (text ? text.substring(0, 30) : sel) + '"'
        });
      }
    } catch(err) {
      console.error(err);
    }
  }, true);

  const inputTimers = new Map();
  document.addEventListener('input', function(e) {
    try {
      if (e.target.closest('#__flow_banner__')) return;
      const el = e.target;
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
        clearTimeout(inputTimers.get(el));
        inputTimers.set(el, setTimeout(() => {
          const sel = getSelector(el);
          const fieldType = detectFieldType(el);
          const val = el.value || '';
          report({
            action: fieldType === 'captcha' ? 'captcha' : 'fill',
            selector: sel,
            tag: el.tagName.toLowerCase(),
            field: fieldType,
            value: val,
            description: fieldType === 'captcha' ? 'Captcha Code input' : ('Fill ' + fieldType.toUpperCase() + ' (' + sel + ')')
          });
        }, 500));
      }
    } catch(err) {
      console.error(err);
    }
  }, true);
})();
"""

def add_flow_log(text, level="info"):
    with flow_lock:
        timestamp = datetime.now().strftime("%H:%M:%S")
        flow_state["new_logs"].append({
            "text": f"[{timestamp}] {text}",
            "level": level
        })

def handle_recorded_step(data):
    with flow_lock:
        if flow_state["recorded_steps"]:
            last = flow_state["recorded_steps"][-1]
            if last.get("action") == data.get("action") and last.get("selector") == data.get("selector"):
                last["value"] = data.get("value")
                last["description"] = data.get("description")
                return

        step_num = len(flow_state["recorded_steps"]) + 1
        data["id"] = step_num
        flow_state["recorded_steps"].append(data)
        add_flow_log(f"Captured Step {step_num}: {data.get('description')}", "success")


def recording_worker(target_url):
    global active_recording_browser
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            with flow_lock:
                active_recording_browser = browser

            context = browser.new_context(no_viewport=True)
            context.expose_function("recordFlowStep", handle_recorded_step)
            context.add_init_script(FLOW_RECORDER_JS)

            page = context.new_page()

            add_flow_log(f"Opening {target_url} for capture. Perform your actions in the browser...", "info")
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            while True:
                with flow_lock:
                    if flow_state["stop_requested"]:
                        break
                try:
                    if all(p.is_closed() for p in context.pages):
                        break
                    time.sleep(0.5)
                except Exception:
                    break

            try:
                browser.close()
            except Exception:
                pass

    except Exception as e:
        add_flow_log(f"Recording error: {str(e)}", "error")
    finally:
        with flow_lock:
            flow_state["is_recording"] = False
            flow_state["stop_requested"] = False
            active_recording_browser = None
        add_flow_log(f"Capture finished. Recorded {len(flow_state['recorded_steps'])} steps.", "bold")


def replay_worker(config):
    global flow_state

    target_url = config.get("target_url")
    steps = config.get("steps", [])
    rows = config.get("rows", [])
    delay = float(config.get("delay", 2.0))

    add_flow_log(f"Starting Batch Replay for {len(rows)} records using {len(steps)} steps...", "bold")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            context = browser.new_context(no_viewport=True)
            page = context.new_page()

            for i, row in enumerate(rows):
                with flow_lock:
                    if flow_state["stop_requested"]:
                        add_flow_log("Batch replay stopped by user.", "warn")
                        break

                name_val = str(row.get("name", "")).strip()
                email_val = str(row.get("email", "")).strip()
                phone_val = str(row.get("phone", "")).strip()

                add_flow_log(f"[{i+1}/{len(rows)}] Processing: {name_val} ({phone_val})...", "info")

                result_entry = {
                    "name": name_val,
                    "email": email_val,
                    "phone": phone_val,
                    "status": "Success",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1000)

                    for step in steps:
                        action = step.get("action")
                        selector = step.get("selector")
                        field = step.get("field", "fixed")

                        if action == "click":
                            loc = page.locator(selector).first
                            if not loc.is_visible():
                                page.wait_for_timeout(1000)
                            if loc.is_visible():
                                loc.scroll_into_view_if_needed()
                                loc.click()
                                page.wait_for_timeout(1000)

                        elif action == "fill":
                            val_to_fill = ""
                            if field == "name":
                                val_to_fill = name_val
                            elif field == "email":
                                val_to_fill = email_val
                            elif field == "phone":
                                # Extract clean 10-digit phone
                                p_digits = re.sub(r"\D", "", phone_val)
                                val_to_fill = p_digits[-10:] if len(p_digits) >= 10 else phone_val
                            else:
                                val_to_fill = str(step.get("value", ""))

                            loc = page.locator(selector).first
                            loc.wait_for(state="visible", timeout=12000)
                            loc.fill(val_to_fill)
                            page.wait_for_timeout(300)

                        elif action == "captcha" or field == "captcha":
                            # Focus and highlight captcha box for user
                            loc = page.locator(selector).first
                            if loc.is_visible():
                                try:
                                    page.evaluate("(el) => { el.style.outline = '3px solid #f59e0b'; el.focus(); }", loc.element_handle())
                                except Exception:
                                    loc.focus()

                                add_flow_log(f"[{i+1}/{len(rows)}] Name, Phone & Email filled! Focus is on Captcha - enter the code & click Confirm...", "warn")

                                # Wait for user to solve captcha and submit (modal disappears when vote is cast)
                                for _ in range(120): # up to 60s
                                    with flow_lock:
                                        if flow_state["stop_requested"]:
                                            break
                                    if not loc.is_visible():
                                        break
                                    time.sleep(0.5)

                    # Post submit wait
                    page.wait_for_timeout(int(delay * 1000))

                    with flow_lock:
                        flow_state["success"] += 1
                        flow_state["processed"] += 1
                        flow_state["results"].append(result_entry)

                    add_flow_log(f"[{i+1}/{len(rows)}] Successfully submitted vote for {name_val}!", "success")

                except Exception as step_err:
                    err_msg = str(step_err).splitlines()[0]
                    result_entry["status"] = f"Failed: {err_msg}"
                    with flow_lock:
                        flow_state["failed"] += 1
                        flow_state["processed"] += 1
                        flow_state["results"].append(result_entry)

                    add_flow_log(f"[{i+1}/{len(rows)}] Error on {name_val}: {err_msg}", "error")

            try:
                browser.close()
            except Exception:
                pass

    except Exception as e:
        add_flow_log(f"Replay Fatal Error: {str(e)}", "error")
    finally:
        with flow_lock:
            flow_state["is_replaying"] = False
            flow_state["stop_requested"] = False
        add_flow_log("Batch automation finished.", "bold")


# ========================================================
# 2. ROUTES
# ========================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/flow/start-capture", methods=["POST"])
def start_flow_capture():
    global flow_state
    with flow_lock:
        if flow_state["is_recording"]:
            return jsonify({"status": "error", "message": "Capture is already active."}), 400
        if flow_state["is_replaying"]:
            return jsonify({"status": "error", "message": "Replay is currently running."}), 400

        data = request.json or {}
        target_url = (data.get("target_url") or "").strip()
        if not target_url:
            return jsonify({"status": "error", "message": "Please enter target website URL."}), 400

        flow_state["is_recording"] = True
        flow_state["stop_requested"] = False
        flow_state["target_url"] = target_url
        flow_state["recorded_steps"] = []
        flow_state["new_logs"] = []

    thread = threading.Thread(target=recording_worker, args=(target_url,), daemon=True)
    thread.start()
    return jsonify({"status": "recording_started", "url": target_url})

@app.route("/api/flow/stop-capture", methods=["POST"])
def stop_flow_capture():
    with flow_lock:
        if flow_state["is_recording"]:
            flow_state["stop_requested"] = True
            return jsonify({"status": "stopping_capture"})
    return jsonify({"status": "not_recording"})

@app.route("/api/flow/preset-innovatecg", methods=["POST"])
def preset_innovatecg():
    steps = [
        {
            "id": 1,
            "action": "click",
            "selector": 'button:has-text("Education & Skills")',
            "tag": "button",
            "text": "Education & Skills",
            "description": "Click 'Education & Skills' Category"
        },
        {
            "id": 2,
            "action": "click",
            "selector": 'div.rounded-3xl:has-text("Sunmughan Swamy") >> button:has-text("Vote Now")',
            "tag": "button",
            "text": "Vote Now",
            "description": "Click 'Vote Now' for Sunmughan Swamy"
        },
        {
            "id": 3,
            "action": "fill",
            "selector": 'input[name="name"]',
            "tag": "input",
            "field": "name",
            "value": "",
            "description": "Fill NAME (input[name='name'])"
        },
        {
            "id": 4,
            "action": "fill",
            "selector": 'input[name="phone"]',
            "tag": "input",
            "field": "phone",
            "value": "",
            "description": "Fill PHONE (clean 10 digits)"
        },
        {
            "id": 5,
            "action": "fill",
            "selector": 'input[name="email"]',
            "tag": "input",
            "field": "email",
            "value": "",
            "description": "Fill EMAIL (input[name='email'])"
        },
        {
            "id": 6,
            "action": "captcha",
            "selector": 'input[placeholder*="code" i], input[name*="code" i]',
            "tag": "input",
            "field": "captcha",
            "value": "",
            "description": "CAPTCHA: Focus & wait for your code entry"
        },
        {
            "id": 7,
            "action": "click",
            "selector": 'button:has-text("Confirm & Cast Vote")',
            "tag": "button",
            "text": "Confirm & Cast Vote",
            "description": "Click 'Confirm & Cast Vote'"
        }
    ]
    with flow_lock:
        flow_state["target_url"] = "https://innovatecg.in/voting"
        flow_state["recorded_steps"] = steps
    add_flow_log("⚡ Preloaded InnovateCG 7-step flow (Education & Skills -> Sunmughan Swamy -> Name -> Phone -> Email -> Captcha -> Confirm).", "success")
    return jsonify({"status": "loaded", "steps": steps})

@app.route("/api/flow/steps", methods=["GET"])
def get_flow_steps():
    with flow_lock:
        return jsonify({
            "is_recording": flow_state["is_recording"],
            "target_url": flow_state["target_url"],
            "steps": list(flow_state["recorded_steps"])
        })

@app.route("/api/flow/update-steps", methods=["POST"])
def update_flow_steps():
    data = request.json or {}
    steps = data.get("steps", [])
    with flow_lock:
        flow_state["recorded_steps"] = steps
    return jsonify({"status": "updated", "count": len(steps)})

@app.route("/api/flow/start-replay", methods=["POST"])
def start_flow_replay():
    global flow_state
    with flow_lock:
        if flow_state["is_recording"]:
            return jsonify({"status": "error", "message": "Please stop recording first."}), 400
        if flow_state["is_replaying"]:
            return jsonify({"status": "error", "message": "Replay is already running."}), 400

        data = request.json or {}
        rows = data.get("rows", [])
        steps = data.get("steps") or flow_state["recorded_steps"]
        target_url = data.get("target_url") or flow_state["target_url"]

        if not target_url:
            return jsonify({"status": "error", "message": "Missing website URL."}), 400
        if not steps:
            return jsonify({"status": "error", "message": "No recorded steps found."}), 400
        if not rows:
            return jsonify({"status": "error", "message": "No CSV data loaded."}), 400

        flow_state["is_replaying"] = True
        flow_state["stop_requested"] = False
        flow_state["target_url"] = target_url
        flow_state["recorded_steps"] = steps
        flow_state["total"] = len(rows)
        flow_state["processed"] = 0
        flow_state["success"] = 0
        flow_state["failed"] = 0
        flow_state["new_logs"] = []
        flow_state["results"] = []

    thread = threading.Thread(target=replay_worker, args=({
        "target_url": target_url,
        "steps": steps,
        "rows": rows,
        "delay": data.get("delay", 2.0)
    },), daemon=True)
    thread.start()

    return jsonify({"status": "replay_started", "total": len(rows)})

@app.route("/api/flow/stop-replay", methods=["POST"])
def stop_flow_replay():
    with flow_lock:
        if flow_state["is_replaying"]:
            flow_state["stop_requested"] = True
            return jsonify({"status": "stopping_replay"})
    return jsonify({"status": "not_replaying"})

@app.route("/api/flow/progress", methods=["GET"])
def get_flow_progress():
    with flow_lock:
        logs_to_send = list(flow_state["new_logs"])
        flow_state["new_logs"].clear()

        return jsonify({
            "is_recording": flow_state["is_recording"],
            "is_replaying": flow_state["is_replaying"],
            "total": flow_state["total"],
            "processed": flow_state["processed"],
            "success": flow_state["success"],
            "failed": flow_state["failed"],
            "steps": flow_state["recorded_steps"],
            "logs": logs_to_send,
            "results": flow_state["results"]
        })


if __name__ == "__main__":
    port = 5000
    print(f"============================================================")
    print(f"  Website Flow Recorder & Replayer")
    print(f"  Dashboard: http://localhost:{port}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
