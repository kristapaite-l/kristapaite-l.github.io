import os
import re
import time
import sqlite3
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables from .env file
load_dotenv()

# --- Configuration & Paths ---
HACK_CHINESE_LOGIN_URL = "https://www.hackchinese.com/users/sign_in"
SESSION_FILE = "auth_state.json"

TARGET_DIR = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\data\languages\mandarin"
SNAPSHOT_DIR = os.path.join(TARGET_DIR, "dashboard_snapshot")
DASHBOARD_MASTER_CSV = os.path.join(TARGET_DIR, "hack_chinese_daily_dashboard.csv")
TEMP_DB = os.path.join(TARGET_DIR, "temp_staging.db")

# Helper function to get dated vocab CSV path
def get_vocab_csv_path(today_str):
    return os.path.join(TARGET_DIR, f"hack_chinese_master_vocab_{today_str}.csv")

def scrape_dashboard_to_temp_db(page, today_str):
    """Step 1: Scrape dashboard metrics, save dated snapshot, and stage in SQLite."""
    DASHBOARD_URL = "https://www.hackchinese.com/dashboard"
    print(f"Navigating to: {DASHBOARD_URL}")
    page.goto(DASHBOARD_URL)
    page.wait_for_selector("body")
    time.sleep(3)

    # Ensure snapshot subfolder exists and save screenshot with today's date
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    screenshot_path = os.path.join(SNAPSHOT_DIR, f"dashboard_snapshot_{today_str}.png")
    page.screenshot(path=screenshot_path)
    print(f"Dashboard screenshot saved to: {screenshot_path}")

    page_text = page.inner_text("body")

    # Dynamic extraction via regex pattern matching
    match_reviews = re.search(r'(\d+)\s*\n\s*Reviews Due', page_text, re.IGNORECASE)
    reviews_due = int(match_reviews.group(1)) if match_reviews else 0

    study_days_match = re.search(r'(\d+)\s*\n\s*Study Days', page_text, re.IGNORECASE)
    study_days = int(study_days_match.group(1)) if study_days_match else 0

    match_words = re.search(r'(\d+)\s*\n\s*Words Studied', page_text, re.IGNORECASE)
    words_studied = int(match_words.group(1)) if match_words else 0

    match_chars = re.search(r'(\d+)\s*\n\s*Characters Studied', page_text, re.IGNORECASE)
    chars_studied = int(match_chars.group(1)) if match_chars else 0

    match_sessions = re.search(r'(\d+)\s*\n\s*Study Sessions', page_text, re.IGNORECASE)
    study_sessions = int(match_sessions.group(1)) if match_sessions else 0

    match_rev_lt = re.search(r'(\d+)\s*\n\s*Reviews\s*\n\s*\(Lifetime\)', page_text, re.IGNORECASE)
    if not match_rev_lt:
        match_rev_lt = re.search(r'(\d+)\s*\n\s*Reviews', page_text, re.IGNORECASE)
    reviews_lifetime = int(match_rev_lt.group(1)) if match_rev_lt else 0

    match_wpd = re.search(r'(\d+\.\d+|\d+)\s*\n\s*Words/Day', page_text, re.IGNORECASE)
    words_per_day = float(match_wpd.group(1)) if match_wpd else 0.0

    match_ret = re.search(r'(\d+)%\s*\n\s*Retention Rate', page_text, re.IGNORECASE)
    retention_rate = (float(match_ret.group(1)) / 100.0) if match_ret else 0.0

    dashboard_data = {
        "snapshot_date": today_str,
        "reviews_due": reviews_due,
        "study_days_5min_plus": study_days,
        "words_studied": words_studied,
        "characters_studied": chars_studied,
        "study_sessions_lifetime": study_sessions,
        "reviews_lifetime": reviews_lifetime,
        "words_per_day_lifetime": words_per_day,
        "retention_rate_lifetime_pct": retention_rate
    }

    temp_df = pd.DataFrame([dashboard_data])
    conn = sqlite3.connect(TEMP_DB)
    temp_df.to_sql("temp_dashboard", conn, if_exists="replace", index=False)
    conn.close()
    print("Dashboard metrics staged in SQLite temp database.")


def download_vocab_csv_to_temp_db(page, today_str):
    """Step 2: Navigate three-dots menu -> Settings -> Data -> Exports -> Export All Learned Words."""
    print("Navigating dashboard settings modal via UI clicks...")
    
    # Ensure page is on dashboard
    if "dashboard" not in page.url:
        page.goto("https://www.hackchinese.com/dashboard")
        page.wait_for_timeout(2000)

    # 1. Click the three dots icon next to the "Study" button
    print("Clicking three-dots menu icon...")
    
    three_dots_locators = [
        'header a:has-text("Study") + button',
        'header div:has-text("Study") button',
        'a[href*="study"] + button',
        'header button:has(svg)'
    ]

    clicked_dots = False
    for selector in three_dots_locators:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                btn.click()
                clicked_dots = True
                print(f"Successfully clicked three-dots menu using selector: {selector}")
                break
        except Exception:
            continue

    if not clicked_dots:
        print("Fallback: Clicking top-right menu coordinates...")
        # Direct fallback click on top right header controls near three-dots icon
        page.mouse.click(1245, 30)

    time.sleep(1.5)

    # 2. Click "Settings" in the dropdown menu
    print("Clicking 'Settings' from menu...")
    settings_item = page.locator('text="Settings"').locator('visible=true').first
    settings_item.wait_for(state="visible", timeout=5000)
    settings_item.click()

    time.sleep(1.5)

    # 3. Click "Data" in the settings modal sidebar
    print("Clicking 'Data' tab...")
    data_item = page.locator('text="Data"').locator('visible=true').first
    data_item.wait_for(state="visible", timeout=5000)
    data_item.click()

    time.sleep(1.5)

    # 4. Click "Exports" tab
    print("Clicking 'Exports' tab...")
    exports_item = page.locator('text="Exports"').locator('visible=true').first
    exports_item.wait_for(state="visible", timeout=5000)
    exports_item.click()

    time.sleep(1.5)

    # 5. Click "Export All Learned Words" to download
    print("Triggering 'Export All Learned Words' download...")
    with page.expect_download(timeout=30000) as download_info:
        export_btn = page.locator('button:has-text("Export All Learned Words"), a:has-text("Export All Learned Words")').locator('visible=true').first
        export_btn.click()

    download = download_info.value
    download_path = os.path.join(TARGET_DIR, "temp_download.csv")
    download.save_as(download_path)
    print(f"Downloaded CSV saved temporarily to {download_path}")

    # Read downloaded CSV and append snapshot_date
    vocab_df = pd.read_csv(download_path)
    vocab_df["snapshot_date"] = today_str

    cols = ["snapshot_date"] + [c for c in vocab_df.columns if c != "snapshot_date"]
    vocab_df = vocab_df[cols]

    # Clean up temporary download file
    if os.path.exists(download_path):
        os.remove(download_path)

    # Stage in SQLite database
    conn = sqlite3.connect(TEMP_DB)
    vocab_df.to_sql("temp_vocab", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Staged {len(vocab_df)} vocabulary records into SQLite temp database.")


def process_and_append_dashboard():
    """Appends dashboard metrics from temp database to master CSV immediately."""
    if not os.path.exists(TEMP_DB):
        return

    conn = sqlite3.connect(TEMP_DB)
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)["name"].values

    if "temp_dashboard" in tables:
        temp_dash = pd.read_sql("SELECT * FROM temp_dashboard", conn)
        append_if_new(temp_dash, DASHBOARD_MASTER_CSV, "Dashboard")

    conn.close()


def process_and_append_vocab(today_str):
    """Appends/saves vocabulary metrics from temp database to dated CSV file."""
    if not os.path.exists(TEMP_DB):
        return

    conn = sqlite3.connect(TEMP_DB)
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)["name"].values

    if "temp_vocab" in tables:
        temp_vocab = pd.read_sql("SELECT * FROM temp_vocab", conn)
        vocab_csv_path = get_vocab_csv_path(today_str)
        
        # Save directly as today's dated CSV
        temp_vocab.to_csv(vocab_csv_path, index=False)
        print(f"Successfully saved dated vocabulary export to {vocab_csv_path}")

    conn.close()
    
def append_if_new(temp_df, master_csv_path, dataset_name):
    if temp_df.empty:
        print(f"No {dataset_name} staging data available to process.")
        return

    scraped_date = str(temp_df["snapshot_date"].iloc[0])

    if not os.path.exists(master_csv_path):
        temp_df.to_csv(master_csv_path, index=False)
        print(f"Created {dataset_name} Master CSV at {master_csv_path} with initial snapshot ({scraped_date}).")
        return

    existing_df = pd.read_csv(master_csv_path)
    max_existing_date = str(existing_df["snapshot_date"].max())

    print(f"[{dataset_name}] Existing max date: {max_existing_date} | Scraped date: {scraped_date}")

    if scraped_date <= max_existing_date:
        print(f"[{dataset_name}] Snapshot date matches or precedes existing max date. Skipping append.")
        return

    # Validate Schema Alignment
    existing_cols = list(existing_df.columns)
    temp_cols = list(temp_df.columns)

    if set(existing_cols) != set(temp_cols):
        print(f"[{dataset_name}] Schema mismatch detected!")
        print(f"Existing: {existing_cols}")
        print(f"Scraped:  {temp_cols}")
        print(f"[{dataset_name}] Append operation aborted to prevent data corruption.")
        return

    temp_df = temp_df[existing_cols]
    temp_df.to_csv(master_csv_path, mode="a", header=False, index=False)
    print(f"Successfully appended new {dataset_name} snapshot ({scraped_date}) to {master_csv_path}!")


def run_pipeline():
    username = os.getenv("HACK_CHINESE_EMAIL", "your_email@example.com")
    password = os.getenv("HACK_CHINESE_PASS", "your_password")
    today_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(TARGET_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        if os.path.exists(SESSION_FILE):
            print("Loading saved session...")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            context = browser.new_context()

        page = context.new_page()

        # Handle login sequence
        page.goto("https://www.hackchinese.com/dashboard")
        page.wait_for_timeout(3000)

        if "sign_in" in page.url or "login" in page.url:
            print("Logging into Hack Chinese automatically...")
            if page.url != HACK_CHINESE_LOGIN_URL:
                page.goto(HACK_CHINESE_LOGIN_URL)

            page.fill('input[type="email"]', username)
            page.fill('input[type="password"]', password)
            page.click('button:has-text("Sign in"), input[type="submit"]')
            page.wait_for_url("**/dashboard", timeout=15000)

            context.storage_state(path=SESSION_FILE)
            print("Login successful and session state updated.")

        # Step 1: Scrape dashboard & save to temp DB
        scrape_dashboard_to_temp_db(page, today_str)

        # Immediate Append: Save dashboard metrics to master CSV right away
        print("Saving dashboard metrics to master CSV immediately...")
        process_and_append_dashboard()

        # Step 2: Attempt vocabulary download & staging
        try:
            download_vocab_csv_to_temp_db(page, today_str)
            process_and_append_vocab(today_str)
        except Exception as e:
            print(f"Vocabulary export encountered an issue: {e}")

        browser.close()


if __name__ == "__main__":
    run_pipeline()