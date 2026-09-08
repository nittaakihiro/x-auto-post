#!/usr/bin/env python3
"""Slack #x-influencer-watch の最新投稿を取得（MCP不要）。

v5（2026-09-08）: ローカルの x_watcher.py がAI系アカウント（海外・国内）も同じチャンネルに
「🌐 AI」タグ付きで流すようになったので、建設系とAI系を分けて出力する。
  --json      建設系（従来どおり slack_buzz.json 用）
  --json-ai   AI系（ai_buzz.json 用）
  --json-all  両方（category 付き）
"""
import json
import os
import sys
import urllib.request

CHANNEL = "C0ANXKLGC90"
AI_TAG = "🌐"


def fetch(limit=150):
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN環境変数が未設定", file=sys.stderr)
        return []
    url = f"https://slack.com/api/conversations.history?channel={CHANNEL}&limit={limit}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    if not data.get("ok"):
        print(f"Slack API error: {data.get('error')}", file=sys.stderr)
        return []
    return data.get("messages", [])


def classify(text: str) -> str:
    head = text.split("\n", 1)[0]
    return "ai" if AI_TAG in head else "construction"


def to_json(msgs, category=None):
    out = []
    for m in msgs:
        text = m.get("text", "")
        if "x.com" not in text and "twitter.com" not in text:
            continue
        cat = classify(text)
        if category and cat != category:
            continue
        out.append({"ts": m.get("ts"), "category": cat, "text": text})
    return out


if __name__ == "__main__":
    msgs = fetch()
    if "--json-ai" in sys.argv:
        print(json.dumps(to_json(msgs, "ai"), ensure_ascii=False, indent=2))
    elif "--json-all" in sys.argv:
        print(json.dumps(to_json(msgs), ensure_ascii=False, indent=2))
    elif "--json" in sys.argv:
        print(json.dumps(to_json(msgs, "construction"), ensure_ascii=False, indent=2))
    else:
        for m in msgs:
            text = m.get("text", "")
            if "x.com" in text or "twitter.com" in text:
                print(text[:300])
                print("---")
