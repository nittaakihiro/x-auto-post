#!/usr/bin/env python3
"""海外ニュースの日本語ダイジェストを Slack DM に送る（v5・朝7時/夕18時 JST）。

output/news_feed.json（fetch_news.py --translate 済み）から、直近 --hours 時間の
海外建設（construction_global）と海外AI（ai_global）を title_ja 付きで並べる。
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def slack_api(method, token, payload):
    req = urllib.request.Request(f"https://slack.com/api/{method}", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fmt(it):
    title = it.get("title_ja") or it.get("title")
    flag = "🤖" if it.get("ai_related") else "•"
    src = it["source"]
    line = f"{flag} *{title}*\n　　{src}・{it.get('published_jst','')[5:]}　<{it['url']}|記事>"
    if it.get("summary_ja"):
        line += f"\n　　{it['summary_ja'][:90]}"
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=14)
    ap.add_argument("--feed", default="output/news_feed.json")
    ap.add_argument("--max-construction", type=int, default=10)
    ap.add_argument("--max-ai", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.feed))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).isoformat(timespec="minutes")
    fresh = [it for it in d["items"] if (it.get("published") or "") >= cutoff]
    # 海外建設: AI関連を先頭 → テック寄り媒体を優先 → 新しい順。英国のローカル受注ニュースは媒体ごとに2件まで
    PRIORITY = {"AEC Magazine": 0, "Construction Dive": 1, "Global Construction Review": 2, "Construction Executive": 3,
                "ConstructConnect Blog": 4, "ArchDaily": 5, "Construction News (UK)": 6, "PBC Today (UK)": 7, "Construction Enquirer (UK)": 8}
    PER_SOURCE_CAP = {"Construction Enquirer (UK)": 2, "Construction News (UK)": 2, "PBC Today (UK)": 2}
    cons_all = sorted([it for it in fresh if it["category"] == "construction_global"],
                      key=lambda x: (0 if x.get("ai_related") else 1, PRIORITY.get(x["source"], 9),
                                     -(datetime.fromisoformat(x["published"]).timestamp())))
    cons, seen = [], {}
    for it in cons_all:
        cap = PER_SOURCE_CAP.get(it["source"])
        if cap and seen.get(it["source"], 0) >= cap and not it.get("ai_related"):
            continue
        seen[it["source"]] = seen.get(it["source"], 0) + 1
        cons.append(it)
        if len(cons) >= args.max_construction:
            break
    ai = [it for it in fresh if it["category"] == "ai_global"][: args.max_ai]
    PRIORITY_JP = {"PR TIMES": 0, "xtech.nikkei.com": 1, "日経クロステック": 1, "built.itmedia.co.jp": 2, "ITmedia": 2, "digital-construction.jp": 3,
                   "BuildApp News": 4, "建設通信新聞": 5, "日刊建設工業新聞": 5, "建設ITワールド（家入龍太）": 6, "ANDPAD ONE": 7, "施工の神様": 8}
    jp = sorted([it for it in fresh if it["category"] == "construction_japan" and it.get("ai_related")],
                key=lambda x: (PRIORITY_JP.get(x["source"], 9), -(datetime.fromisoformat(x["published"]).timestamp())))[: args.max_construction]
    if not cons and not ai and not jp:
        print("新着なし", file=sys.stderr)
        return 0

    now = datetime.now(JST)
    head = f"🌏 *建設×AIニュース（海外は日本語訳）* {now.strftime('%-m/%-d %H:%M')}　直近{args.hours}h"
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": head}}]
    if cons:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*🏗️ 海外・建設（{len(cons)}件・🤖=AI関連）*"}})
        for it in cons:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": fmt(it)}})
    if jp:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*🇯🇵 国内・建設×AI（{len(jp)}件）*"}})
        for it in jp:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": fmt(it)}})
    if ai:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*🤖 海外・AI（{len(ai)}件）*"}})
        for it in ai:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": fmt(it)}})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "元データ: x-auto-post/output/news_feed.json（2時間毎更新・Gemini訳）"}]})

    if args.dry_run:
        for b in blocks:
            print(b.get("text", {}).get("text", ""))
        return 0
    token = os.environ["SLACK_BOT_TOKEN"]
    user = os.environ.get("SLACK_USER_ID", "U01PHHAB887")
    ch = slack_api("conversations.open", token, {"users": user})["channel"]["id"]
    for i in range(0, len(blocks), 48):
        r = slack_api("chat.postMessage", token, {"channel": ch, "blocks": blocks[i:i + 48], "text": head})
        if not r.get("ok"):
            print("Slack error:", r.get("error"), file=sys.stderr)
            return 1
    print(f"sent: construction {len(cons)} / jp-construction-ai {len(jp)} / ai {len(ai)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
