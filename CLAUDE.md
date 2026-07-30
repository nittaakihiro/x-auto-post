# X Auto Post System

## 概要
X（Twitter, @akionionio）の自動投稿システム。**戦略の正本は `docs/x-strategist.md`（v4, 2026-07-30 成長モデル再設計）**。ルーティン手順は `docs/x-routine-spec.md`。

## アーキテクチャ（3段）
1. **生成**: Claude Code Routines（x-post-morning 6:30 JST / noon 11:00 / evening 19:00）が投稿0〜1本+絡みカード1枚を生成し、`output/post_queue.json` / `output/dashboard.json` にcommit+push。**投稿はしない**（ゲート3回失敗の枠は休載）
2. **キュー**: `output/post_queue.json`（appendのみ。既存エントリは上書きしない）
3. **実投稿**: GitHub Actions `auto-post.yml` の `scripts/auto_post.py`
   - **正確な時刻の投稿はローカルMacのcronからのworkflow_dispatch**（7:25 / 12:00 / 20:00 / 20:50 JST）
   - Actionsのschedule cronはフォールバック（実測で40分〜3.5h遅延するため前倒し配置）
   - 予定から6時間（SKIP_GRACE_HOURS）超過したpendingはfailedにしてスキップ
   - 投稿失敗が出たらSlack DMで即通知（auto-post.ymlのNotifyステップ）

## 補助ワークフロー
- `fetch-slack.yml`: 30分毎にSlack #x-influencer-watch → `output/slack_buzz.json`
- `slack-dashboard.yml`: `output/dashboard.json` が変わった時だけ（=生成ルーティン直後、1日3回）投稿+絡み候補をSlack DM
- `fetch-metrics.yml`: 週1（月曜5:30 JST）で自分の直近100投稿のpublic_metricsを `data/analytics/live_metrics.json` へ → x-analytics-weekly ルーティン（月曜6:00 JST）が読んで `data/analytics/weekly_summary.md` を更新

## 投稿ルールの要点（詳細は docs/x-strategist.md v4）
- 必須要素ゲート: 実名1+ / 数字2+ / 新情報1+ / 現場への含意1行 / 一人称の一次観点1文+。満たせないネタは没
- **0〜3本/日（3本義務は廃止）**。ゲート3回失敗の枠は休載。週5本（土曜フラッグシップ含む）が下限
- 土曜朝はフラッグシップ「今週の建設業、数字で3つ」
- 創作体験談・あるある・気づき独り言は全廃 / **自己リプ全廃**（ソースURLリプも廃止・出典は本文に「機関名＋発表日」）
- 本文にURL・ハッシュタグ・自社名を入れない
- マンネリ対策はジャンルbanではなく「同一の数字×固有名詞ペアの14日間ban」+ 一人称表現のローテ
- 絡みカードは**各枠1枚だけ・完成文形式**（朝昼=リプ、夜=引用RT）。24h以内（snowflakeで機械検証・6h以内優先）×建設業界関連×いいね50+またはフォロワー2,000+ の3条件AND
- 引用RT・リプライはキューに入れない（API制限で失敗するため手動投稿）。**絡み実行数はfetch-metricsが週次カウント＝週次KPI**

## 検証ルール
戦略・ルールを変更したら、必ず2週間後に weekly_summary.md で前後比較する。検証なしの変更継続は禁止（6月の崩壊の再発防止）。
