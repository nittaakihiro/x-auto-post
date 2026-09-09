#!/usr/bin/env python3
"""RSS/Atom から AI・建設テックの最新ニュースを集めて output/news_feed.json に書く（v5 チャエン型運用の一次ソース）。

- 依存なし（標準ライブラリのみ）。GitHub Actions (fetch-news.yml) が2時間毎に実行してcommitする
- 直近 --hours（既定48h）の記事だけ残す。URLで重複排除、新しい順
- category: ai_global / ai_japan / construction_global / construction_japan
- ai_related: 建設系フィードでAI・DX・ロボ等に触れている記事に True（夕枠「建設ニュースはAI最優先」の選別用）
"""
import argparse
import hashlib
import os
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
    {"id": "gcr", "name": "Global Construction Review", "url": "https://www.globalconstructionreview.com/feed/", "category": "construction_global", "lang": "en"},
    {"id": "construction_enquirer", "name": "Construction Enquirer (UK)", "url": "https://www.constructionenquirer.com/feed/", "category": "construction_global", "lang": "en"},
    {"id": "constructconnect", "name": "ConstructConnect Blog", "url": "https://www.constructconnect.com/blog/rss.xml", "category": "construction_global", "lang": "en"},
    {"id": "archdaily", "name": "ArchDaily", "url": "https://www.archdaily.com/feed", "category": "construction_global", "lang": "en", "keyword_filter": True},
    {"id": "aecmag", "name": "AEC Magazine", "url": "https://aecmag.com/feed/", "category": "construction_global", "lang": "en"},
    {"id": "constructionnews_uk", "name": "Construction News (UK)", "url": "https://www.constructionnews.co.uk/feed/", "category": "construction_global", "lang": "en"},
    {"id": "pbctoday", "name": "PBC Today (UK)", "url": "https://www.pbctoday.co.uk/news/feed/", "category": "construction_global", "lang": "en", "keyword_filter": True},
    {"id": "constructionexec", "name": "Construction Executive", "url": "https://www.constructionexec.com/rss", "category": "construction_global", "lang": "en"},
    # --- 建設 国内 ---
    {"id": "buildapp", "name": "BuildApp News", "url": "https://news.build-app.jp/feed", "category": "construction_japan", "lang": "ja"},
    {"id": "ken_it_world", "name": "建設ITワールド（家入龍太）", "url": "https://ken-it.world/feed/", "category": "construction_japan", "lang": "ja"},
    {"id": "sekokan_navi", "name": "施工の神様", "url": "https://sekokan-navi.jp/magazine/feed/", "category": "construction_japan", "lang": "ja"},
    {"id": "andpad_one", "name": "ANDPAD ONE", "url": "https://one.andpad.jp/feed/", "category": "construction_japan", "lang": "ja"},
    # --- 建設×AI 国内（Googleニュース検索RSS: PR TIMES・日経クロステック・ITmedia BUILT・digital-construction.jp 等をまとめて拾う） ---
    {"id": "gnews_kensetsu_ai", "name": "Google News", "url": "https://news.google.com/rss/search?q=%E5%BB%BA%E8%A8%AD%20AI%20when%3A2d&hl=ja&gl=JP&ceid=JP%3Aja", "category": "construction_japan", "lang": "ja", "gnews": True},
    {"id": "gnews_sekokan_ai", "name": "Google News", "url": "https://news.google.com/rss/search?q=%E6%96%BD%E5%B7%A5%E7%AE%A1%E7%90%86%20AI%20when%3A3d&hl=ja&gl=JP&ceid=JP%3Aja", "category": "construction_japan", "lang": "ja", "gnews": True},
    {"id": "gnews_bim_ai", "name": "Google News", "url": "https://news.google.com/rss/search?q=BIM%20AI%20when%3A3d&hl=ja&gl=JP&ceid=JP%3Aja", "category": "construction_japan", "lang": "ja", "gnews": True},
    {"id": "gnews_zenecon_ai", "name": "Google News", "url": "https://news.google.com/rss/search?q=%E3%82%BC%E3%83%8D%E3%82%B3%E3%83%B3%20%E7%94%9F%E6%88%90AI%20when%3A3d&hl=ja&gl=JP&ceid=JP%3Aja", "category": "construction_japan", "lang": "ja", "gnews": True},
    {"id": "gnews_sekisan_ai", "name": "Google News", "url": "https://news.google.com/rss/search?q=%E7%A9%8D%E7%AE%97%20AI%20when%3A7d&hl=ja&gl=JP&ceid=JP%3Aja", "category": "construction_japan", "lang": "ja", "gnews": True},
    {"id": "gnews_kensetsu_dx", "name": "Google News", "url": "https://news.google.com/rss/search?q=%E5%BB%BA%E8%A8%ADDX%20when%3A2d&hl=ja&gl=JP&ceid=JP%3Aja", "category": "construction_japan", "lang": "ja", "gnews": True, "keyword_filter": True},
    {"id": "kensetsunews", "name": "建設通信新聞", "url": "https://www.kensetsunews.com/feed", "category": "construction_japan", "lang": "ja"},
    {"id": "decn", "name": "日刊建設工業新聞", "url": "https://www.decn.co.jp/?feed=rss2", "category": "construction_japan", "lang": "ja"},
]

AI_KEYWORDS = re.compile(
    r"\bAI\b|ＡＩ|人工知能|生成AI|LLM|GPT|Claude|Gemini|OpenAI|Anthropic|DeepMind|Codex|Copilot|"
    r"エージェント|agent|機械学習|machine learning|ロボット|robot|自動化|automation|DX|BIM|デジタル|ドローン|drone|"
    r"自律|autonomous|Nvidia|NVIDIA|モデル|model",
    re.IGNORECASE,
)
# Googleニュース由来の記事で、建設の文脈が無いもの・株/相場/イベント告知系の媒体は落とす
CONSTRUCTION_WORDS = re.compile(r"建設|施工|ゼネコン|工事|BIM|CIM|積算|土木|建築|現場|工務店|設計|ビル|住宅|インフラ|解体|測量|重機|建機|構造|配筋|鉄筋|型枠|足場")
GNEWS_SOURCE_DENY = ("kabu-ir.com", "newscast.jp", "note.com", "ニコニコニュース", "株探", "minkabu", "kabutan", "Yahoo!ファイナンス", "PR TIMES TV", "時事ドットコム",
                     "みんかぶ", "投資", "モーニングスター", "Reuters", "ロイター", "日本経済新聞 電子版" if False else "___")
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


def parse_xml(data: bytes):
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        cleaned = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", data)
        return ET.fromstring(cleaned)


def parse_feed(feed: dict, data: bytes) -> list[dict]:
    root = parse_xml(data)
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
        src_name = None
        if feed.get("gnews"):
            src_el = it.find("source")
            src_name = (src_el.text or "").strip() if src_el is not None else None
            if src_name and title.endswith(" - " + src_name):
                title = title[: -len(" - " + src_name)].strip()
            summary = ""  # Googleニュースのdescriptionは見出しの繰り返しなので捨てる
        out.append({"title": title, "url": link.strip(), "published": published, "summary": strip_html(summary)[:300], "src_name": src_name})
    return out


GEMINI_MODEL = "gemini-3.5-flash-lite"


def translate_batch(items: list[dict]) -> int:
    """英語記事の title/summary を日本語にする（title_ja / summary_ja）。Gemini 1リクエストで最大20件。失敗しても止めない。"""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or not items:
        return 0
    done = 0
    for i in range(0, len(items), 20):
        chunk = items[i:i + 20]
        lines = "\n".join(f"[{n}] TITLE: {it['title']}\nSUMMARY: {it['summary'][:220]}" for n, it in enumerate(chunk))
        prompt = (
            "以下は英語ニュースの見出しと要約です。番号ごとに自然な日本語へ翻訳し、必ずJSON配列だけを出力してください。"
            "形式: [{\"n\": 0, \"title_ja\": \"...\", \"summary_ja\": \"...\"}, ...]。"
            "見出しは30字前後で簡潔に、要約は80字以内。固有名詞・製品名・企業名は原語のままでよい。\n\n" + lines
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
        for model in (GEMINI_MODEL, "gemini-2.5-flash"):
            try:
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                arr = json.loads(text)
                for row in arr:
                    n = int(row.get("n", -1))
                    if 0 <= n < len(chunk):
                        chunk[n]["title_ja"] = (row.get("title_ja") or "").strip()
                        chunk[n]["summary_ja"] = (row.get("summary_ja") or "").strip()
                        done += 1
                break
            except Exception as e:
                print(f"translate NG ({model}): {type(e).__name__} {str(e)[:80]}", file=sys.stderr)
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--out", default="output/news_feed.json")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--translate", action="store_true", help="英語記事に title_ja/summary_ja を付ける（GEMINI_API_KEY 必須）")
    args = ap.parse_args()

    # 前回出力の訳をキャッシュとして引き継ぐ（同じ記事を毎回訳さない）
    cache = {}
    try:
        for it in json.load(open(args.out)).get("items", []):
            if it.get("title_ja"):
                cache[it["id"]] = (it["title_ja"], it.get("summary_ja", ""))
    except Exception:
        pass

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
            if p["url"] in seen or ("t:" + p["title"]) in seen:
                continue
            seen.add("t:" + p["title"])
            blob = f"{p['title']} {p['summary']}"
            ai_hit = bool(AI_KEYWORDS.search(blob))
            if feed.get("keyword_filter") and not ai_hit:
                continue
            if feed.get("gnews"):
                src_lower = (p.get("src_name") or "").lower()
                if any(d.lower() in src_lower for d in GNEWS_SOURCE_DENY):
                    continue
                if not CONSTRUCTION_WORDS.search(p["title"]):
                    continue
                if re.search(r"展示会|出展|EXPO|セミナー開催|ウェビナー|市場レポート|市場規模|CAGR|銘柄|株価|上方修正", p["title"]):
                    continue
            seen.add(p["url"])
            items.append({
                "id": hashlib.sha1(p["url"].encode()).hexdigest()[:12],
                "source": (p.get("src_name") or feed["name"]) if feed.get("gnews") else feed["name"],
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

    for it in items:
        if it["id"] in cache:
            it["title_ja"], it["summary_ja"] = cache[it["id"]]
    if args.translate:
        todo = [it for it in items if it["lang"] == "en" and not it.get("title_ja")]
        n = translate_batch(todo)
        print(f"translated {n}/{len(todo)}", file=sys.stderr)
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
