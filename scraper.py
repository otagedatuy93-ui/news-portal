import os
import time
import feedparser
import trafilatura
from supabase import create_client, Client
from transformers import pipeline
from sentence_transformers import SentenceTransformer

# --- ENVIRONMENT VARIABLES ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("CRITICAL ERROR: Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- LOAD AI MODELS (Runs once when script starts) ---
print("Loading NLP Categorization Model... (This takes a few seconds)")
classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")

print("Loading Vector Embedding Model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# --- DEFINITIONS ---
CATEGORIES = [
    "Tech & Startups", 
    "Global Politics", 
    "Bangladesh News", 
    "Science & Space", 
    "Economy", 
    "General News"
]

RSS_FEEDS = [
    # 🇧🇩 BANGLADESH NEWS (English)
    "https://www.tbsnews.net/tbs-rss",                      
    "https://www.thedailystar.net/rss",                     
    "https://en.prothomalo.com/feed",                       
    "https://www.dhakatribune.com/rss",                     
    
    # 🌍 INTERNATIONAL NEWS
    "http://feeds.bbci.co.uk/news/world/rss.xml",           
    "http://rss.cnn.com/rss/edition.rss",                   
    "https://www.aljazeera.com/xml/rss/all.xml",            
    "https://www.theguardian.com/world/rss",                
    
    # 💻 TECH & SCIENCE
    "https://techcrunch.com/feed/",                         
    "https://www.theverge.com/rss/index.xml",               
    "https://news.ycombinator.com/rss",                     
    "https://www.space.com/feeds/all",                      
    "https://www.sciencedaily.com/rss/all.xml"              
]

def calculate_read_time(text):
    """Calculates read time based on an average speed of 238 words per minute."""
    word_count = len(text.split())
    minutes = max(1, round(word_count / 238))
    return f"⏱️ {minutes} min read"

def fetch_full_news(rss_url, max_articles=5):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting feed: {rss_url}")
    
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  [ERROR] Failed to parse feed {rss_url}: {e}")
        return

    if not feed.entries:
        print("  [WARNING] No articles found.")
        return

    articles_processed = 0

    for entry in feed.entries:
        if articles_processed >= max_articles:
            break
            
        try:
            title = getattr(entry, 'title', 'Untitled')
            link = getattr(entry, 'link', None)
            
            if not link:
                continue
                
            print(f"  -> Processing: {title[:50]}...")
            
            # Download and extract text
            downloaded_html = trafilatura.fetch_url(link)
            if not downloaded_html: 
                continue
                
            full_text = trafilatura.extract(downloaded_html)
            if not full_text or len(full_text.strip()) < 50: 
                continue

            # NLP Processing
            read_time_str = calculate_read_time(full_text)
            
            print("    [NLP] Categorizing...")
            nlp_result = classifier(full_text[:500], CATEGORIES)
            best_category = nlp_result['labels'][0]
            print(f"    [NLP] Assigned Category: {best_category}")

            print("    [NLP] Generating Vector Embedding...")
            embedding = embedder.encode(full_text[:1500]).tolist()

            # Database Insertion
            article_data = {
                "title": title,
                "link": link,
                "full_text": full_text,
                "category": best_category,
                "read_time": read_time_str,
                "embedding": embedding
            }
            
            try:
                supabase.table("articles").insert(article_data).execute()
                print("    [SUCCESS] Saved to database with AI tags & vectors!")
                articles_processed += 1
            except Exception as e:
                if "duplicate key value" in str(e) or "23505" in str(e):
                    print("    [SKIPPED] Already in database.")
                else:
                    print(f"    [ERROR] Database insertion failed: {e}")
                    
        except Exception as e:
            print(f"    [CRITICAL ERROR] Loop failure: {e}")
            continue

if __name__ == "__main__":
    print("=== STARTING NEWS SCRAPER WITH AI ===")
    for feed_url in RSS_FEEDS:
        fetch_full_news(feed_url, max_articles=5)
    print("\n=== SCRAPING COMPLETE ===")