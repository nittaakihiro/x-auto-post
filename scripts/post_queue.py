#!/usr/bin/env python3
"""
投稿キュー管理モジュール
post_queue.json の読み書き・投稿済みフラグ管理を行う。

キューの構造:
[
  {
    "id": "2026-03-23_09:00",
    "date": "2026-03-23",
    "time": "09:00",
    "text": "投稿テキスト",
    "type": "original",        // "original" | "quote_rt" | "thread"
    "quote_tweet_id": null,    // 引用RTの場合のみ
    "thread_texts": null,      // スレッドの場合: ["1つ目", "2つ目"]
    "image": {
      "type": "gemini",           // "gemini" | "screenshot" | "none"
      "prompt": "Geminiプロンプト", // geminiの場合
      "path": null                // 生成後のファイルパス
    },
    "reply": {
      "text": "5分後リプのテキスト",
      "delay_minutes": 5
    },
    "freshness": "locked",     // "locked" | "updatable"（朝アップデート対象かどうか）
    "status": "pending",       // "pending" | "posted" | "reply_done" | "failed"
    "tweet_id": null,          // 投稿後にセット
    "reply_tweet_id": null,    // リプ投稿後にセット
    "posted_at": null,         // 投稿日時
    "error": null              // エラー時のメッセージ
  }
]
"""

import fcntl
import json
import time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
from pathlib import Path

QUEUE_FILE = Path(__file__).resolve().parent.parent / "output" / "post_queue.json"
LOCK_FILE = QUEUE_FILE.with_suffix(".lock")


def _acquire_lock(lock_fp, timeout=10):
    """ファイルロックを取得。タイムアウト付き。"""
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError("post_queue.lock の取得タイムアウト")
            time.sleep(0.5)


def load_queue() -> list[dict]:
    """キューを読み込む。ファイルロック付き。"""
    if not QUEUE_FILE.exists():
        return []
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as lf:
        _acquire_lock(lf)
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def save_queue(queue: list[dict]):
    """キューを保存。ファイルロック付き。"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as lf:
        _acquire_lock(lf)
        try:
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def get_due_posts(queue: list[dict], now: datetime = None) -> list[dict]:
    """
    現在時刻以前でまだ投稿されていないポストを返す。
    WiFi切断→復帰時のキャッチアップにも対応。
    """
    if now is None:
        now = datetime.now(JST)

    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    due = []
    for post in queue:
        if post["status"] != "pending":
            continue
        # 今日以前の日付で、予定時刻を過ぎているもの
        if post["date"] < today:
            due.append(post)
        elif post["date"] == today and post["time"] <= current_time:
            due.append(post)
    return due


def get_pending_replies(queue: list[dict], now: datetime = None) -> list[dict]:
    """
    投稿済みだがリプがまだのポストで、delay時間を過ぎたものを返す。
    """
    if now is None:
        now = datetime.now(JST)

    pending = []
    for post in queue:
        if post["status"] != "posted":
            continue
        if not post.get("reply") or not post["reply"].get("text"):
            continue
        if not post.get("posted_at"):
            continue

        posted_at = datetime.fromisoformat(post["posted_at"])
        delay = post["reply"].get("delay_minutes", 5)
        elapsed = (now - posted_at).total_seconds() / 60

        if elapsed >= delay:
            pending.append(post)
    return pending


def mark_posted(queue: list[dict], post_id: str, tweet_id: str):
    """投稿済みにマーク。"""
    for post in queue:
        if post["id"] == post_id:
            post["status"] = "posted"
            post["tweet_id"] = tweet_id
            post["posted_at"] = datetime.now(JST).isoformat()
            break
    save_queue(queue)


def mark_reply_done(queue: list[dict], post_id: str, reply_tweet_id: str):
    """リプ投稿済みにマーク。"""
    for post in queue:
        if post["id"] == post_id:
            post["status"] = "reply_done"
            post["reply_tweet_id"] = reply_tweet_id
            break
    save_queue(queue)


def mark_failed(queue: list[dict], post_id: str, error: str):
    """失敗マーク。"""
    for post in queue:
        if post["id"] == post_id:
            post["status"] = "failed"
            post["error"] = error
            break
    save_queue(queue)


def add_post(queue: list[dict], date: str, time: str, text: str,
             post_type: str = "original", reply_text: str = None,
             reply_delay: int = 5, quote_tweet_id: str = None,
             thread_texts: list[str] = None,
             image_type: str = "none", image_prompt: str = None,
             source_query: str = None,
             freshness: str = "locked") -> list[dict]:
    """キューに投稿を追加。"""
    post_id = f"{date}_{time}"

    # 重複チェック
    if any(p["id"] == post_id for p in queue):
        print(f"[SKIP] 既に存在: {post_id}")
        return queue

    entry = {
        "id": post_id,
        "date": date,
        "time": time,
        "text": text,
        "type": post_type,
        "quote_tweet_id": quote_tweet_id,
        "thread_texts": thread_texts,
        "image": {
            "type": image_type,
            "prompt": image_prompt,
            "path": None,
        } if image_type != "none" else {"type": "none", "prompt": None, "path": None},
        "reply": {
            "text": reply_text,
            "delay_minutes": reply_delay,
            "source_query": source_query,
        } if reply_text else None,
        "freshness": freshness,  # "locked" | "updatable"
        "status": "pending",
        "tweet_id": None,
        "reply_tweet_id": None,
        "posted_at": None,
        "error": None,
    }
    queue.append(entry)
    queue.sort(key=lambda x: (x["date"], x["time"]))
    save_queue(queue)
    print(f"[ADD] キューに追加: {post_id}")
    return queue


def queue_stats(queue: list[dict]) -> dict:
    """キューの統計情報。"""
    stats = {"total": len(queue), "pending": 0, "posted": 0, "reply_done": 0, "failed": 0}
    for p in queue:
        s = p.get("status", "pending")
        if s in stats:
            stats[s] += 1
    return stats


if __name__ == "__main__":
    q = load_queue()
    s = queue_stats(q)
    print(f"キュー状態: {s}")
