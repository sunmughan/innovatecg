from playwright.sync_api import sync_playwright
import json
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://innovatecg.in/voting', wait_until='networkidle')
    
    categories = [
        'Sushasan & Governance', 'Science & Tech', 'Education & Skills',
        'Rural Impact', 'Health & Wellness', 'Nari Shakti', 'Green Champion',
        'Culture & Tourism', 'Media & Civic', 'Creative & Entertainment',
        'Lifestyle & Food', 'Tribal Voice', 'Style & Fashion',
        'Sports & Fitness', 'Gaming & Esports'
    ]
    
    catalog = {}
    
    for cat in categories:
        try:
            btn = page.locator(f'button:has-text("{cat}")').first
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(700)
                
                # Extract candidates on page
                cand_data = page.evaluate('''() => {
                    const cards = Array.from(document.querySelectorAll('div.rounded-3xl')).filter(c => {
                        return c.innerText && c.innerText.includes('Vote Now');
                    });
                    return cards.map(c => {
                        const h4 = c.querySelector('h4, h3');
                        const name = h4 ? h4.innerText.trim() : '';
                        const lines = c.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                        return {
                            name: name || (lines.length > 1 ? lines[1] : ''),
                            subCategory: lines.length > 2 ? lines[2] : '',
                            district: lines.find(l => ['Durg', 'Raipur', 'Bilaspur', 'Bastar', 'Rajnandgaon', 'Korba', 'Raigarh', 'Surguja', 'Dhamtari', 'Mahasamund', 'Janjgir', 'Kanker', 'Kawardha', 'Balod', 'Bemetara', 'Gariaband', 'Baloda Bazar', 'Mungeli', 'Surajpur', 'Balrampur', 'Sukma', 'Bijapur', 'Narayanpur', 'Kondagaon', 'Dantewada', 'Gaurela-Pendra-Marwahi', 'Khairagarh', 'Mohla-Manpur', 'Sakti', 'Sarangarh-Bilaigarh', 'Manendragarh'].includes(l)) || ''
                        };
                    }).filter(c => c.name && c.name !== 'Vote Now');
                }''')
                
                catalog[cat] = cand_data
                print(f"[{cat}]: Found {len(cand_data)} candidates")
        except Exception as e:
            print(f"Error for {cat}: {e}")
            
    with open('candidates_catalog.json', 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2)
        
    print(f"Total categories indexed: {len(catalog)}")
    total_candidates = sum(len(v) for v in catalog.values())
    print(f"Total candidates indexed: {total_candidates}")
    browser.close()
