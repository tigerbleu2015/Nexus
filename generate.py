"""
TechPulse — Daily Article Generator
Fetches trending tech/gaming news via NewsAPI, writes a full article via Gemini AI,
and saves it as a Hugo-compatible Markdown file.
"""

import os
import re
import datetime
import requests
from google import genai
from google.genai import types

# ── Config ────────────────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "bb47c7769d264e79b455ddc239c5f4e4")
OUTPUT_DIR   = os.path.join("site", "content", "posts")

# Pool of Gemini keys — add more as needed, script rotates on quota exhaustion
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "AIzaSyAxdhwFp7kgpPt7TIL09DWB0xPKP5EZiwM,AIzaSyBRV4iTJ5K_kaJlhDxGB94AjzKCaLt50WQ,AIzaSyBXpQQL_5Mrbk6afwcH4_czydnAo725Aps,AIzaSyBuo4ODSWhidUvNdAqmFjAzZuviCnL7JRs").split(",") if k.strip()]

CATEGORIES = ["gaming", "virtual reality", "augmented reality", "tech hardware", "AI gaming"]

# ── NewsAPI: fetch top story ───────────────────────────────────────────────────
def fetch_top_story():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for category in CATEGORIES:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": category,
            "from": yesterday,
            "sortBy": "popularity",
            "language": "en",
            "pageSize": 5,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        for a in articles:
            if a.get("title") and a.get("description") and "[Removed]" not in a["title"]:
                print(f"[NewsAPI] Found: {a['title']}")
                return a
    raise RuntimeError("No suitable news story found today.")

# ── Gemini: generate full article ─────────────────────────────────────────────
def generate_article(story: dict) -> str:
    prompt = (
        "You are a senior tech journalist writing for TechPulse, a high-end professional website\n"
        "covering Gaming, AR, VR, and Technology. Your audience is enthusiast gamers and tech professionals.\n\n"
        "Write a complete, SEO-optimized article based on the following news story.\n\n"
        f"NEWS TITLE: {story['title']}\n"
        f"NEWS DESCRIPTION: {story.get('description', '')}\n"
        f"SOURCE: {story.get('source', {}).get('name', 'Unknown')}\n\n"
        "STRICT OUTPUT FORMAT — return ONLY the following Markdown, nothing else:\n\n"
        "---\n"
        'title: "[Compelling SEO title here]"\n'
        f"date: {datetime.date.today().isoformat()}\n"
        'description: "[One-sentence meta description, max 155 chars]"\n'
        'categories: ["[Primary: Gaming OR AR/VR OR Tech]"]\n'
        'tags: ["tag1", "tag2", "tag3", "tag4"]\n'
        "---\n\n"
        "## TL;DR\n\n[2-3 sentence executive summary]\n\n"
        "## Overview\n\n[2-3 paragraphs of professional analysis and context]\n\n"
        "## Key Specifications / Details\n\n"
        "| Specification | Detail |\n|---|---|\n"
        "| [Spec 1] | [Value] |\n| [Spec 2] | [Value] |\n| [Spec 3] | [Value] |\n| [Spec 4] | [Value] |\n\n"
        "## What This Means for Gamers / Tech Users\n\n[2 paragraphs on real-world impact]\n\n"
        "## Industry Reaction\n\n[1-2 paragraphs on broader industry context]\n\n"
        "## Our Take\n\n> [A sharp, opinionated 2-3 sentence editorial quote]\n\n"
        "## Verdict\n\n[Final 1-2 paragraph conclusion with forward-looking insight]\n"
    )

    last_error = None
    for key in GEMINI_KEYS:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            print(f"[TechPulse] Gemini responded successfully.")
            return response.text.strip()
        except Exception as e:
            print(f"[TechPulse] Key failed ({str(e)[:80]}), trying next...")
            last_error = e
    raise RuntimeError(f"All Gemini keys exhausted. Last error: {last_error}")

# ── Save as Hugo Markdown file ─────────────────────────────────────────────────
def save_article(content: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Extract title from front matter for filename
    title_match = re.search(r'^title:\s*["\'](.+?)["\']', content, re.MULTILINE)
    if title_match:
        slug = re.sub(r'[^a-z0-9]+', '-', title_match.group(1).lower()).strip('-')
    else:
        slug = f"article-{datetime.date.today().isoformat()}"

    filename = f"{datetime.date.today().isoformat()}-{slug[:60]}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[TechPulse] Article saved: {filepath}")
    return filepath

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[TechPulse] Starting daily generation...")
    story   = fetch_top_story()
    article = generate_article(story)
    save_article(article)
    print("[TechPulse] Done.")
