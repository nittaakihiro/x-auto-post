#!/usr/bin/env python3
"""自分の直近投稿のpublic_metricsを取得して data/analytics/live_metrics.json に保存。

週次アナリティクス（x-analytics-weekly ルーティン）の入力。ユーザーが手動で
CSVを置かなくてもフィードバックループが回るようにする。
GitHub Actions (fetch-metrics.yml) から週1で実行される。
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_poster import XPoster

OUT = Path(__file__).resolve().parent.parent / "data" / "analytics" / "live_metrics.json"


HISTORY = OUT.parent / "followers_history.jsonl"


def main():
    poster = XPoster()
    tweets = poster.get_my_tweets(100)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(tweets),
        "tweets": tweets,
    }
    # フォロワー数（主KPI）。取得失敗してもツイートメトリクスは保存する
    try:
        me = poster.client.get_me(user_fields=["public_metrics"])
        pm = dict(me.data.public_metrics or {})
        payload["account"] = {
            "username": me.data.username,
            "followers": pm.get("followers_count"),
            "following": pm.get("following_count"),
            "tweet_count": pm.get("tweet_count"),
        }
    except Exception as e:
        print(f"[METRICS] フォロワー数取得失敗: {e}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    if payload.get("account", {}).get("followers") is not None:
        with HISTORY.open("a") as f:
            f.write(json.dumps({
                "date": datetime.now(timezone.utc).date().isoformat(),
                "followers": payload["account"]["followers"],
            }) + "\n")
    print(f"[METRICS] {len(tweets)}件を {OUT} に保存 / followers={payload.get('account', {}).get('followers')}")


if __name__ == "__main__":
    main()
