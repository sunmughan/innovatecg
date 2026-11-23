import shutil
import os

src = r"C:\Users\WIN\.gemini\antigravity\brain\eecba6ea-cde8-4d72-9d74-92aa8141a357\.user_uploaded\media_1795402295396_dedb1419.csv"
dst = r"c:\Users\WIN\OneDrive\Downloads\mywebsite\mobile.csv"
shutil.copy2(src, dst)
print("Copied to:", dst, "Size:", os.path.getsize(dst))

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://innovatecg.in/voting", wait_until="networkidle")
    
    cat_btn = page.locator('button:has-text("Education & Skills")').first
    print("Initial class:", cat_btn.get_attribute("class"))
    
    cat_btn.click()
    page.wait_for_timeout(1000)
    print("After 1st click class:", cat_btn.get_attribute("class"))
    
    swamy = page.locator('div.rounded-3xl:has-text("Sunmughan Swamy") >> button:has-text("Vote Now")').first
    print("Swamy visible:", swamy.is_visible())
    
    # Check what happens on 2nd click
    cat_btn.click()
    page.wait_for_timeout(1000)
    print("After 2nd click class:", cat_btn.get_attribute("class"))
    print("Swamy visible after 2nd click:", swamy.is_visible())
    
    # Open modal
    swamy.click()
    page.wait_for_timeout(1000)
    print("Modal open:", page.locator('input[name="name"]').is_visible())
    
    # Close modal (simulate close or finish)
    close_btn = page.locator('button:has-text("✕"), button:has-text("Close"), svg.lucide-x').first
    if close_btn.is_visible():
        close_btn.click()
        page.wait_for_timeout(1000)
        print("Modal closed. Swamy visible again?", swamy.is_visible())
    
    browser.close()
