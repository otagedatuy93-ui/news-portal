import os
from fasthtml.common import *
from supabase import create_client, Client

# --- 1. SUPABASE CONNECTION ---
# Uses the exact same environment variables as your scraper
SUPABASE_URL = os.environ.get("https://ofbdocelucncurwtgzij.supabase.co")
SUPABASE_KEY = os.environ.get("sb_publishable_DjKELrVnsirfhs2DLfNaOg_Zx9ADzhx")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CSS & JAVASCRIPT ---
# The CSS handles the layout, badges, and the visual blur effect
css = Style('''
    body { font-family: system-ui, sans-serif; background: #f3f4f6; color: #111827; max-width: 800px; margin: 0 auto; padding: 20px; }
    .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    
    /* Blur-to-Expand Logic */
    .article-body { max-height: 250px; overflow: hidden; position: relative; transition: max-height 0.4s ease; font-size: 1.1rem; line-height: 1.6; color: #374151;}
    .article-body.expanded { max-height: 15000px; } /* Expands to fit any article */
    
    .blur-overlay { position: absolute; bottom: 0; left: 0; width: 100%; height: 120px; background: linear-gradient(transparent, rgba(255,255,255,1) 85%); cursor: pointer; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 10px; font-weight: bold; color: #2563eb; }
    .expanded .blur-overlay { display: none; } /* Hides blur when clicked */
    
    /* UI Styling */
    .meta { display: flex; gap: 10px; margin-bottom: 15px; font-size: 0.85rem; align-items: center;}
    .badge { background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 99px; font-weight: 600; }
    a { color: #2563eb; text-decoration: none; margin-left: auto; font-weight: 500;}
    a:hover { text-decoration: underline; }
''')

# The JS simply adds the 'expanded' class when the blur is clicked
js = Script('''
    function expandArticle(btn) {
        btn.closest('.article-body').classList.add('expanded');
    }
''')

# Initialize the FastHTML app
app, rt = fast_app(hdrs=(css, js))

# --- 3. UI COMPONENTS ---
def ArticleCard(article, page_num, is_last):
    # THE DOOM SCROLL LOGIC: 
    # If this is the last card in the batch, attach HTMX triggers.
    # "hx_trigger='revealed'" means when the user scrolls it into view, it fetches the next page.
    scroll_attrs = {}
    if is_last:
        scroll_attrs = {
            "hx_get": f"/?page={page_num + 1}",
            "hx_trigger": "revealed", 
            "hx_swap": "afterend"
        }

    return Div(
        H2(article.get('title', 'Untitled'), style="margin-top: 0;"),
        Div(
            Span(article.get('category', 'News'), cls="badge"),
            Span(article.get('read_time', '⏱️ ? min'), cls="badge"),
            A("Read Original ↗", href=article.get('link', '#'), target="_blank"),
            cls="meta"
        ),
        # The content container with the blur overlay
        Div(
            # Split the raw text into actual paragraphs for readability
            *[P(p) for p in article.get('full_text', '').split('\n') if p.strip()],
            
            # The clickable blur button
            Div("Read full article ↓", cls="blur-overlay", onclick="expandArticle(this)"),
            cls="article-body"
        ),
        cls="card",
        **scroll_attrs
    )

# --- 4. BACKEND ROUTING ---
@rt("/")
def get(page: int = 1):
    PAGE_SIZE = 10
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE - 1
    
    # Fetch 10 articles from Supabase, newest first
    response = supabase.table("articles").select("*").order("created_at", desc=True).range(start_idx, end_idx).execute()
    articles = response.data
    
    # Generate the HTML cards
    cards = [ArticleCard(art, page, is_last=(i == len(articles) - 1)) for i, art in enumerate(articles)]
    
    # If HTMX is making a background request for infinite scrolling, just return the raw cards
    if page > 1:
        return tuple(cards)
        
    # If it is the initial page load, return the full page layout
    return Titled("My News Portal",
        H1("Personal News Feed", style="text-align: center; color: #111827; font-weight: 800;"),
        Div(*cards, id="feed-container")
    )

serve()
