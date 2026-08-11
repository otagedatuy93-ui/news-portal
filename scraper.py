import os
import time
import feedparser
import trafilatura
from supabase import create_client, Client

# --- ENVIRONMENT VARIABLES ---
# It's critical these are set in your GitHub Repository Secrets
SUPABASE_URL = os.environ.get("https://ofbdocelucncurwtgzij.supabase.coL")
SUPABASE_KEY = os.environ.get("sb_publishable_DjKELrVnsirfhs2DLfNaOg_Zx9ADzhx")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("CRITICAL ERROR: Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

# Initialize database connection
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CURATED RSS FEEDS ---
RSS_FEEDS = [
    # 🇧🇩 BANGLADESH NEWS (English)
    "https://www.tbsnews.net/tbs-rss",                      # The Business Standard
    "https://www.thedailystar.net/rss",                     # The Daily Star
    "https://en.prothomalo.com/feed",                       # Prothom Alo
    "https://www.dhakatribune.com/rss",                     # Dhaka Tribune
    
    # 🌍 INTERNATIONAL NEWS (World Editions)
    "http://feeds.bbci.co.uk/news/world/rss.xml",           # BBC World News
    "http://rss.cnn.com/rss/edition.rss",                   # CNN International
    "https://www.aljazeera.com/xml/rss/all.xml",            # Al Jazeera
    "https://www.theguardian.com/world/rss",                # The Guardian (World)
    
    # 💻 TECH, CODING & STARTUPS
    "https://techcrunch.com/feed/",                         # TechCrunch
    "https://www.theverge.com/rss/index.xml",               # The Verge
    "https://news.ycombinator.com/rss",                     # Hacker News
    
    # 🚀 SCIENCE & SPACE
    "https://www.space.com/feeds/all",                      # Space.com
    "https://www.sciencedaily.com/rss/all.xml"              # Science Daily
]

def fetch_full_news(rss_url, max_articles=5):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting feed: {rss_url}")
    
    # --- 1. SAFE RSS PARSING ---
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  [ERROR] Failed to parse feed {rss_url}: {e}")
        return # Exit this feed gracefully, move to the next

    if not feed.entries:
        print("  [WARNING] No articles found or invalid feed URL. Skipping.")
        return

    articles_processed = 0

    for entry in feed.entries:
        if articles_processed >= max_articles:
            break
            
        try:
            # Safely grab title and link with fallbacks in case XML is malformed
            title = getattr(entry, 'title', 'Untitled')
            link = getattr(entry, 'link', None)
            
            if not link:
                continue
                
            print(f"  -> Processing: {title[:50]}...")
            
            # --- 2. SAFE HTML DOWNLOAD ---
            try:
                downloaded_html = trafilatura.fetch_url(link)
            except Exception as e:
                print(f"    [ERROR] Download failed for {link}: {e}")
                continue # Skip this article
                
            if not downloaded_html:
                print("    [WARNING] Could not retrieve HTML (site might have bot protection).")
                continue
                
            # --- 3. SAFE TEXT EXTRACTION ---
            try:
                full_text = trafilatura.extract(downloaded_html)
            except Exception as e:
                print(f"    [ERROR] Text extraction failed: {e}")
                continue # Skip this article
                
            if not full_text or len(full_text.strip()) < 50:
                print("    [WARNING] Extracted text too short or empty (likely a paywall/video page).")
                continue

            # --- 4. SAFE DATABASE INSERTION ---
            article_data = {
                "title": title,
                "link": link,
                "full_text": full_text
            }
            
            try:
                # Push to Supabase
                supabase.table("articles").insert(article_data).execute()
                print("    [SUCCESS] Saved to database!")
                articles_processed += 1
            except Exception as e:
                error_msg = str(e)
                # Catching duplicate keys gracefully so it doesn't crash the script
                if "duplicate key value" in error_msg or "23505" in error_msg:
                    print("    [SKIPPED] Already in database.")
                else:
                    print(f"    [ERROR] Database insertion failed: {error_msg}")
                    
        except Exception as e:
            # Global catch for any totally unexpected loop error
            print(f"    [CRITICAL ERROR] Unexpected failure on an article loop: {e}")
            continue

if __name__ == "__main__":
    print("=== STARTING NEWS SCRAPER ===")
    for feed_url in RSS_FEEDS:
        fetch_full_news(feed_url, max_articles=5)
    print("\n=== SCRAPING COMPLETE ===")