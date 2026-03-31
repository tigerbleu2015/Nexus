"""
TechPulse — Daily Article Generator
Fetches trending tech/gaming news via NewsAPI, writes a full article via Groq AI,
and saves it as a Jekyll-compatible Markdown file.
"""

import os
import re
import datetime
import requests

# ── Config ────────────────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "bb47c7769d264e79b455ddc239c5f4e4")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY  = os.getenv("PEXELS_API_KEY", "")
OUTPUT_DIR   = os.path.join("site", "_posts")
USED_FILE    = os.path.join("site", "_data", "used_stories.txt")

CATEGORIES = ["gaming", "virtual reality", "augmented reality", "tech hardware", "AI gaming"]

# ── Load / save used story titles ─────────────────────────────────────────────
def load_used() -> set:
    if not os.path.exists(USED_FILE):
        return set()
    with open(USED_FILE, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}

def mark_used(title: str):
    os.makedirs(os.path.dirname(USED_FILE), exist_ok=True)
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(title.strip().lower() + "\n")

# ── Fetch image from Pexels ───────────────────────────────────────────────────
def fetch_image(query: str) -> str:
    fallbacks = [
        "https://images.pexels.com/photos/3165335/pexels-photo-3165335.jpeg?w=1200",  # gaming setup
        "https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg?w=1200",  # tech
        "https://images.pexels.com/photos/442576/pexels-photo-442576.jpeg?w=1200",    # vr
    ]
    if not PEXELS_API_KEY:
        return fallbacks[0]
    try:
        clean = re.sub(r'[^a-z0-9 ]', '', query.lower()).strip()[:60]
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": clean, "per_page": 1, "orientation": "landscape"},
            timeout=10
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large2x"]
    except Exception as e:
        print(f"[Pexels] Image fetch failed: {e}")
    return fallbacks[0]

# ── NewsAPI: fetch top story ───────────────────────────────────────────────────
def fetch_top_story():
    used = load_used()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for category in CATEGORIES:
        params = {
            "q": category,
            "from": yesterday,
            "sortBy": "popularity",
            "language": "en",
            "pageSize": 10,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        resp.raise_for_status()
        for a in resp.json().get("articles", []):
            title = a.get("title", "")
            if (a.get("description") and "[Removed]" not in title
                    and title.lower() not in used):
                print(f"[NewsAPI] Found new story: {title}")
                return a
    raise RuntimeError("No new stories found today — all recent stories already published.")

# ── Groq: generate full article ───────────────────────────────────────────────
def generate_article(story: dict) -> str:
    today = datetime.date.today().isoformat()
    image_url = fetch_image(story['title'])
    prompt = (
        "You are a senior tech journalist for Nexus News, covering Gaming, AR, VR, and Technology.\n"
        "Write a LONG, detailed, engaging, SEO-optimized article (minimum 800 words) based on this news story.\n"
        "Write like a professional at IGN or The Verge — insightful, opinionated, with real depth.\n\n"
        f"TITLE: {story['title']}\n"
        f"DESCRIPTION: {story.get('description', '')}\n"
        f"SOURCE: {story.get('source', {}).get('name', 'Unknown')}\n\n"
        "Return ONLY valid Jekyll Markdown with this exact front matter and structure:\n\n"
        "---\n"
        'layout: post\n'
        'title: "WRITE A COMPELLING CLICK-WORTHY SEO TITLE"\n'
        f'date: {today}\n'
        'description: "ONE SENTENCE META DESCRIPTION MAX 155 CHARS"\n'
        'categories: ["Gaming"]\n'
        'tags: ["tag1", "tag2", "tag3", "tag4"]\n'
        f'image: "{image_url}"\n'
        "---\n\n"
        "## TL;DR\n\n3-4 sentence punchy executive summary that hooks the reader.\n\n"
        "## What's Going On\n\n3 full paragraphs of context, background, and what this story actually means. Be specific and detailed.\n\n"
        "## Breaking It Down\n\n2-3 paragraphs of deep technical or industry analysis. Include real numbers, comparisons, and expert-level insight.\n\n"
        "## Key Specs & Details\n\n"
        "| Specification | Detail |\n|---|---|\n"
        "| [at least 6 rows of real relevant specs or facts] | [values] |\n\n"
        "## Why Gamers Should Care\n\n2-3 paragraphs on direct real-world impact for gamers and tech enthusiasts. Be specific.\n\n"
        "## The Bigger Picture\n\n2 paragraphs on industry trends, what this signals for the future, and how it fits into the broader tech landscape.\n\n"
        "## What The Competition Is Doing\n\n1-2 paragraphs comparing to rivals or alternatives in the market.\n\n"
        "## Our Take\n\n> A sharp, confident, opinionated 3-4 sentence editorial quote. Don't be neutral — take a stance.\n\n"
        "## The Verdict\n\n2 paragraphs of strong conclusion with forward-looking predictions. End with something memorable.\n"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                         json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    print("[TechPulse] Groq responded successfully.")
    return text

# ── Save as Jekyll _posts file ────────────────────────────────────────────────
def save_article(content: str, story: dict):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    title_match = re.search(r'^title:\s*["\'](.+?)["\']', content, re.MULTILINE)
    if title_match:
        slug = re.sub(r'[^a-z0-9]+', '-', title_match.group(1).lower()).strip('-')[:60]
    else:
        slug = "daily-article"
    filename = f"{datetime.date.today().isoformat()}-{slug}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    mark_used(story["title"])
    print(f"[TechPulse] Saved: {filepath}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[TechPulse] Starting daily generation...")
    story   = fetch_top_story()
    article = generate_article(story)
    save_article(article, story)
    print("[TechPulse] Done.")
