import os
from fasthtml.common import *
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- UPGRADED CSS WITH STICKY NAVBAR ---
css = Style('''
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; color: #0f172a; max-width: 900px; margin: 0 auto; padding: 0 20px 20px 20px; }
    
    /* The Sticky Header Container */
    .header-container {
        position: sticky;
        top: 0;
        background: #f8fafc; /* Matches body so it looks seamless */
        z-index: 1000; /* Forces the menu to stay above the scrolling articles */
        padding-top: 20px;
        padding-bottom: 15px;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 30px;
    }
    
    /* Category Navigation Bar */
    .navbar { display: flex; gap: 12px; overflow-x: auto; scrollbar-width: none; }
    .navbar::-webkit-scrollbar { display: none; }
    .nav-link { background: #e2e8f0; color: #334155; padding: 8px 18px; border-radius: 20px; text-decoration: none; font-weight: 600; white-space: nowrap; transition: 0.2s;}
    .nav-link:hover { background: #cbd5e1; }
    .nav-link.active { background: #2563eb; color: white; }
    
    /* Modern Card Design */
    .card { background: white; border-radius: 16px; padding: 25px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border: 1px solid #f1f5f9;}
    .article-body { max-height: 180px; overflow: hidden; position: relative; transition: max-height 0.5s ease; font-size: 1.1rem; line-height: 1.7; color: #334155;}
    .article-body.expanded { max-height: 20000px; }
    
    /* Sleeker Blur Overlay */
    .blur-overlay { position: absolute; bottom: 0; left: 0; width: 100%; height: 100px; background: linear-gradient(transparent, rgba(255,255,255,1) 80%); cursor: pointer; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 10px; font-weight: bold; color: #2563eb; font-size: 1.05rem;}
    .expanded .blur-overlay { display: none; }
    
    /* Meta Tags */
    .meta { display: flex; gap: 10px; margin-bottom: 20px; font-size: 0.9rem; align-items: center; flex-wrap: wrap;}
    .badge { background: #dbeafe; color: #1e40af; padding: 5px 12px; border-radius: 99px; font-weight: 600; }
    .read-more { color: #2563eb; text-decoration: none; margin-left: auto; font-weight: bold; background: #eff6ff; padding: 6px 16px; border-radius: 8px;}
    .read-more:hover { background: #bfdbfe; }
''')

js = Script('''
    function expandArticle(btn) { btn.closest('.article-body').classList.add('expanded'); }
''')

app, rt = fast_app(hdrs=(css, js))

# --- CATEGORY NAVIGATION COMPONENT ---
def NavBar(current_cat):
    categories = ["Tech & Startups", "Global Politics", "Bangladesh News", "Science & Space", "Economy", "General News"]
    links = [A("All News", href="/", cls="nav-link active" if not current_cat else "nav-link")]
    
    for cat in categories:
        is_active = "nav-link active" if current_cat == cat else "nav-link"
        links.append(A(cat, href=f"/?category={cat}", cls=is_active))
        
    # Wrap in the new sticky container
    return Div(
        Div(*links, cls="navbar"),
        cls="header-container"
    )

# --- ARTICLE CARD COMPONENT ---
def ArticleCard(article, page_num, is_last, current_cat):
    cat_query = f"&category={current_cat}" if current_cat else ""
    scroll_attrs = {"hx_get": f"/?page={page_num + 1}{cat_query}", "hx_trigger": "revealed", "hx_swap": "afterend"} if is_last else {}
    
    return Div(
        H2(article.get('title', 'Untitled'), style="margin-top: 0; font-size: 1.6rem; color: #0f172a;"),
        Div(Span(article.get('category', 'News'), cls="badge"), Span(article.get('read_time', '⏱️ ? min'), cls="badge"), A("Original Site ↗", href=article.get('link', '#'), target="_blank", cls="read-more"), cls="meta"),
        Div(*[P(p) for p in article.get('full_text', '').split('\n') if p.strip()], Div("Read Full Article ↓", cls="blur-overlay", onclick="expandArticle(this)"), cls="article-body"),
        cls="card", **scroll_attrs
    )

# --- BACKEND ROUTING ---
@rt("/")
def get(page: int = 1, category: str = None):
    PAGE_SIZE = 10
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE - 1
    
    query = supabase.table("articles").select("*").order("created_at", desc=True)
    if category:
        query = query.eq("category", category)
        
    response = query.range(start_idx, end_idx).execute()
    articles = response.data
    
    cards = [ArticleCard(art, page, is_last=(i == len(articles) - 1), current_cat=category) for i, art in enumerate(articles)]
    
    if page > 1: 
        return tuple(cards)
    
    return Titled("My News Portal", 
        H1("My Daily Feed", style="text-align: center; font-weight: 900; font-size: 2.5rem; margin-top: 25px; margin-bottom: 15px;"),
        NavBar(category),
        Div(*cards, id="feed-container")
    )

serve()