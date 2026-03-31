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
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
OUTPUT_DIR   = os.path.join("site", "_posts")

CATEGORIES = ["gaming", "virtual reality", "augmented reality", "tech hardware", "AI gaming"]

# ── NewsAPI: fetch top story ───────────────────────────────────────────────────
def fetch_top_story():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for category in CATEGORIES:
        params = {
            "q": category,
            "from": yesterday,
            "sortBy": "popularity",
            "language": "en",
            "pageSize": 5,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        resp.raise_for_status()
        for a in resp.json().get("articles", []):
            if a.get("title") and a.get("description") and "[Removed]" not in a["title"]:
                print(f"[NewsAPI] Found: {a['title']}")
                return a
    raise RuntimeError("No suitable news story found today.")

# ── Groq: generate full article ───────────────────────────────────────────────
def generate_article(story: dict) -> str:
    today = datetime.date.today().isoformat()
    prompt = (
        "You are a senior tech journalist for TechPulse, covering Gaming, AR, VR, and Technology.\n"
        "Write a complete SEO-optimized article based on this news story.\n\n"
        f"TITLE: {story['title']}\n"
        f"DESCRIPTION: {story.get('description', '')}\n"
        f"SOURCE: {story.get('source', {}).get('name', 'Unknown')}\n\n"
        "Return ONLY valid Jekyll Markdown with this exact front matter and structure:\n\n"
        "---\n"
        'layout: post\n'
        'title: "WRITE A COMPELLING SEO TITLE HERE"\n'
        f'date: {today}\n'
        'description: "ONE SENTENCE META DESCRIPTION MAX 155 CHARS"\n'
        'categories: ["Gaming"]\n'
        'tags: ["tag1", "tag2", "tag3"]\n'
        "---\n\n"
        "## TL;DR\n\n2-3 sentence summary.\n\n"
        "## Overview\n\n2-3 paragraphs of analysis.\n\n"
        "## Key Specifications\n\n"
        "| Specification | Detail |\n|---|---|\n| Item | Value |\n\n"
        "## What This Means for Gamers\n\n2 paragraphs.\n\n"
        "## Industry Reaction\n\n1-2 paragraphs.\n\n"
        "## Our Take\n\n> Editorial opinion in 2-3 sentences.\n\n"
        "## Verdict\n\n1-2 paragraph conclusion.\n"
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
def save_article(content: str):
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
    print(f"[TechPulse] Saved: {filepath}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[TechPulse] Starting daily generation...")
    story   = fetch_top_story()
    article = generate_article(story)
    save_article(article)
    print("[TechPulse] Done.")
