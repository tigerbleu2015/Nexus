"""
Nexus News — Daily Article Generator
Fetches trending tech/gaming news, writes a full SEO-optimized article via Groq,
saves it as a Jekyll post. Deduplicates by article URL to prevent same-topic repeats.
"""

import os
import re
import datetime
import requests

# ── Config ────────────────────────────────────────────────────────────────────
NEWS_API_KEY   = os.getenv("NEWS_API_KEY",  "bb47c7769d264e79b455ddc239c5f4e4")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",  "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
OUTPUT_DIR     = os.path.join("site", "_posts")
USED_FILE      = os.path.join("site", "_data", "used_stories.txt")

CATEGORIES = ["gaming", "virtual reality", "augmented reality", "tech hardware", "AI gaming"]

# ── Deduplication (by URL — more reliable than title) ─────────────────────────
def load_used() -> set:
    if not os.path.exists(USED_FILE):
        return set()
    with open(USED_FILE, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}

def mark_used(url: str, title: str):
    os.makedirs(os.path.dirname(USED_FILE), exist_ok=True)
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(url.strip().lower() + "\n")
        f.write(title.strip().lower() + "\n")

# ── Pexels image ──────────────────────────────────────────────────────────────
def fetch_image(query: str) -> str:
    fallbacks = [
        "https://images.pexels.com/photos/3165335/pexels-photo-3165335.jpeg?w=1200",
        "https://images.pexels.com/photos/1714208/pexels-photo-1714208.jpeg?w=1200",
        "https://images.pexels.com/photos/442576/pexels-photo-442576.jpeg?w=1200",
    ]
    if not PEXELS_API_KEY:
        return fallbacks[0]
    try:
        clean = re.sub(r'[^a-z0-9 ]', '', query.lower()).strip()[:60]
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": clean, "per_page": 3, "orientation": "landscape"},
            timeout=10
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large2x"]
    except Exception as e:
        print(f"[Pexels] {e}")
    return fallbacks[0]

# ── NewsAPI ───────────────────────────────────────────────────────────────────
def fetch_top_story():
    used = load_used()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    seen_urls = set()  # dedupe within this run across categories

    for category in CATEGORIES:
        params = {
            "q": category, "from": yesterday,
            "sortBy": "popularity", "language": "en",
            "pageSize": 10, "apiKey": NEWS_API_KEY,
        }
        resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        resp.raise_for_status()
        for a in resp.json().get("articles", []):
            url   = (a.get("url") or "").lower()
            title = (a.get("title") or "").strip()
            if (a.get("description")
                    and "[Removed]" not in title
                    and url not in seen_urls
                    and url not in used
                    and title.lower() not in used):
                seen_urls.add(url)
                print(f"[NewsAPI] Found: {title}")
                return a
    raise RuntimeError("No new stories found — all recent stories already published.")

# ── Groq article generation ───────────────────────────────────────────────────
def generate_article(story: dict) -> str:
    today      = datetime.date.today().isoformat()
    image_url  = fetch_image(story["title"])
    # Sanitize inputs — strip non-ASCII and truncate to safe lengths
    title  = story["title"].encode("ascii", "ignore").decode()[:200]
    desc   = (story.get("description") or "").encode("ascii", "ignore").decode()[:400]
    source = (story.get("source", {}).get("name") or "Unknown").encode("ascii", "ignore").decode()[:100]

    prompt = f"""You are a senior tech journalist at Nexus News covering Gaming, AR, VR, and Technology.
Write a LONG (minimum 900 words), deeply engaging, SEO-optimized article based on this news story.
Write like a professional at IGN or The Verge — insightful, opinionated, specific, with real depth.

NEWS TITLE: {title}
NEWS DESCRIPTION: {desc}
SOURCE: {source}

IMPORTANT SEO RULES:
- Title must include the main keyword naturally and be under 65 characters
- Description must be under 155 characters and include the main keyword
- Use the main keyword in the first paragraph
- Include related keywords naturally throughout
- Write for humans first, search engines second

Return ONLY valid Jekyll Markdown with EXACTLY this structure (no extra text before or after):

---
layout: post
title: "COMPELLING SEO TITLE UNDER 65 CHARS"
date: {today}
description: "META DESCRIPTION UNDER 155 CHARS WITH MAIN KEYWORD"
categories: ["Gaming"]
tags: ["tag1", "tag2", "tag3", "tag4", "tag5"]
image: "{image_url}"
---

## TL;DR

3-4 punchy sentences that hook the reader immediately. Include the main keyword.

## What's Happening

3 detailed paragraphs covering the full context, background, and significance. Be specific with names, numbers, and dates.

## Deep Dive

2-3 paragraphs of expert technical or industry analysis. Include real comparisons, benchmarks, or market data where relevant.

## Key Specs & Facts

| Specification | Detail |
|---|---|
| [6+ rows of real, specific specs or facts relevant to this story] | [accurate values] |

## Why This Matters to You

2-3 paragraphs on direct real-world impact. Speak directly to gamers and tech enthusiasts. Be specific about what changes for them.

## The Bigger Picture

2 paragraphs on what this signals for the industry, upcoming trends, and where things are heading in the next 12-24 months.

## How It Stacks Up Against the Competition

1-2 paragraphs comparing to direct rivals or alternatives. Name names.

## Our Take

> 3-4 sentence sharp editorial opinion. Take a clear stance. Don't sit on the fence.

## Final Verdict

2 strong paragraphs of conclusion with a forward-looking prediction. End with a memorable line.
"""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.72,
        "max_tokens": 3000,
    }
    resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                         json=payload, headers=headers, timeout=90)
    if not resp.ok:
        print(f"[Groq Error] {resp.status_code}: {resp.text[:300]}")
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    # Strip any markdown code fences the model might add
    text = re.sub(r'^```(?:markdown|md)?\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```$', '', text, flags=re.MULTILINE)
    print("[Nexus] Groq responded successfully.")
    return text.strip()

# ── Save Jekyll post ──────────────────────────────────────────────────────────
def save_article(content: str, story: dict):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    title_match = re.search(r'^title:\s*["\'](.+?)["\']', content, re.MULTILINE)
    slug = re.sub(r'[^a-z0-9]+', '-', title_match.group(1).lower()).strip('-')[:60] if title_match else "daily-article"
    filepath = os.path.join(OUTPUT_DIR, f"{datetime.date.today().isoformat()}-{slug}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    mark_used(story.get("url", ""), story["title"])
    print(f"[Nexus] Saved: {filepath}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[Nexus News] Starting daily generation...")
    story   = fetch_top_story()
    article = generate_article(story)
    save_article(article, story)
    print("[Nexus News] Done.")
