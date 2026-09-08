#!/usr/bin/env python3
"""RSS/Atom から AI・建設テックの最新ニュースを集めて output/news_feed.json に書く（v5 チャエン型運用の一次ソース）。

- 依存なし（標準ライブラリのみ）。GitHub Actions (fetch-news.yml) が2時間毎に実行してcommitする
- 直近 --hours（既定48h）の記事だけ残す。URLで重複排除、新しい順
- category: ai_global / ai_japan / construction_global / construction_japan
- ai_related: 建設系フィードでAI・DX・ロボ等に触れている記事に True（夕枠「建設ニュースはAI最優先」の選別用）
"""
import argparse
import hashlib
import html
import json
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEEDS = [
    # --- AI 海外（一次ソース優先） ---
    {"id": "openai", "name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "category": "ai_global", "lang": "en"},
    {"id": "deepmind", "name": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml", "category": "ai_global", "lang": "en"},
    {"id": "google_ai", "name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "category": "ai_global", "lang": "en"},
    {"id": "nvidia", "name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/feed/", "category": "ai_global", "lang": "en"},
    {"id": "techcrunch_ai", "name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "ai_global", "lang": "en"},
    {"id": "verge_ai", "name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "ai_global", "lang": "en"},
    {"id": "arstechnica_ai", "name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "category": "ai_global", "lang": "en"},
    {"id": "venturebeat_ai", "name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": "ai_global", "lang": "en"},
    {"id": "mit_tr", "name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "category": "ai_global", "lang": "en"},
    {"id": "the_decoder", "name": "The Decoder", "url": "https://the-decoder.com/feed/", "category": "ai_global", "lang": "en"},
    {"id": "simonw", "name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "category": "ai_global", "lang": "en"},
    {"id": "hn_top", "name": "Hacker News (150pt+)", "url": "https://hnrss.org/frontpage?points=150", "category": "ai_global", "lang": "en", "keyword_filter": True},
    # --- AI 国内 ---
    {"id": "itmedia_ai", "name": "ITmedia AI+", "url": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml", "category": "ai_japan", "lang": "ja"},
    {"id": "gigazine", "name": "GIGAZINE", "url": "https://gigazine.net/news/rss_2.0/", "category": "ai_japan", "lang": "ja", "keyword_filter": True},
    {"id": "ainow", "name": "AINOW", "url": "https://ainow.ai/feed/", "category": "ai_japan", "lang": "ja"},
    # --- 建設テック 海外 ---
    {"id": "construction_dive", "name": "Construction Dive", "url": "https://www.constructiondive.com/feeds/news/", "category": "construction_global", "lang": "en"},
    # --- 建設 国内 ---
    {"id": "buildapp", "name": "BuildApp News", "url": "https://news.build-app.jp/feed", "category": "construction_japan", "lang": "ja"},
    {"id": "kensetsunews", "name": "建設通信新聞", "url": "https://www.kensetsunews.com/feed", "category": "construction_japan", "lang": "ja"},
    {"id": "decn", "name": "日刊建設工業新聞", "url": "https://www.decn.co.jp/?feed=rss2", "category": "construction_japan", "lang": "ja"},
]

AI_KEYWORDS = re.compile(
    r"\bAI\b|ＡＩ|人工知能|生成AI|LLM|GPT|Claude|Gemini|OpenAI|Anthropic|DeepMind|Codex|Copilot|"
    r"エージェント|agent|機械学習|machine learning|ロボット|robot|自動化|automation|DX|BIM|デジタル|ドローン|drone|"
    r"自律|autonomous|Nvidia|NVIDIA|モデル|model",
    re.IGNORECASE,
)
NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/", "content": "http://purl.org/rss/1.0/modules/content/"}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s.replace("Z", "+0000") if fmt.endswith("%z") else s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def text_of(el, *paths):
    for p in paths:
        node = el.find(p, NS)
        if node is not None:
            if p.endswith("link") and node.get("href"):
                return node.get("href")
            if node.text:
                return node.text
    return ""


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        return r.read()


def parse_feed(feed: dict, data: bytes) -> list[dict]:
    root = ET.fromstring(data)
    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = root.findall(".//atom:entry", NS)
        is_atom = True
    out = []
    for it in items:
        if is_atom:
            title = text_of(it, "atom:title")
            link = ""
            for l in it.findall("atom:link", NS):
                if l.get("rel") in (None, "alternate"):
                    link = l.get("href") or ""
                    break
            published = parse_date(text_of(it, "atom:published", "atom:updated"))
            summary = text_of(it, "atom:summary", "atom:content")
        else:
            title = text_of(it, "title")
            link = text_of(it, "link") or (it.find("guid").text if it.find("guid") is not None else "")
            published = parse_date(text_of(it, "pubDate", "dc:date"))
            summary = text_of(it, "description", "content:encoded")
        title = strip_html(title)
        if not title or not link:
            continue
        out.append({"title": title, "url": link.strip(), "published": published, "summary": strip_html(summary)[:300]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--out", default="output/news_feed.json")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.hours)
    items, errors, seen = [], [], set()
    for feed in FEEDS:
        try:
            data = fetch(feed["url"])
            parsed = parse_feed(feed, data)
        except Exception as e:
            errors.append({"feed": feed["id"], "error": f"{type(e).__name__}: {str(e)[:80]}"})
            print(f"NG {feed['id']}: {type(e).__name__} {str(e)[:80]}", file=sys.stderr)
            continue
        kept = 0
        for p in parsed:
            if p["published"] and p["published"] < cutoff:
                continue
            if p["url"] in seen:
                continue
            blob = f"{p['title']} {p['summary']}"
            ai_hit = bool(AI_KEYWORDS.search(blob))
            if feed.get("keyword_filter") and not ai_hit:
                continue
            seen.add(p["url"])
            items.append({
                "id": hashlib.sha1(p["url"].encode()).hexdigest()[:12],
                "source": feed["name"],
                "source_id": feed["id"],
                "category": feed["category"],
                "lang": feed["lang"],
                "title": p["title"],
                "url": p["url"],
                "published": p["published"].astimezone(timezone.utc).isoformat(timespec="minutes") if p["published"] else None,
                "published_jst": p["published"].astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M") if p["published"] else None,
                "summary": p["summary"],
                "ai_related": ai_hit if feed["category"].startswith("construction") else True,
            })
            kept += 1
        print(f"OK {feed['id']}: {kept}件", file=sys.stderr)

    items.sort(key=lambda x: x["published"] or "", reverse=True)
    items = items[: args.limit]
    counts = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    out = {
        "generated_at": now.isoformat(timespec="minutes"),
        "generated_at_jst": now.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
        "window_hours": args.hours,
        "counts": counts,
        "errors": errors,
        "items": items,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {args.out}: {len(items)}件 {counts} errors={len(errors)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
