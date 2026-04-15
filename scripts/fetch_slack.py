#!/usr/bin/env python3
"""Slack #x-influencer-watch の最新投稿を取得（MCP不要）"""
import json
import os
import sys
import urllib.request

CHANNEL = "C0ANXKLGC90"


def fetch(limit=30):
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


def to_json(msgs):
    out = []
    for m in msgs:
        text = m.get("text", "")
        if "x.com" not in text and "twitter.com" not in text:
            continue
        out.append({"ts": m.get("ts"), "text": text})
    return out


if __name__ == "__main__":
    msgs = fetch()
    if "--json" in sys.argv:
        print(json.dumps(to_json(msgs), ensure_ascii=False, indent=2))
    else:
        for m in msgs:
            text = m.get("text", "")
            if "x.com" in text or "twitter.com" in text:
                print(text[:300])
                print("---")
