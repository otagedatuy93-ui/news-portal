import os
import feedparser
import trafilatura
from supabase import create_client, Client
from transformers import pipeline
from sentence_transformers import SentenceTransformer

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Loading AI Models...")
classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

CATEGORIES = ["Tech & Startups", "Global Politics", "Bangladesh News", "Science & Space", "Economy", "General News"]

RSS_FEEDS = [
    "https://www.tbsnews.net/tbs-rss", "https://www.thedailystar.net/rss", "https://en.prothomalo.com/feed", 
    "https://www.dhakatribune.com/rss", "http://feeds.bbci.co.uk/news/world/rss.xml", "http://rss.cnn.com/rss/edition.rss",
    "https://www.aljazeera.com/xml/rss/all.xml", "https://www.theguardian.com/world/rss", "https://techcrunch.com/feed/", 
    "https://www.theverge.com/rss/index.xml", "https://news.ycombinator.com/rss", "https://www.space.com/feeds/all", 
    "https://www.sciencedaily.com/rss/all.xml"
]

def fetch_full_news(rss_url, max_articles=5):
    print(f"\nStarting feed: {rss_url}")
    try: feed = feedparser.parse(rss_url)
    except Exception: return
    if not feed.entries: return
    
    articles_processed = 0
    for entry in feed.entries:
        if articles_processed >= max_articles: break
        try:
            title = getattr(entry, 'title', 'Untitled')
            link = getattr(entry, 'link', None)
            if not link: continue
            
            html = trafilatura.fetch_url(link)
            if not html: continue
            text = trafilatura.extract(html)
            if not text or len(text.strip()) < 50: continue

            word_count = len(text.split())
            read_time = f"⏱️ {max(1, round(word_count / 238))} min read"
            
            nlp_result = classifier(text[:500], CATEGORIES)
            category = nlp_result['labels'][0]
            embedding = embedder.encode(text[:1500]).tolist()

            data = {"title": title, "link": link, "full_text": text, "category": category, "read_time": read_time, "embedding": embedding}
            
            try:
                supabase.table("articles").insert(data).execute()
                print(f"Saved: {title[:30]}...")
                articles_processed += 1
            except Exception as e:
                if "duplicate" not in str(e) and "23505" not in str(e): print(f"DB Error: {e}")
        except Exception: continue

if __name__ == "__main__":
    for feed_url in RSS_FEEDS: fetch_full_news(feed_url, max_articles=5)
