# X Auto Post System

## 概要
X（Twitter, @akionionio）の投稿支援システム。**戦略の正本は `docs/x-strategist.md`（v4.2, 2026-08-03 感情起点の設計転換）**。ルーティン手順は `docs/x-routine-spec.md`。

## アーキテクチャ（v4.1: 自動投稿は停止中・下書き運転）
1. **生成**: Claude Code Routines（x-post-morning 6:30 JST / noon 11:00 / evening 19:00）が**下書き**（`status='draft'` + `hint`=解釈の種）0〜1本+絡みカード3〜4枚（1日10枚目安）を生成し、`output/post_queue.json` / `output/dashboard.json` にcommit+push
2. **通知**: `slack-dashboard.yml` が下書き＋絡みカードをSlack DMへ
3. **実投稿**: **新田さんが下書きを自分の言葉にリライトして手動投稿**（枠時刻7:25/12:00/20:00は目安）
4. （温存）自動投稿系: `auto-post.yml` + ローカルlaunchd dispatch。pendingを積めば従来どおり自動投稿される（draftは無視される）。SKIP_GRACE_HOURS=6h・失敗時Slack DM通知

## 補助ワークフロー
- `fetch-slack.yml`: 30分毎にSlack #x-influencer-watch → `output/slack_buzz.json`
- `slack-dashboard.yml`: `output/dashboard.json` が変わった時だけ（=生成ルーティン直後、1日3回）投稿+絡み候補をSlack DM
- `fetch-metrics.yml`: 週1（月曜5:30 JST）で自分の直近100投稿のpublic_metricsを `data/analytics/live_metrics.json` へ → x-analytics-weekly ルーティン（月曜6:00 JST）が読んで `data/analytics/weekly_summary.md` を更新

## 投稿ルールの要点（詳細は docs/x-strategist.md v4.2）
- 必須要素ゲート: **感情が1個動く（やべえ/マジか/いや違う・v4.2最上位）** / 実名1+ / 数字2〜4個（主役1個） / 新情報1+ / 現場への含意1行。一人称は本文に書かず `hint` へ（リライト運転）
- 勝ち型4種: 危機直撃 / 暴露 / 通説反論 / 一次体験。制度解説・統計の正確な翻訳は原則没
- **0〜3本/日（3本義務は廃止）**。感情ゲートを通るネタが無い枠は休載（判定前に5ネタ探索）。週5本（土曜フラッグシップ含む）が下限
- 土曜朝はフラッグシップ「今週の建設業、数字で3つ」
- 創作体験談・あるある・気づき独り言は全廃 / **自己リプ全廃**（ソースURLリプも廃止・出典は本文に「機関名＋発表日」）
- 本文にURL・ハッシュタグ・自社名を入れない
- マンネリ対策はジャンルbanではなく「同一の数字×固有名詞ペアの14日間ban」+ 一人称表現のローテ
- 絡みカードは**各枠3〜4枚・1日10枚目安・完成文形式**（朝昼=リプ、夜=リプ+引用RT最低1枚）。24h以内（snowflakeで機械検証・6h以内優先）×建設業界関連×いいね50+またはフォロワー2,000+ の3条件AND。条件未達で無理に埋めない
- 引用RT・リプライはキューに入れない（API制限で失敗するため手動投稿）。**絡み実行数はfetch-metricsが週次カウント＝週次KPI**

## 検証ルール
戦略・ルールを変更したら、必ず2週間後に weekly_summary.md で前後比較する。検証なしの変更継続は禁止（6月の崩壊の再発防止）。
