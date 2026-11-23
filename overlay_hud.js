(() => {
    if (document.getElementById('agy-floating-toolbar')) return;

    window.__AGY_PAUSED = false;
    window.__AGY_CONFIG_UPDATE = false;
    window.__AGY_SKIP_REQUESTED = false;
    
    if (!window.__AGY_CONFIG) {
        window.__AGY_CONFIG = {
            mode: 'manual',
            tab_count: 1,
            tabs: [
                { category: 'Education & Skills', candidate: 'Sunmughan Swamy' }
            ]
        };
    }

    // 1. Floating Unified Toolbar (No overlapping, flexbox layout)
    const toolbar = document.createElement('div');
    toolbar.id = 'agy-floating-toolbar';
    toolbar.style.cssText = 'position:fixed;top:12px;right:16px;z-index:2147483647;display:flex;align-items:center;gap:8px;background:rgba(255,255,255,0.92);backdrop-filter:blur(8px);padding:5px 8px;border-radius:28px;box-shadow:0 6px 20px rgba(0,0,0,0.28);border:1.5px solid #fed7aa;font-family:sans-serif;';

    // A. Skip Record Button
    const skipBtn = document.createElement('button');
    skipBtn.id = 'agy-skip-btn';
    skipBtn.innerText = '⏭️ Skip Record';
    skipBtn.style.cssText = 'background:#dc2626;color:white;padding:7px 14px;border:none;border-radius:20px;font-family:sans-serif;font-size:12px;font-weight:bold;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.2);transition:all 0.15s;white-space:nowrap;';
    skipBtn.onmouseover = () => skipBtn.style.transform = 'scale(1.04)';
    skipBtn.onmouseout = () => skipBtn.style.transform = 'scale(1)';
    skipBtn.onclick = (e) => {
        e.preventDefault();
        window.__AGY_SKIP_REQUESTED = true;
        skipBtn.innerText = '⏳ Skipping...';
        skipBtn.style.background = '#6b7280';
    };

    // B. Control Center Button
    const hubBtn = document.createElement('button');
    hubBtn.id = 'agy-hub-btn';
    hubBtn.innerHTML = '⚙️ <b>Control Center</b>';
    hubBtn.style.cssText = 'background:linear-gradient(135deg, #C15B3D, #D39B2C);color:white;padding:7px 16px;border:none;border-radius:20px;font-family:sans-serif;font-size:12px;font-weight:bold;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.2);transition:all 0.15s;white-space:nowrap;';
    hubBtn.onmouseover = () => hubBtn.style.transform = 'scale(1.04)';
    hubBtn.onmouseout = () => hubBtn.style.transform = 'scale(1)';

    toolbar.appendChild(skipBtn);
    toolbar.appendChild(hubBtn);

    // 2. Modal Overlay Container
    const modal = document.createElement('div');
    modal.id = 'agy-hub-modal';
    modal.style.cssText = 'display:none;position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,0.72);backdrop-filter:blur(4px);justify-content:center;align-items:center;padding:16px;font-family:sans-serif;box-sizing:border-box;';
    
    modal.innerHTML = `
    <div style="background:#FAF7F0;border:2px solid #D39B2C;border-radius:24px;width:100%;max-width:720px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 40px rgba(0,0,0,0.5);display:flex;flex-direction:column;color:#18181b;">
        <!-- Header -->
        <div style="background:linear-gradient(135deg, #C15B3D, #D39B2C);padding:18px 24px;color:white;display:flex;justify-content:space-between;align-items:center;border-top-left-radius:22px;border-top-right-radius:22px;">
            <div>
                <h3 style="margin:0;font-size:18px;font-weight:800;letter-spacing:0.5px;">⚡ Automation Control Center</h3>
                <span style="font-size:11px;background:#fef08a;color:#854d0e;padding:3px 10px;border-radius:12px;font-weight:bold;margin-top:6px;display:inline-block;">⏸️ PAUSED while menu is open</span>
            </div>
            <button id="agy-close-modal-x" style="background:rgba(255,255,255,0.2);border:none;color:white;font-size:18px;width:34px;height:34px;border-radius:50%;cursor:pointer;font-weight:bold;">✕</button>
        </div>

        <div style="padding:22px;display:flex;flex-direction:column;gap:18px;">
            <!-- Run Mode Selection -->
            <div style="background:white;padding:16px;border-radius:16px;border:1px solid #e4e4e7;">
                <label style="font-size:13px;font-weight:bold;color:#27272a;display:block;margin-bottom:8px;">🎯 Execution Mode:</label>
                <div style="display:flex;gap:12px;">
                    <label id="agy-mode-manual-label" style="flex:1;display:flex;align-items:center;gap:10px;padding:12px 14px;border:2px solid #D39B2C;border-radius:14px;cursor:pointer;background:#fffbeb;">
                        <input type="radio" name="agy-mode" value="manual" checked style="accent-color:#C15B3D;">
                        <div>
                            <div style="font-weight:bold;font-size:13px;color:#92400e;">Manual Run (Semi-Auto)</div>
                            <div style="font-size:11px;color:#78350f;">Bot fills details -> Human enters captcha -> Auto-roll</div>
                        </div>
                    </label>
                    <label id="agy-mode-auto-label" style="flex:1;display:flex;align-items:center;gap:10px;padding:12px 14px;border:2px solid #e4e4e7;border-radius:14px;cursor:pointer;background:#fafafa;">
                        <input type="radio" name="agy-mode" value="auto" style="accent-color:#C15B3D;">
                        <div>
                            <div style="font-weight:bold;font-size:13px;color:#18181b;">Auto Run Mode</div>
                            <div style="font-size:11px;color:#71717a;">Continuous automated parallel execution</div>
                        </div>
                    </label>
                </div>
            </div>

            <!-- Parallel Tabs Count -->
            <div style="background:white;padding:16px;border-radius:16px;border:1px solid #e4e4e7;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <label style="font-size:13px;font-weight:bold;color:#27272a;">📑 Parallel Running Tabs (Chromium Browser):</label>
                    <select id="agy-tab-count" style="padding:6px 14px;border-radius:10px;border:2px solid #d4d4d8;font-weight:bold;font-size:13px;cursor:pointer;background:white;">
                        <option value="1">1 Tab (Standard)</option>
                        <option value="2">2 Tabs Parallel</option>
                        <option value="3">3 Tabs Parallel</option>
                        <option value="4">4 Tabs Parallel</option>
                        <option value="5">5 Tabs Parallel</option>
                    </select>
                </div>
                <div style="font-size:11px;color:#71717a;">Each parallel tab runs concurrently with its assigned category & target candidate.</div>
            </div>

            <!-- Tab Target Configuration Cards -->
            <div id="agy-tabs-container" style="display:flex;flex-direction:column;gap:14px;">
                <!-- Populated dynamically -->
            </div>
        </div>

        <!-- Footer -->
        <div style="padding:16px 24px;background:#f4f4f5;border-top:1px solid #e4e4e7;display:flex;justify-content:flex-end;gap:12px;border-bottom-left-radius:22px;border-bottom-right-radius:22px;">
            <button id="agy-cancel-btn" style="padding:10px 18px;border-radius:12px;border:1px solid #d4d4d8;background:white;font-weight:bold;font-size:13px;cursor:pointer;">Cancel & Resume</button>
            <button id="agy-apply-btn" style="padding:10px 24px;border-radius:12px;border:none;background:linear-gradient(135deg, #C15B3D, #D39B2C);color:white;font-weight:bold;font-size:13px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.25);">🚀 Apply Settings & Resume</button>
        </div>
    </div>
    `;

    document.body.appendChild(toolbar);
    document.body.appendChild(modal);

    // Update Radio UI borders on change
    document.querySelectorAll('input[name="agy-mode"]').forEach(r => {
        r.onchange = () => {
            const isManual = r.value === 'manual';
            document.getElementById('agy-mode-manual-label').style.borderColor = isManual ? '#D39B2C' : '#e4e4e7';
            document.getElementById('agy-mode-manual-label').style.background = isManual ? '#fffbeb' : '#fafafa';
            document.getElementById('agy-mode-auto-label').style.borderColor = !isManual ? '#D39B2C' : '#e4e4e7';
            document.getElementById('agy-mode-auto-label').style.background = !isManual ? '#fffbeb' : '#fafafa';
        };
    });

    // Tab Rendering Helper
    function renderTabCards() {
        const count = parseInt(document.getElementById('agy-tab-count').value, 10);
        const container = document.getElementById('agy-tabs-container');
        container.innerHTML = '';

        const categories = Object.keys(window.__AGY_CATALOG || {});

        for (let i = 0; i < count; i++) {
            const existing = (window.__AGY_CONFIG.tabs && window.__AGY_CONFIG.tabs[i]) || {
                category: categories[i % categories.length] || 'Education & Skills',
                candidate: 'Sunmughan Swamy'
            };

            const card = document.createElement('div');
            card.className = 'agy-tab-card';
            card.dataset.index = i;
            card.style.cssText = 'background:white;padding:16px;border-radius:16px;border:1.5px solid #fed7aa;box-shadow:0 2px 6px rgba(0,0,0,0.03);display:flex;flex-direction:column;gap:10px;';

            card.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:bold;font-size:13px;color:#C15B3D;">📌 Tab #${i + 1} Target</span>
                    <span style="font-size:11px;color:#a1a1aa;">Independent Tab Session</span>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    <div>
                        <label style="font-size:11px;font-weight:bold;color:#52525b;display:block;margin-bottom:4px;">1. Select Category:</label>
                        <select class="agy-cat-select" style="width:100%;padding:8px 10px;border-radius:10px;border:1.5px solid #d4d4d8;font-size:12px;font-weight:600;background:white;">
                            ${categories.map(c => `<option value="${c}" ${c === existing.category ? 'selected' : ''}>${c}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label style="font-size:11px;font-weight:bold;color:#52525b;display:block;margin-bottom:4px;">2. Search & Select Candidate:</label>
                        <input type="text" class="agy-cand-search" placeholder="🔍 Type name to filter..." style="width:100%;padding:6px 10px;border-radius:8px;border:1px solid #d4d4d8;font-size:11px;margin-bottom:4px;box-sizing:border-box;">
                        <select class="agy-cand-select" style="width:100%;padding:8px 10px;border-radius:10px;border:1.5px solid #d4d4d8;font-size:12px;font-weight:600;background:white;">
                            <!-- Populated on category select / search -->
                        </select>
                        <div class="agy-checkpoint-badge" style="font-size:11px;background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:8px;font-weight:bold;margin-top:6px;display:inline-flex;align-items:center;gap:4px;border:1px solid #fde68a;">
                            <span>🏁 Checkpoint:</span> <span class="agy-badge-text">Row #1 (New)</span>
                        </div>
                    </div>
                </div>
            `;

            container.appendChild(card);

            const catSelect = card.querySelector('.agy-cat-select');
            const candSelect = card.querySelector('.agy-cand-select');
            const searchInput = card.querySelector('.agy-cand-search');
            const badgeText = card.querySelector('.agy-badge-text');

            function updateCheckpointBadge() {
                const candName = candSelect.value;
                const checkpoints = window.__AGY_CHECKPOINTS || {};
                const info = checkpoints[candName];
                if (info && (info.submitted_count > 0 || info.last_index >= 0)) {
                    const nextRow = (info.last_index >= 0) ? (info.last_index + 2) : (info.submitted_count + 1);
                    badgeText.innerText = `Row #${nextRow} (${info.submitted_count} votes cast)`;
                    badgeText.parentElement.style.background = '#dcfce7';
                    badgeText.parentElement.style.color = '#15803d';
                    badgeText.parentElement.style.borderColor = '#bbf7d0';
                } else {
                    badgeText.innerText = `Row #1 (New / 0 votes)`;
                    badgeText.parentElement.style.background = '#fef3c7';
                    badgeText.parentElement.style.color = '#92400e';
                    badgeText.parentElement.style.borderColor = '#fde68a';
                }
            }

            function populateCandidates(filterQuery = '') {
                const cat = catSelect.value;
                const cands = (window.__AGY_CATALOG && window.__AGY_CATALOG[cat]) || [];
                const q = filterQuery.toLowerCase().trim();
                const filtered = q ? cands.filter(c => c.name.toLowerCase().includes(q) || (c.subCategory && c.subCategory.toLowerCase().includes(q))) : cands;

                candSelect.innerHTML = filtered.map(c => {
                    const isSelected = c.name.toLowerCase() === (existing.candidate || '').toLowerCase();
                    return `<option value="${c.name}" ${isSelected ? 'selected' : ''}>${c.name} ${c.district ? '(' + c.district + ')' : ''}</option>`;
                }).join('');

                if (filtered.length === 0) {
                    candSelect.innerHTML = `<option value="">(No candidate match found)</option>`;
                }
                updateCheckpointBadge();
            }

            catSelect.onchange = () => populateCandidates(searchInput.value);
            candSelect.onchange = updateCheckpointBadge;
            searchInput.oninput = () => populateCandidates(searchInput.value);
            populateCandidates();
        }
    }

    // Open Modal and Pause
    hubBtn.onclick = () => {
        window.__AGY_PAUSED = true;
        modal.style.display = 'flex';
        // Set mode radio
        const modeRadio = document.querySelector(`input[name="agy-mode"][value="${window.__AGY_CONFIG.mode || 'manual'}"]`);
        if (modeRadio) {
            modeRadio.checked = true;
            modeRadio.dispatchEvent(new Event('change'));
        }
        document.getElementById('agy-tab-count').value = String(window.__AGY_CONFIG.tab_count || 1);
        renderTabCards();
    };

    // Close Modal and Resume
    function closeModal() {
        modal.style.display = 'none';
        window.__AGY_PAUSED = false;
    }

    document.getElementById('agy-close-modal-x').onclick = closeModal;
    document.getElementById('agy-cancel-btn').onclick = closeModal;
    document.getElementById('agy-tab-count').onchange = renderTabCards;

    // Apply Settings
    document.getElementById('agy-apply-btn').onclick = () => {
        const mode = document.querySelector('input[name="agy-mode"]:checked').value;
        const tabCount = parseInt(document.getElementById('agy-tab-count').value, 10);
        const cards = document.querySelectorAll('.agy-tab-card');
        const tabsConfig = [];

        cards.forEach((card, idx) => {
            const cat = card.querySelector('.agy-cat-select').value;
            const cand = card.querySelector('.agy-cand-select').value;
            tabsConfig.push({ tabIndex: idx, category: cat, candidate: cand });
        });

        window.__AGY_CONFIG = {
            mode: mode,
            tab_count: tabCount,
            tabs: tabsConfig
        };
        window.__AGY_CONFIG_UPDATE = true;
        closeModal();
    };
})();
