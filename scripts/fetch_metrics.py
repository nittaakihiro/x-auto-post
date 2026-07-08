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


def main():
    poster = XPoster()
    tweets = poster.get_my_tweets(100)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(tweets),
        "tweets": tweets,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"[METRICS] {len(tweets)}件を {OUT} に保存")


if __name__ == "__main__":
    main()
