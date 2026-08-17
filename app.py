import os
from fasthtml.common import *
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

css = Style('''
    body { font-family: system-ui, sans-serif; background: #f3f4f6; color: #111827; max-width: 800px; margin: 0 auto; padding: 20px; }
    .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .article-body { max-height: 250px; overflow: hidden; position: relative; transition: max-height 0.4s ease; font-size: 1.1rem; line-height: 1.6; color: #374151;}
    .article-body.expanded { max-height: 15000px; }
    .blur-overlay { position: absolute; bottom: 0; left: 0; width: 100%; height: 120px; background: linear-gradient(transparent, rgba(255,255,255,1) 85%); cursor: pointer; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 10px; font-weight: bold; color: #2563eb; }
    .expanded .blur-overlay { display: none; }
    .meta { display: flex; gap: 10px; margin-bottom: 15px; font-size: 0.85rem; align-items: center;}
    .badge { background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 99px; font-weight: 600; }
    a { color: #2563eb; text-decoration: none; margin-left: auto; font-weight: 500;}
''')

js = Script('''
    function expandArticle(btn) { btn.closest('.article-body').classList.add('expanded'); }
''')

app, rt = fast_app(hdrs=(css, js))

def ArticleCard(article, page_num, is_last):
    scroll_attrs = {"hx_get": f"/?page={page_num + 1}", "hx_trigger": "revealed", "hx_swap": "afterend"} if is_last else {}
    return Div(
        H2(article.get('title', 'Untitled'), style="margin-top: 0;"),
        Div(Span(article.get('category', 'News'), cls="badge"), Span(article.get('read_time', '⏱️ ? min'), cls="badge"), A("Read ↗", href=article.get('link', '#'), target="_blank"), cls="meta"),
        Div(*[P(p) for p in article.get('full_text', '').split('\n') if p.strip()], Div("Read full article ↓", cls="blur-overlay", onclick="expandArticle(this)"), cls="article-body"),
        cls="card", **scroll_attrs
    )

@rt("/")
def get(page: int = 1):
    PAGE_SIZE = 10
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE - 1
    response = supabase.table("articles").select("title, category, read_time, link, full_text").order("created_at", desc=True).range(start_idx, end_idx).execute()
    articles = response.data
    cards = [ArticleCard(art, page, is_last=(i == len(articles) - 1 and len(articles) == PAGE_SIZE)) for i, art in enumerate(articles)]
    if page > 1: return tuple(cards)
    return Titled("My News Portal", H1("Personal News Feed", style="text-align: center; color: #111827; font-weight: 800;"), Div(*cards, id="feed-container"))

serve()
