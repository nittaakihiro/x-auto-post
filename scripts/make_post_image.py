#!/usr/bin/env python3
"""下書き投稿の添付画像を作って（任意で）Slack DMに届ける（v6・画像は必要な投稿だけ）。

方針（2026-09-08 新田さん「ニュースサイトのスクショはできない」）:
- ニュースサイト（Yahoo・ITmedia・日経・BuildApp・建設通信 等）の画面はスクショしない
- article_url が企業の公式ページ（プレスリリース・製品ページ・公式ブログ）の時だけ先頭をスクショ
- none・動画は生成しない。画像を選択した投稿は必要に応じてGeminiで図解する

使い方:
  python3 scripts/make_post_image.py --date 2026-09-08 --slack-dm     # その日の draft/pending 全部
  python3 scripts/make_post_image.py --post-id 2026-09-08_20:00 --slack-dm
環境変数: GEMINI_API_KEY（図解生成）, SLACK_BOT_TOKEN + SLACK_USER_ID（DM送付）
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "output" / "post_queue.json"
JST = timezone(timedelta(hours=9))

# ここに載るドメインは「報道・メディア」扱い → スクショせず Gemini 図解にフォールバック
NEWS_DENY = (
    "yahoo.co.jp", "itmedia.co.jp", "nikkei.com", "xtech.nikkei.com", "build-app.jp", "kensetsunews.com",
    "decn.co.jp", "techcrunch.com", "theverge.com", "arstechnica.com", "venturebeat.com", "technologyreview.com",
    "the-decoder.com", "gigazine.net", "ainow.ai", "constructiondive.com", "enr.com", "news.ycombinator.com",
    "cnbc.com", "reuters.com", "bloomberg.com", "forbes.com", "wired.com", "impress.co.jp", "ledge.ai",
    "prtimes.jp", "note.com", "x.com", "twitter.com", "youtube.com",
)


def is_news_site(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in NEWS_DENY)


def build_diagram_prompt(post: dict) -> str:
    """本文から図解プロンプトを組む（1行目=タイトル・「・」行=要点）。"""
    lines = [l.strip() for l in post["text"].split("\n") if l.strip()]
    title = re.sub(r"^【[^】]*】", "", lines[0]).strip("。 ") if lines else ""
    bullets = [l.lstrip("・").strip() for l in lines if l.startswith("・")][:5]
    src = ""
    m = re.search(r"■ 出典\s*\n(https?://\S+)", (post.get("reply") or {}).get("text") or "")
    if m:
        src = urllib.parse.urlparse(m.group(1)).netloc
    bullets_txt = "\n".join(f"- {b}" for b in bullets) if bullets else "- （本文の要点を3つ）"
    return (
        "SNS投稿用の要点図解を1枚作ってください。16:9、1600x900、白背景、フラットデザイン、人物なし、写真なし。"
        "日本語の文字は太めのゴシック体で、誤字なく正確に描画すること。文字は少なめ・余白広め・色は紺と1色のアクセントだけ。\n"
        f"上部に大きめのタイトル: 「{title}」\n"
        f"その下に要点を箇条書きで（アイコン付き、各1行）:\n{bullets_txt}\n"
        + (f"右下に小さく出典: {src}\n" if src else "")
        + "装飾やイラストは最小限。数字を大きく見せる。ロゴや実在企業のマークは描かない。"
    )


def gen_gemini(prompt: str, out_path: Path) -> Path | None:
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
    except ImportError:
        print("[WARN] google-genai / Pillow 未インストール", file=sys.stderr)
        return None
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[WARN] GEMINI_API_KEY 未設定", file=sys.stderr)
        return None
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
    for attempt in range(3):
        try:
            r = client.models.generate_content(model="gemini-3.1-flash-image-preview", contents=prompt, config=cfg)
            for part in r.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    img = Image.open(BytesIO(part.inline_data.data))
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    img.save(out_path, format="PNG")
                    print(f"[GEMINI] {out_path} ({img.size[0]}x{img.size[1]})", file=sys.stderr)
                    return out_path
        except Exception as e:
            print(f"[GEMINI] error ({attempt+1}/3): {e}", file=sys.stderr)
    return None


def gen_screenshot(url: str, out_path: Path) -> Path | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[WARN] playwright 未インストール", file=sys.stderr)
        return None
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": 1200, "height": 675}, locale="ja-JP",
                                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            pg = ctx.new_page()
            pg.goto(url, timeout=30000, wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            pg.add_style_tag(content="[id*='cookie'],[class*='cookie'],[id*='consent'],[class*='consent']{display:none!important}")
            pg.screenshot(path=str(out_path), full_page=False)
            b.close()
        print(f"[SHOT] {out_path}", file=sys.stderr)
        return out_path
    except Exception as e:
        print(f"[SHOT] error: {e}", file=sys.stderr)
        return None


def slack_api(method: str, token: str, payload: dict | None = None, form: dict | None = None) -> dict:
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/x-www-form-urlencoded"}
    else:
        data = json.dumps(payload or {}).encode()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    req = urllib.request.Request(f"https://slack.com/api/{method}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def slack_upload_dm(token: str, user_id: str, path: Path, comment: str) -> bool:
    ch = slack_api("conversations.open", token, {"users": user_id})
    if not ch.get("ok"):
        print(f"[SLACK] DM open失敗: {ch.get('error')}", file=sys.stderr)
        return False
    channel_id = ch["channel"]["id"]
    size = path.stat().st_size
    up = slack_api("files.getUploadURLExternal", token, form={"filename": path.name, "length": str(size)})
    if not up.get("ok"):
        print(f"[SLACK] getUploadURL失敗: {up.get('error')}", file=sys.stderr)
        return False
    req = urllib.request.Request(up["upload_url"], data=path.read_bytes(), method="POST",
                                 headers={"Content-Type": "application/octet-stream"})
    urllib.request.urlopen(req, timeout=60).read()
    done = slack_api("files.completeUploadExternal", token,
                     {"files": [{"id": up["file_id"], "title": path.name}], "channel_id": channel_id,
                      "initial_comment": comment})
    if not done.get("ok"):
        print(f"[SLACK] completeUpload失敗: {done.get('error')}", file=sys.stderr)
        return False
    print(f"[SLACK] 画像送付: {path.name}", file=sys.stderr)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y-%m-%d"))
    ap.add_argument("--post-id")
    ap.add_argument("--slack-dm", action="store_true", help="生成した画像をSlack DMへ送る")
    ap.add_argument("--force", action="store_true", help="既に画像があっても作り直す")
    args = ap.parse_args()

    queue = json.load(open(QUEUE))
    targets = [p for p in queue if (p["id"] == args.post_id if args.post_id else
                                    (p.get("date") == args.date and p.get("status") in ("draft", "pending")))]
    if not targets:
        print("対象なし", file=sys.stderr)
        return 0
    token = os.environ.get("SLACK_BOT_TOKEN")
    user_id = os.environ.get("SLACK_USER_ID", "U01PHHAB887")
    made = 0
    for post in targets:
        if post.get("video_url"):
            print(f"[SKIP] 動画埋め込みのため画像不要: {post['id']}", file=sys.stderr)
            continue
        img = post.get("image") or {}
        if img.get("type", "none") == "none":
            print("skip: image_type=none")
            continue
        out = ROOT / "output" / "x-dashboard" / post["date"].replace("-", ".") / "画像" / f"{post['id'].replace(':', '-')}.png"
        if out.exists() and not args.force:
            path = out
        else:
            path = None
            url = post.get("article_url") or ""
            if img.get("type") == "screenshot" and url and not is_news_site(url):
                path = gen_screenshot(url, out)
            if path is None:
                prompt = img.get("prompt") or build_diagram_prompt(post)
                path = gen_gemini(prompt, out)
        if path is None:
            print(f"[SKIP] 画像作成失敗: {post['id']}", file=sys.stderr)
            continue
        made += 1
        if args.slack_dm and token:
            kind = "公式ページのスクショ" if (img.get("type") == "screenshot" and post.get("article_url") and not is_news_site(post.get("article_url", ""))) else "AI図解"
            slack_upload_dm(token, user_id, path, f"🖼️ {post['date']} {post['time']}枠の添付画像（{kind}）。この画像を付けて投稿→■補足を自己リプ")
    print(f"done: {made}/{len(targets)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
