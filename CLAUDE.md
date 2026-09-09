# X Auto Post System

## 概要
X（Twitter, @akionionio）の投稿支援システム。**戦略の正本は `docs/x-strategist.md`（v5, 2026-09-08 チャエン型運用「AIに一番詳しい建設業の人」）**。ルーティン手順は `docs/x-routine-spec.md`。旧版（v3〜v4.2）は `docs/archive/`。

## アーキテクチャ（v5: 下書き運転・完成文）
1. **ネタ収集（自動）**: `fetch-news.yml`（2h毎・RSS27本 → `output/news_feed.json`）＋ `fetch-slack.yml`（30分毎・Slack #x-influencer-watch → `output/slack_buzz.json`=建設系 / `output/ai_buzz.json`=AI系）。X側の監視はローカルMacの `AI-work/scripts/x_watcher.py`（2h毎・建設42＋AI16アカウント・AI系は「🌐 AI」タグ付き）
2. **生成**: Claude Code Routines（x-post-morning 6:30 JST=柱①AI速報 / noon 11:00=柱②AI×建設 / evening 19:00=柱③建設ニュースAI優先）が**完成文の下書き**（`status='draft'`＋`reply_text`=■補足/■出典＋`article_url`）1本＋絡みカード3〜4枚を生成し、`output/post_queue.json` / `output/dashboard.json` にcommit+push
3. **通知**: `slack-dashboard.yml` が下書き＋絡みカードをSlack DMへ
4. **実投稿**: 新田さんが「記事スクショを添付して投稿→■補足を自己リプ」（枠時刻は目安）
5. （温存）自動投稿系: `auto-post.yml` + ローカルlaunchd dispatch。`pending` を積めば自動投稿され、`image.type='screenshot'` なら `article_url` の記事スクショをPlaywrightで撮って添付する

## 補助ワークフロー
- `fetch-news.yml`: 2時間毎にRSS → `output/news_feed.json`（category: ai_global/ai_japan/construction_global/construction_japan・`ai_related`・48h窓）
- `fetch-slack.yml`: 30分毎にSlack → `output/slack_buzz.json` / `output/ai_buzz.json`
- `slack-dashboard.yml`: `output/dashboard.json` が変わった時だけDM
- `fetch-metrics.yml`: 週1（月曜5:30 JST）→ `data/analytics/live_metrics.json` → x-analytics-weekly ルーティン（月曜6:00 JST）が `data/analytics/weekly_summary.md` を更新

## 投稿ルールの要点（詳細は docs/x-strategist.md v5）
- 型: 【タグ】固有名詞＋結論 → 本音1行 → ・箇条書き3〜5（数字はここ） → 建設への含意1〜2行。**段落ごとに空行**・100〜200字・**画像必須**（記事スクショ）・**■補足の自己リプに出典URL**（本文URLは禁止のまま）
- 文体: です・ます基調＋ゆるい語尾（。。／笑／〜な気がする）。絵文字なし。攻撃・極論・ハッシュタグ・DM誘導・創作は禁止
- 3本/日が看板（休載は48h以内のネタが本当にゼロの時だけ）。土曜朝は【🔥今週の建設×AIニュース】
- 鮮度: AI 48h以内（24h優先）／建設72h。チャエン（@masahirochaen）が既に出したネタは彼より早いか建設の角度がある時だけ
- 絡みカード: 各枠3〜4枚・完成文。国内AI（@masahirochaen最優先）＋建設A tier。夜は海外AIバズの引用翻訳型を最低1枚。3条件AND（24h以内×AIか建設×いいね50+ orフォロワー2,000+）
- マンネリ: 同一ニュース14日ban・同じ【タグ】3連続NG

## 検証ルール
戦略・ルールを変更したら、必ず2週間後に weekly_summary.md で前後比較する（v5は 2026-09-22）。検証なしの変更継続は禁止。

2026-09-09 v5.1: 既存27フィードを30分間隔で収集（定期実行は遅延し得る）。翻訳は従来の2時間間隔＋キャッシュを維持。Slackは今回分の下書きと推奨絡みカード。戦略末尾のv5.1補足を適用する。
