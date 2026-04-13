#!/usr/bin/env python3
"""
X自動投稿スクリプト（cron実行用）

cron設定例:
  */5 9-21 * * * cd /Users/akihiro/Desktop/AI-work && /usr/bin/python3 scripts/auto_post.py >> /tmp/x-auto-post.log 2>&1

動作:
  1. post_queue.json から現在時刻以前の未投稿ポストを取得
  2. X APIで投稿
  3. 投稿済みフラグをセット
  4. delay時間経過後のリプ待ちポストがあればリプ投稿
  5. ログ出力

WiFi切断対応:
  - 予定時刻を過ぎたpendingポストは全て投稿される（キャッチアップ）
  - 同日分のみキャッチアップ（前日以前は自動スキップ）
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import time
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 日本時間 (JST = UTC+9)
JST = timezone(timedelta(hours=9))

# 全HTTP呼び出しのデフォルトタイムアウト（昨日の17時間SSL readハング再発防止）
socket.setdefaulttimeout(60)

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from post_queue import (
    load_queue,
    save_queue,
    get_due_posts,
    get_pending_replies,
    mark_posted,
    mark_reply_done,
    mark_failed,
    queue_stats,
)
from x_poster import XPoster

# ログ設定
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("auto_post")

# 前日以前のpendingは自動スキップ（古い投稿を今さら投稿しない）
SKIP_OLD_DAYS = True


def fetch_latest_source(search_query: str) -> str | None:
    """
    Google検索で最新のニュース記事URLを取得する。
    リプライのソースリンクを投稿直前に最新化するために使う。
    """
    try:
        # Google Custom Search API（無料枠: 100回/日）
        api_key = os.environ.get("GOOGLE_API_KEY")
        cx = os.environ.get("GOOGLE_CSE_ID")

        if not api_key or not cx:
            # API未設定の場合はフォールバック: そのまま返す
            log.warning("GOOGLE_API_KEY/GOOGLE_CSE_ID未設定。ソース最新化スキップ。")
            return None

        params = urllib.parse.urlencode({
            "key": api_key,
            "cx": cx,
            "q": search_query,
            "sort": "date",
            "num": 1,
        })
        url = f"https://www.googleapis.com/customsearch/v1?{params}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        items = data.get("items", [])
        if items:
            result_url = items[0]["link"]
            result_title = items[0].get("title", "")
            log.info(f"[SOURCE] 最新ソース取得: {result_title} → {result_url}")
            return result_url

    except Exception as e:
        log.warning(f"[SOURCE] 最新ソース取得失敗: {e}")

    return None


def update_reply_source(post: dict) -> None:
    """
    リプにsource_queryが設定されている場合、投稿直前に最新ソースを検索して
    リプ本文のURLを差し替える。
    """
    reply = post.get("reply")
    if not reply:
        return

    source_query = reply.get("source_query")
    if not source_query:
        return

    latest_url = fetch_latest_source(source_query)
    if not latest_url:
        return

    text = reply["text"]
    # 既存URLを差し替え（http/httpsで始まるURL）
    url_pattern = r'https?://\S+'
    if re.search(url_pattern, text):
        reply["text"] = re.sub(url_pattern, latest_url, text)
        log.info(f"[SOURCE] リプのソースURLを最新化: {latest_url}")
    else:
        # URLがない場合は末尾に追加
        reply["text"] = f"{text}\n{latest_url}"
        log.info(f"[SOURCE] リプにソースURL追加: {latest_url}")


def run():
    # プロセスロック: 二重起動を防止（cron重複対策）
    lock_path = Path(__file__).resolve().parent.parent / "output" / "auto_post.pid"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fp = open(lock_path, "w")
    try:
        import fcntl
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.warning("別プロセスが実行中。スキップ。")
        lock_fp.close()
        return

    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")

    # 時間帯ガード: 7:00-21:00 JST 以外は実行しない
    if now.hour < 7 or now.hour >= 21:
        return

    log.info(f"=== 自動投稿チェック開始 ({now.strftime('%Y-%m-%d %H:%M')}) ===")

    queue = load_queue()
    if not queue:
        log.info("キューが空です。終了。")
        return

    poster = XPoster()

    # --- 1. 未投稿ポストの投稿 ---
    due_posts = get_due_posts(queue, now)

    if SKIP_OLD_DAYS:
        skipped = [p for p in due_posts if p["date"] < today]
        due_posts = [p for p in due_posts if p["date"] >= today]
        for p in skipped:
            mark_failed(queue, p["id"], "日付超過のためスキップ")
            log.warning(f"スキップ（日付超過）: {p['id']}")

    for post in due_posts:
        try:
            # --- 投稿直前に再チェック: 別プロセスが先に投稿済みかもしれない ---
            fresh_queue = load_queue()
            fresh_post = next((p for p in fresh_queue if p["id"] == post["id"]), None)
            if not fresh_post or fresh_post["status"] != "pending":
                log.info(f"スキップ（既に処理済み）: {post['id']}")
                continue
            queue = fresh_queue  # 以降は最新のqueueを使う

            # --- 引用RTでquote_tweet_idがない場合はスキップ（手動投稿前提） ---
            if post["type"] == "quote_rt" and not post.get("quote_tweet_id"):
                log.info(f"スキップ（引用RT/quote_tweet_id未設定）: {post['id']} → 手動投稿してください")
                continue

            # --- 画像生成（Geminiプロンプトがある場合） ---
            media_ids = None
            img_info = post.get("image", {})
            if isinstance(img_info, dict) and img_info.get("type") == "gemini" and img_info.get("prompt"):
                if not img_info.get("path"):
                    # 画像パス: output/x-dashboard/{date}/画像/{post_id}.png
                    img_dir = Path(__file__).resolve().parent.parent / "output" / "x-dashboard" / post["date"].replace("-", ".") / "画像"
                    img_path = str(img_dir / f"{post['id'].replace(':', '-')}.png")
                    generated = poster.generate_image(img_info["prompt"], img_path)
                    if generated:
                        img_info["path"] = generated
                        save_queue(queue)

                if img_info.get("path") and Path(img_info["path"]).exists():
                    mid = poster.upload_media(img_info["path"])
                    media_ids = [mid]

            # --- 投稿 ---
            if post["type"] == "quote_rt" and post.get("quote_tweet_id"):
                tweet_id = poster.quote(post["text"], post["quote_tweet_id"])
            elif post["type"] == "thread" and post.get("thread_texts"):
                ids = poster.thread(post["thread_texts"], media_ids=media_ids)
                tweet_id = ids[0] if ids else None
            else:
                tweet_id = poster.post(post["text"], media_ids=media_ids)

            if tweet_id:
                mark_posted(queue, post["id"], tweet_id)
                log.info(f"投稿成功: {post['id']} → tweet:{tweet_id}")
            else:
                mark_failed(queue, post["id"], "tweet_idが取得できませんでした")

            # 連続投稿のレート制限対策（2秒間隔）
            time.sleep(2)

        except Exception as e:
            mark_failed(queue, post["id"], str(e))
            log.error(f"投稿失敗: {post['id']} → {e}")

    # --- 2. リプライの投稿 ---
    queue = load_queue()  # 最新状態を再読み込み
    pending_replies = get_pending_replies(queue, now)

    for post in pending_replies:
        try:
            # ソースURLを投稿直前に最新化
            update_reply_source(post)
            save_queue(queue)

            reply_id = poster.reply(post["tweet_id"], post["reply"]["text"])
            mark_reply_done(queue, post["id"], reply_id)
            log.info(f"リプ成功: {post['id']} → reply:{reply_id}")
            time.sleep(2)
        except Exception as e:
            log.error(f"リプ失敗: {post['id']} → {e}")

    # --- 3. 統計表示 ---
    queue = load_queue()
    stats = queue_stats(queue)
    log.info(f"キュー状態: {stats}")
    log.info("=== 完了 ===")

    # プロセスロック解放
    import fcntl
    fcntl.flock(lock_fp, fcntl.LOCK_UN)
    lock_fp.close()


if __name__ == "__main__":
    run()
